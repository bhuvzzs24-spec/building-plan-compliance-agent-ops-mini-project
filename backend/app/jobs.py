from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import os

logger = logging.getLogger("building_plan_compliance.queue")
_local_queue = ThreadPoolExecutor(max_workers=int(os.getenv("QUEUE_THREADS", "4")))
QUEUE_NAME = os.getenv("REDIS_QUEUE_NAME", "building_compliance_runs")
PROCESSING_QUEUE_NAME = f"{QUEUE_NAME}:processing"
ENQUEUED_KEY_PREFIX = f"{QUEUE_NAME}:enqueued:"
ENQUEUED_KEY_TTL_SECONDS = 86_400
_ENQUEUE_ONCE_SCRIPT = """
if redis.call('SET', KEYS[1], '1', 'NX', 'EX', ARGV[2]) then
  redis.call('LPUSH', KEYS[2], ARGV[1])
  return 1
end
return 0
"""
_RECOVER_ENQUEUE_SCRIPT = """
local function has_run(list_key, run_id)
  local entries = redis.call('LRANGE', list_key, 0, -1)
  for _, raw in ipairs(entries) do
    local ok, item = pcall(cjson.decode, raw)
    if ok and item['run_id'] == run_id then return true end
  end
  return false
end
if has_run(KEYS[2], ARGV[2]) or has_run(KEYS[3], ARGV[2]) then
  redis.call('SET', KEYS[1], '1', 'EX', ARGV[3])
  return 0
end
redis.call('SET', KEYS[1], '1', 'EX', ARGV[3])
redis.call('LPUSH', KEYS[2], ARGV[1])
return 1
"""
_ACK_JOB_SCRIPT = """
redis.call('LREM', KEYS[1], 1, ARGV[1])
redis.call('DEL', KEYS[2])
return 1
"""


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


def enqueue_run(run_id: str, proposal: dict, correlation_id: str, force: bool = False) -> str:
    payload = json.dumps({
        "run_id": run_id,
        "proposal": proposal,
        "correlation_id": correlation_id,
    }, separators=(",", ":"))
    client = _redis_client()
    if client is not None:
        try:
            # Redis executes marker creation and LPUSH atomically, closing the
            # crash window between idempotency state and queue insertion.
            marker = f"{ENQUEUED_KEY_PREFIX}{run_id}"
            if force:
                client.eval(
                    _RECOVER_ENQUEUE_SCRIPT, 3, marker, QUEUE_NAME,
                    PROCESSING_QUEUE_NAME, payload, run_id, ENQUEUED_KEY_TTL_SECONDS,
                )
            else:
                client.eval(_ENQUEUE_ONCE_SCRIPT, 2, marker, QUEUE_NAME, payload, ENQUEUED_KEY_TTL_SECONDS)
            return "redis"
        except Exception:
            logger.exception("Redis enqueue failed; using bounded local fallback")
    return "local"


def acknowledge_run(client, run_id: str, raw_payload: str) -> None:
    """Remove the processing entry and its dedupe marker atomically."""
    client.eval(
        _ACK_JOB_SCRIPT, 2, PROCESSING_QUEUE_NAME,
        f"{ENQUEUED_KEY_PREFIX}{run_id}", raw_payload,
    )


def _run_local(run_id: str, proposal: dict, correlation_id: str) -> None:
    from backend.app.run_service import execute_run
    execute_run(run_id, proposal, correlation_id)


def run_sync(run_id: str, proposal: dict, correlation_id: str) -> None:
    # Retained as a clear hook for test harnesses and local smoke checks.
    _local_queue.submit(_run_local, run_id, proposal, correlation_id)

