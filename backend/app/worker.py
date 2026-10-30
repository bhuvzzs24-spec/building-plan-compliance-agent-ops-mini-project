from __future__ import annotations

import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.app.jobs import QUEUE_NAME
from backend.app.run_service import execute_run

logger = logging.getLogger("building_plan_compliance.worker")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"healthy","service":"worker"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/metrics":
            body = b"building_compliance_worker_up 1\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        logger.info(json.dumps({"event": "worker_http", "message": format % args}))


def serve_health():
    server = ThreadingHTTPServer(("0.0.0.0", int(os.getenv("WORKER_HEALTH_PORT", "9101"))), HealthHandler)
    server.serve_forever()


def main():
    import redis

    url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    client = redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=5, decode_responses=True)
    threading.Thread(target=serve_health, daemon=True).start()
    delay = 0.5
    logger.info(json.dumps({"event": "worker_started", "queue": QUEUE_NAME}))
    while True:
        try:
            item = client.blpop(QUEUE_NAME, timeout=5)
            delay = 0.5
            if item is None:
                continue
            _, raw = item
            job = json.loads(raw)
            execute_run(job["run_id"], job["proposal"], job["correlation_id"])
        except Exception as exc:
            logger.exception(json.dumps({"event": "worker_degraded", "error_type": type(exc).__name__}))
            time.sleep(delay)
            delay = min(delay * 2, 8)


if __name__ == "__main__":
    main()
