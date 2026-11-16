"""Opt-in delayed OpenAI-compatible test stub. Never use as production evidence."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import time


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "healthy", "service": "delayed-test-stub"})
        else:
            self._send(404, {"error": "not_found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._send(404, {"error": "not_found"})
            return
        mode = os.getenv("LLM_STUB_MODE", "normal")
        time.sleep(max(0, int(os.getenv("LLM_STUB_DELAY_MS", "350"))) / 1000)
        if mode == "unavailable":
            self._send(503, {"error": "injected_provider_unavailable"})
            return
        try:
            request = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            user = json.loads(request["messages"][-1]["content"])
            findings = user.get("findings", [])
            supported = mode != "unsupported"
            result = {
                "checks": [
                    {"finding_index": index, "supported": supported, "reason": "Test stub controlled result."}
                    for index, _ in enumerate(findings)
                ],
                "groundedness": 0.9 if supported else 0.1,
                "context_relevance": 0.9,
                "faithfulness": 0.9 if supported else 0.1,
                "hallucination_rate": 0.1 if supported else 0.9,
            }
            self._send(200, {
                "id": "stub-completion",
                "choices": [{"message": {"role": "assistant", "content": json.dumps(result)}}],
                # Token and price values are intentionally omitted: the stub
                # does not pretend to measure provider tokenization or cost.
            })
        except Exception:
            self._send(400, {"error": "invalid_stub_request"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(os.getenv("LLM_STUB_PORT", "8081"))), Handler).serve_forever()
