from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os

logger = logging.getLogger("building_plan_compliance.queue")
_local_queue = ThreadPoolExecutor(max_workers=int(os.getenv("QUEUE_THREADS", "4")))
QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "building_compliance_runs")


def _redis_client():
    url = os.getenv("REDIS_URL")
    if not url:
        return None
    try:
        import redis
        return redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2, decode_responses=True)
    except Exception:
        logger.exception("Redis client could not be initialized")
        return None


def enqueue_run(run_id: str, proposal: dict, correlation_id: str) -> str:
    payload = json.dumps({
        "run_id": run_id,
        "proposal": proposal,
        "correlation_id": correlation_id,
    }, separators=(",", ":"))
    client = _redis_client()
    if client is not None:
        try:
            client.rpush(QUEUE_NAME, payload)
            return "redis"
        except Exception:
            logger.exception("Redis enqueue failed; using bounded local fallback")
    return "local"


def _run_local(run_id: str, proposal: dict, correlation_id: str) -> None:
    from backend.app.run_service import execute_run
    execute_run(run_id, proposal, correlation_id)


def run_sync(run_id: str, proposal: dict, correlation_id: str) -> None:
    # Retained as a clear hook for test harnesses and local smoke checks.
    _local_queue.submit(_run_local, run_id, proposal, correlation_id)

