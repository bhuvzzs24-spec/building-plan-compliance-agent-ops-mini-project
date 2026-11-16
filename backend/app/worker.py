from __future__ import annotations

import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from backend.app.jobs import QUEUE_NAME, PROCESSING_QUEUE_NAME, enqueue_run, acknowledge_run
from backend.app.run_service import execute_run
from backend.app.metrics import metrics, refresh_process_metrics
from backend.app import storage

logger = logging.getLogger("building_plan_compliance.worker")


def recover_stranded_jobs(client) -> int:
    recovered = 0
    while True:
        # RPOPLPUSH is atomic; a crash during recovery cannot drop the item.
        stranded = client.rpoplpush(PROCESSING_QUEUE_NAME, QUEUE_NAME)
        if stranded is None:
            return recovered
        metrics.increment("worker_recovered_jobs_total")
        recovered += 1


def reconcile_missing_jobs(client) -> int:
    """Requeue persisted pending/stale runs missing from both Redis lists."""
    queued = client.lrange(QUEUE_NAME, 0, -1) + client.lrange(PROCESSING_QUEUE_NAME, 0, -1)
    present_ids = set()
    for raw in queued:
        try:
            present_ids.add(json.loads(raw)["run_id"])
        except (ValueError, TypeError, KeyError):
            continue
    recovered = 0
    for job in storage.recoverable_runs(float(os.getenv("WORKER_STALE_SECONDS", "60"))):
        if job["run_id"] not in present_ids:
            if enqueue_run(job["run_id"], job["proposal"], job["correlation_id"], force=True) == "redis":
                recovered += 1
                metrics.increment("worker_recovered_jobs_total")
    return recovered


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b'{"status":"healthy","service":"worker"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/metrics":
            refresh_process_metrics()
            body = metrics.render(service="worker").encode("utf-8")
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
    storage.initialize()
    # Redeliver jobs stranded in processing by a worker crash. The persisted
    # run lease prevents concurrent duplicate execution of a fresh claim.
    recover_stranded_jobs(client)
    reconcile_missing_jobs(client)
    logger.info(json.dumps({"event": "worker_started", "queue": QUEUE_NAME}))
    while True:
        try:
            raw = client.brpoplpush(QUEUE_NAME, PROCESSING_QUEUE_NAME, timeout=5)
            delay = 0.5
            if raw is None:
                continue
            job = json.loads(raw)
            metrics.increment("worker_jobs_received_total")
            execute_run(job["run_id"], job["proposal"], job["correlation_id"])
            acknowledge_run(client, job["run_id"], raw)
            metrics.increment("worker_jobs_acknowledged_total")
        except Exception as exc:
            # Leave failed/unacknowledged work in the processing list for
            # startup recovery rather than silently discarding the payload.
            logger.exception(json.dumps({"event": "worker_degraded", "error_type": type(exc).__name__}))
            time.sleep(delay)
            delay = min(delay * 2, 8)


if __name__ == "__main__":
    main()
