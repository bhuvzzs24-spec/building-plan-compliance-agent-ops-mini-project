from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os
import time
from typing import Any

from backend.app import storage
from backend.app.metrics import metrics

logger = logging.getLogger("building_plan_compliance.worker")
_workflow_executor = ThreadPoolExecutor(max_workers=int(os.getenv("WORKFLOW_THREADS", "4")))


def _invoke_workflow(details: dict[str, Any]) -> dict[str, Any]:
    from agents.workflow import compliance_workflow
    return compliance_workflow.invoke({
        "building_details": details,
        "findings": [],
        "clauses": [],
        "citations": [],
    })


def execute_run(run_id: str, details: dict[str, Any], correlation_id: str) -> None:
    started = time.perf_counter()
    if not storage.claim_run(run_id, float(os.getenv("WORKER_STALE_SECONDS", "60"))):
        return
    future = None
    try:
        future = _workflow_executor.submit(_invoke_workflow, details)
        result = future.result(timeout=float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "30")))
        result["correlation_id"] = correlation_id
        result["duration_seconds"] = round(time.perf_counter() - started, 6)
        result["limits"] = {"max_steps": 3, "max_tool_calls": 8}
        storage.update_run(run_id, "completed", result)
        metrics.increment("workflow_runs_total", labels={"status": "completed"})
        metrics.increment("workflow_tool_calls_total", result.get("tool_calls", 0))
        metrics.increment("workflow_steps_total", len(result.get("tool_trace", [])))
        metrics.observe("workflow_duration_seconds", result["duration_seconds"])
        logger.info(json.dumps({
            "event": "workflow_completed",
            "run_id": run_id,
            "correlation_id": correlation_id,
            "recommendation": result.get("recommendation"),
            "duration_seconds": result["duration_seconds"],
            "tool_calls": result.get("tool_calls", 0),
        }, separators=(",", ":")))
    except TimeoutError:
        if future is not None:
            future.cancel()  # Cancels queued work; running Python work may not be interruptible.
        storage.update_run(run_id, "failed", {
            "correlation_id": correlation_id,
            "recommendation": "specialist-review",
            "error": "Workflow exceeded its configured timeout; no compliance answer was returned.",
        })
        metrics.increment("workflow_runs_total", labels={"status": "timeout"})
        metrics.observe("workflow_duration_seconds", time.perf_counter() - started)
        logger.error(json.dumps({
            "event": "workflow_timeout",
            "run_id": run_id,
            "correlation_id": correlation_id,
            "timeout_seconds": float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "30")),
        }, separators=(",", ":")))
    except Exception as exc:
        storage.update_run(run_id, "failed", {
            "correlation_id": correlation_id,
            "recommendation": "specialist-review",
            "error": "Workflow failed; no compliance answer was returned.",
        })
        metrics.increment("workflow_runs_total", labels={"status": "failed"})
        metrics.observe("workflow_duration_seconds", time.perf_counter() - started)
        logger.exception(json.dumps({
            "event": "workflow_failed",
            "run_id": run_id,
            "correlation_id": correlation_id,
            "error_type": type(exc).__name__,
        }, separators=(",", ":")))


def _worker_executor():
    return _workflow_executor
