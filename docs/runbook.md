# Operations runbook

## 1. API healthy but not ready

**Symptom:** /health returns healthy, while /health/ready returns 503 or runs contain no citations.

**Confirm:**

~~~bash
docker compose ps
docker compose logs corpus-indexer
docker compose exec api python -c "import chromadb; c=chromadb.PersistentClient(path='/corpus/chroma_db').get_collection('building_bye_laws'); print(c.count())"
~~~

**Recover:** Confirm PDFs are present under data/bye_laws/, inspect indexer errors, then rerun docker compose run --rm corpus-indexer. Scanned PDFs may need OCR. Recheck /health/ready. A non-empty collection does not prove that rules are current.

## 2. Runs remain pending

**Symptom:** POST /runs returns a run ID but polling does not reach a terminal status.

**Confirm:**

~~~bash
docker compose ps
docker compose logs redis agent-worker api
~~~

Check Redis health and worker count; confirm API and worker mount the same run_state volume and use the same queue name.

**Recover:** If Redis is unhealthy, restart Redis and workers with docker compose up -d redis agent-worker. Jobs accepted into a healthy persistent Redis queue remain available. If a worker repeatedly fails, preserve logs and the run ID; local API fallback applies only when enqueueing and does not recover jobs already stuck in Redis.

## Development incident log

| Date | Incident | Impact | Recovery/status |
|---|---|---|---|
| 2026-10-29 | Initial restricted test execution blocked Windows socket-pair creation and Chroma local storage; the first run could not collect/complete tests. | Initial sandbox attempt produced no valid pass result. | Re-ran with approved test execution: 27 tests passed. Separately, Docker Engine was unavailable; Compose syntax passed, but multi-container startup remains unverified. |
