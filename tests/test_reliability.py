from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from backend.app import storage


def test_run_claim_is_idempotent_under_concurrent_workers():
    run_id = "concurrent-claim-test"
    storage.create_run(run_id, {"building_use": "residential"}, "trace-test")
    with ThreadPoolExecutor(max_workers=8) as executor:
        claims = list(executor.map(lambda _: storage.claim_run(run_id), range(8)))
    assert sum(claims) == 1


def test_stale_running_lease_can_be_recovered_but_terminal_run_cannot():
    run_id = "stale-claim-test"
    storage.create_run(run_id, {"building_use": "residential"}, "trace-test")
    assert storage.claim_run(run_id, stale_after_seconds=30)
    old = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    with storage.connect() as conn:
        conn.execute("UPDATE runs SET updated_at=? WHERE run_id=?", (old, run_id))
    assert storage.claim_run(run_id, stale_after_seconds=30)
    storage.update_run(run_id, "completed", {"recommendation": "specialist-review"})
    assert storage.claim_run(run_id, stale_after_seconds=0) is False


def test_worker_requeues_stranded_processing_items():
    from backend.app import worker

    class FakeRedis:
        def __init__(self):
            self.processing = ["job-1", "job-2"]
            self.ready = []

        def rpoplpush(self, source, destination):
            assert source == worker.PROCESSING_QUEUE_NAME
            assert destination == worker.QUEUE_NAME
            if not self.processing: return None
            value = self.processing.pop()
            self.ready.insert(0, value)
            return value

    redis = FakeRedis()
    assert worker.recover_stranded_jobs(redis) == 2
    assert redis.processing == []
    assert sorted(redis.ready) == ["job-1", "job-2"]


def test_redis_enqueue_uses_fifo_compatible_list_direction(monkeypatch):
    from backend.app import jobs

    class FakeRedis:
        def __init__(self): self.item = None; self.keys = set()
        def eval(self, script, key_count, marker, queue, payload, ttl):
            if marker in self.keys: return 0
            self.keys.add(marker); self.item = (queue, payload); return 1

    client = FakeRedis()
    monkeypatch.setattr(jobs, "_redis_client", lambda: client)
    assert jobs.enqueue_run("r1", {"building_use": "residential"}, "c1") == "redis"
    assert client.item[0] == jobs.QUEUE_NAME
    import json
    assert json.loads(client.item[1])["run_id"] == "r1"


def test_startup_reconciliation_recovers_persisted_unqueued_run(monkeypatch):
    from backend.app import jobs, worker

    run_id = "persisted-before-enqueue"
    storage.create_run(run_id, {"building_use": "residential"}, "recover-correlation")

    class FakeRedis:
        def __init__(self): self.ready=[]; self.processing=[]; self.keys=set()
        def lrange(self, key, start, end):
            return self.ready[:] if key == jobs.QUEUE_NAME else self.processing[:]
        def eval(self, script, key_count, *args):
            if key_count == 3:
                marker, queue, processing, payload, job_id, ttl = args
                import json
                present = self.ready + self.processing
                if any(json.loads(raw).get("run_id") == job_id for raw in present):
                    self.keys.add(marker)
                    return 0
            else:
                marker, queue, payload, ttl = args
                if marker in self.keys: return 0
            self.keys.add(marker)
            self.ready.insert(0, payload)
            return 1

    client = FakeRedis()
    monkeypatch.setattr(jobs, "_redis_client", lambda: client)
    assert worker.reconcile_missing_jobs(client) >= 1
    import json
    assert any(json.loads(payload)["run_id"] == run_id for payload in client.ready)


def test_metrics_emit_service_uptime_counters_and_histograms():
    from backend.app.metrics import Metrics

    metrics = Metrics()
    metrics.increment("workflow_runs_total", labels={"status": "completed"})
    metrics.observe("workflow_duration_seconds", 0.25)
    rendered = metrics.render(service="worker")
    assert "building_compliance_worker_up 1" in rendered
    assert 'building_compliance_workflow_runs_total{status="completed"} 1' in rendered
    assert 'building_compliance_workflow_duration_seconds_bucket{le="0.25"} 1' in rendered
    assert "building_compliance_process_uptime_seconds" in rendered
