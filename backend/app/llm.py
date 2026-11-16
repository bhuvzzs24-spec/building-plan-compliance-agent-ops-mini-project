"""Optional OpenAI-compatible model adapter with bounded retries and breaker.

No provider is contacted unless LLM_BASE_URL and LLM_MODEL are configured.
Credentials are read from the environment and are never logged or persisted.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.app.metrics import metrics


PROMPT_VERSION = "semantic-review-v2"
PROMPT_DIR = Path(__file__).resolve().parents[2] / "agents" / "prompts"
INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"ignore\s+(all\s+)?(safety|security|compliance|review)\s+(rules|checks|requirements|instructions)", re.I),
    re.compile(r"declare\s+(it\s+)?approved\b", re.I),
    re.compile(r"(reveal|print|show)\s+(the\s+)?(system|hidden)\s+prompt", re.I),
    re.compile(r"act\s+as\s+(system|developer|admin)", re.I),
    re.compile(r"bypass\s+(the\s+)?(rules|guardrails|safety)", re.I),
)
TOXIC_PATTERNS = (
    re.compile(r"\b(?:fuck(?:ing)?|shit(?:ty)?|bitch(?:es)?|asshole|kill yourself)\b", re.I),
)


class ProviderUnavailable(RuntimeError):
    pass


@dataclass
class ProviderResult:
    content: str
    usage: dict[str, Any]
    latency_seconds: float
    prompt_version: str


def prompt_injection_detected(values: Any) -> bool:
    text = json.dumps(values, ensure_ascii=False, default=str)
    return any(pattern.search(text) for pattern in INJECTION_PATTERNS)


def toxicity_detected(values: Any) -> bool:
    text = json.dumps(values, ensure_ascii=False, default=str)
    return any(pattern.search(text) for pattern in TOXIC_PATTERNS)


class CircuitBreaker:
    def __init__(self, threshold: int = 3, reset_seconds: float = 30.0):
        self.threshold = max(1, threshold)
        self.reset_seconds = max(1.0, reset_seconds)
        self.failures = 0
        self.opened_at: float | None = None
        self.half_open_in_flight = False
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self.opened_at is None:
                return "closed"
            if time.monotonic() - self.opened_at < self.reset_seconds:
                return "open"
            return "half-open"

    def allow(self) -> bool:
        with self._lock:
            if self.opened_at is None:
                return True
            if time.monotonic() - self.opened_at < self.reset_seconds:
                return False
            if self.half_open_in_flight:
                return False
            self.half_open_in_flight = True
            return True

    def success(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None
            self.half_open_in_flight = False

    def failure(self) -> None:
        with self._lock:
            self.failures += 1
            self.half_open_in_flight = False
            if self.failures >= self.threshold:
                self.opened_at = time.monotonic()


class OpenAICompatibleClient:
    def __init__(self):
        self.base_url = os.getenv("LLM_BASE_URL", "").rstrip("/")
        self.model = os.getenv("LLM_MODEL", "")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))
        self.max_retries = min(2, max(0, int(os.getenv("LLM_MAX_RETRIES", "1"))))
        self.breaker = CircuitBreaker(
            int(os.getenv("LLM_BREAKER_FAILURES", "3")),
            float(os.getenv("LLM_BREAKER_RESET_SECONDS", "30")),
        )

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def complete(self, system_prompt: str, user_payload: dict[str, Any], prompt_version: str = PROMPT_VERSION) -> ProviderResult:
        if not self.configured:
            raise ProviderUnavailable("No model provider is configured")
        if not self.breaker.allow():
            metrics.increment("llm_circuit_open_total")
            raise ProviderUnavailable("Model circuit breaker is open")
        payload = json.dumps({
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(f"{self.base_url}/chat/completions", data=payload, headers=headers)
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read())
                content = body["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("Provider returned non-text content")
                usage = body.get("usage") if isinstance(body.get("usage"), dict) else {}
                self.breaker.success()
                latency = time.perf_counter() - started
                metrics.increment("llm_calls_total", labels={"status": "success"})
                metrics.observe("llm_call_duration_seconds", latency)
                return ProviderResult(content, usage, latency, prompt_version)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, IndexError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(0.2 * (2 ** attempt), 1.0))
        self.breaker.failure()
        metrics.increment("llm_calls_total", labels={"status": "failure"})
        metrics.increment("llm_provider_failures_total")
        raise ProviderUnavailable(f"Model request failed: {type(last_error).__name__}") from last_error


def _cost_estimate(usage: dict[str, Any]) -> float | None:
    try:
        input_rate = float(os.environ["LLM_INPUT_USD_PER_MILLION"])
        output_rate = float(os.environ["LLM_OUTPUT_USD_PER_MILLION"])
        input_tokens = int(usage["prompt_tokens"])
        output_tokens = int(usage["completion_tokens"])
    except (KeyError, TypeError, ValueError):
        return None
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


_client_lock = threading.Lock()
_client_instance: OpenAICompatibleClient | None = None
_client_signature: tuple[str, str, str] | None = None


def _client() -> OpenAICompatibleClient:
    global _client_instance, _client_signature
    signature = (
        os.getenv("LLM_BASE_URL", ""),
        os.getenv("LLM_MODEL", ""),
        os.getenv("LLM_API_KEY", ""),
    )
    with _client_lock:
        if _client_instance is None or signature != _client_signature:
            _client_instance = OpenAICompatibleClient()
            _client_signature = signature
        return _client_instance


def verify_findings(
    findings: list[dict[str, Any]],
    proposal: dict[str, Any],
    prompt_variant: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Optionally semantically verify findings; strict allow-list on all outputs."""
    if prompt_injection_detected({"proposal": proposal, "findings": findings}):
        return None, {"status": "blocked_injection", "provider_configured": False, "prompt_version": PROMPT_VERSION}
    if toxicity_detected({"proposal": proposal, "findings": findings}):
        return None, {"status": "blocked_unsafe_input", "provider_configured": False, "prompt_version": PROMPT_VERSION}
    provider = _client()
    if not provider.configured:
        return None, {"status": "unavailable", "provider_configured": False, "prompt_version": None}
    variant = prompt_variant or "v2"
    prompt_path = PROMPT_DIR / f"semantic_review_{variant}.txt"
    if variant not in {"v1", "v2"} or not prompt_path.is_file():
        raise ValueError("Unknown semantic review prompt variant")
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
        result = provider.complete(
            prompt,
            {"proposal": proposal, "findings": findings},
            f"semantic-review-{variant}",
        )
        parsed = json.loads(result.content)
        checks = parsed.get("checks")
        if not isinstance(checks, list) or len(checks) != len(findings):
            raise ValueError("Verifier output did not match the findings")
        safe_checks = []
        for index, check in enumerate(checks):
            if not isinstance(check, dict) or check.get("finding_index") != index or not isinstance(check.get("supported"), bool):
                raise ValueError("Verifier returned an invalid check")
            reason = check.get("reason", "")
            if not isinstance(reason, str) or len(reason) > 500:
                raise ValueError("Verifier returned an invalid reason")
            if toxicity_detected(reason) or prompt_injection_detected(reason):
                raise ValueError("Verifier returned content rejected by the output safety guard")
            safe_checks.append({"finding_index": index, "supported": check["supported"], "reason": reason})
        score_names = ("groundedness", "context_relevance", "faithfulness", "hallucination_rate")
        scores = {}
        for key in score_names:
            score = parsed.get(key)
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise ValueError(f"Verifier returned invalid {key}")
            scores[key] = float(score)
            metrics.observe(f"llm_{key}", float(score))
        usage = result.usage
        call_usage = {
            "call_id": f"{result.prompt_version}:{time.time_ns()}",
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "usage_source": "provider_reported" if usage.get("prompt_tokens") is not None and usage.get("completion_tokens") is not None else "unavailable",
            "cost_estimate_usd": _cost_estimate(usage),
            "cost_source": "estimated_from_configured_rates" if _cost_estimate(usage) is not None else "unavailable",
            "latency_seconds": round(result.latency_seconds, 6),
            "model": provider.model,
            "prompt_version": f"semantic-review-{variant}",
        }
        metrics.increment("llm_prompt_tokens_total", int(usage.get("prompt_tokens", 0) or 0))
        metrics.increment("llm_completion_tokens_total", int(usage.get("completion_tokens", 0) or 0))
        estimate = call_usage["cost_estimate_usd"]
        if estimate is not None:
            metrics.increment("llm_cost_estimate_usd_total", estimate)
        return {"checks": safe_checks, **scores}, {"status": "verified", **call_usage}
    except (ProviderUnavailable, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return None, {
            "status": "unavailable",
            "provider_configured": True,
            "prompt_version": f"semantic-review-{variant}",
            "error_type": type(exc).__name__,
        }


def provider_status() -> dict[str, Any]:
    provider = _client()
    return {"configured": provider.configured, "model": provider.model or None, "breaker_state": provider.breaker.state}
