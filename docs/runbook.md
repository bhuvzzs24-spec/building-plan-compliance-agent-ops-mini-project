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

Check Redis health and worker count; confirm API and worker mount the same run_state volume and use the same queue name. The worker atomically moves jobs from the ready list to a processing list, acknowledges only after terminal persistence, requeues stranded processing jobs on startup, and reconciles SQLite pending/stale runs against Redis. These recovery paths have unit tests; they still require a live Redis/worker deployment check.

**Recover:** If Redis is unhealthy, restart Redis and workers with `docker compose up -d redis agent-worker`. On worker startup, stranded processing jobs are requeued and missing jobs are reconciled from SQLite. Preserve logs and the run ID if a worker repeatedly fails. The API's local fallback is used only when queue submission is unavailable; it is not the recovery mechanism for jobs already stored in Redis. Verify recovery on the target Docker host before treating it as operationally accepted.

## 3. Docker Desktop stops with a disk-full error

**Symptom:** Docker CLI reports that it cannot connect to the engine, and Docker Desktop logs report `no space left on device` while writing VM logs or its disk image.

**Confirm without changing data:** Check host free space with `df -h`; inspect Docker Desktop logs; query `docker system df` only if the daemon is responsive. A sparse `Docker.raw` logical size does not show available host space or internal VM free space.

**Recover safely:** Stop builds and image pulls. Do not prune images/volumes or reset Docker Desktop as a diagnostic shortcut. Make additional writable storage available without removing project/personal data, restart Docker Desktop, then confirm `docker info` and `docker system df` before building. If local capacity cannot be increased, use an authorized remote Docker host.

## Development incident log

| Date | Incident | Impact | Recovery/status |
|---|---|---|---|
| 2026-10-29 | Initial restricted test execution blocked Windows socket-pair creation and Chroma local storage; the first run could not collect/complete tests. | Initial sandbox attempt produced no valid pass result. | Re-ran with approved test execution: 27 tests passed. Separately, Docker Engine was unavailable; Compose syntax passed, but multi-container startup remains unverified. |
| 2026-11-16 | Docker Desktop VM log writes failed with `no space left on device`; Desktop reported disk full. Host volume had 3.2 GiB free at 99% usage. Docker API socket was inaccessible to the task executor. | Container build/start, health checks, worker scaling, and load testing could not run. | No pruning, reset, build, or data removal attempted. Compose syntax passed; issue remains unresolved pending more storage or an authorized remote Docker host. |
| 2026-11-17 | Docker runtime intentionally not started for this task because the user directed that local Docker not run with limited storage. | Docker images, container health, Redis integration, scaling, and Locust remain unverified. | Base Compose and load-test overlay syntax passed. No remote Docker host was attached. No cleanup or Docker data changes were made. |
