# Docker Verification Report

**Date:** 16 November 2026
**Repository branch:** `main`
**Docker acceptance:** **BLOCKED — full container stack was not started**

## Execution environment and storage

- Host: macOS 25.6, Apple Silicon (ARM64).
- Docker CLI: 29.9.3, context `desktop-linux`.
- Docker Compose: v5.7.0.
- Filesystem containing the project: 228 GiB total, 200 GiB used, **3.2 GiB available (99% capacity)** at check time.
- Docker Desktop data directory: 1.9 GiB allocated according to `du -sh`.
- Docker VM disk image `Docker.raw`: 1.0 TiB logical/sparse size. This is its apparent capacity, not available VM storage.
- Docker's internal image/layer/volume usage could not be queried because the daemon API was unavailable. Do not interpret host `df` or `Docker.raw` logical size as Docker's internal free-space figure.

## Daemon access and prior failure diagnosis

`docker info` and `docker compose ps --all` failed to access `unix:///Users/bhuvzzs/.docker/run/docker.sock` with **permission denied**. A narrowly scoped socket permission request was granted, but the CLI still could not connect. Docker Desktop logs were readable directly and show the engine stopping after writes failed with **`no space left on device`** in its VM `init.log` and `console.log`. The Desktop error payload says **“Docker Desktop cannot continue because the disk is full.”** The host volume is at 99% usage with 3.2 GiB free.

This evidence identifies disk exhaustion as the cause of the observed Docker Desktop shutdown. It does not show a corrupted image layer or confirm a read-only filesystem/mount. The previous “read-only filesystem” description is not supported by the current logs; the concrete recorded error is “no space left on device.” The daemon is not running/accessible in this execution, and socket access is an additional executor limitation.

No pruning, image/volume deletion, factory reset, cleanup, or Docker build was attempted. No personal or project files were removed.

## Compose configuration and image optimization

Command:

```bash
docker compose config --quiet
```

**PASS:** exit code 0. Resolved service list: `agent-worker`, `api`, `corpus-indexer`, `frontend`, `grafana`, `prometheus`, `redis`.

Image build and build context changes made for lower disk use:

- `Dockerfile` now copies only the runtime packages and bye-laws corpus instead of the whole repository.
- `.dockerignore` excludes tests, documentation, evaluation, observability files, local workspace artifacts, and generated reports from image contexts. The frontend build still receives the frontend and entrypoint it needs.
- API, worker, and one-shot indexer share the `building-plan-compliance-app:local` image tag so identical Python runtime layers can be reused.
- API and worker now read `/corpus/index_manifest.json`, the manifest written by the corpus indexer into their shared volume.
- Existing Python base image is `python:3.11-slim`; dependency installation already uses `pip --no-cache-dir`.

The changed Dockerfile and image tag were not built because storage was critically low and the daemon could not be reached. Image size reduction and image sharing are **unmeasured**, not passed.

## Image build and container outcomes

| Check | Result | Evidence |
|---|---|---|
| Docker Desktop daemon access | BLOCKED | Docker socket access denied; Desktop logs report disk-full shutdown. |
| `docker compose up -d --build` | NOT RUN | Rebuilding with only 3.2 GiB host space and an unavailable daemon risks another disk-full failure. No retry was made. |
| `docker compose ps --all` | BLOCKED | Exit 1, permission denied connecting to Docker API socket. |
| Image inventory / `docker system df` | BLOCKED | Docker API unavailable; no image/cache/volume inventory or internal usage was reported. |
| Redis | BLOCKED | No containers started. |
| Corpus indexer container | BLOCKED | No containers started. |
| FastAPI container | BLOCKED | No containers started. |
| Agent worker container | BLOCKED | No containers started. |
| Frontend container | BLOCKED | No containers started. |
| Prometheus container | BLOCKED | No containers started. |
| Grafana container | BLOCKED | No containers started. |

## Application-level results outside Docker

These local process checks do not count as Docker validation. The previously verified non-container run indexed the historical PDF (84 extracted pages, 243 chunks), returned readiness HTTP 200, accepted a valid request with HTTP 202 and completed a run with four obligation findings and ten citations, including historical Table 4/page 22 and Table 6/page 24 in separate findings. The result was `specialist-review`. A malformed request returned HTTP 422, field-level errors, a quarantine ID, and `agent_started=false`. No current-code frontend browser test was run.

The local retrieval evaluation completed 20/20 scenarios with zero execution errors; it does not measure labeled accuracy or semantic support. Its measurements do not substitute for a container-to-container test.

## Frontend, Redis, and end-to-end integration

**BLOCKED / NOT RUN in containers.** No live Compose network, persistent Docker volume, Redis queue, worker execution, indexer dependency, container health check, or frontend-to-API result display was observed. Browser automation was not available in the current execution tools. The local API results above are process-mode only and do not establish Docker integration.

## Worker scaling and load testing

The following were **not run**:

```bash
docker compose up -d --scale agent-worker=3
locust -f evaluation/locustfile.py --host http://localhost:8000
```

RPS, p50/p95, error rate, end-to-end latency under load, SLO failure concurrency, and one-worker versus three-worker results are unavailable. The declared 45-second p95 SLO remains unmeasured. No load numbers are inferred or fabricated.

## Remote Docker availability

`docker context ls` showed only local `default` and `desktop-linux` contexts; no remote daemon was configured. `docker offload status` returned an unexpected connection error, and the shell could not resolve its reporting host. No remote Docker-capable environment or corresponding connector was available to this task. I did not provision a paid or third-party environment.

## Remaining action to unblock Docker acceptance

Docker Desktop needs enough writable host storage to start its VM and extract the seven-service stack's images. With only 3.2 GiB free and logs proving disk-full shutdown, a build is unsafe. No personal data needs to be deleted by this agent. The smallest safe unblock is either:

1. Make additional storage available without deleting personal files (for example, attach/use an authorized external storage location for Docker Desktop's data), restart Docker Desktop, and allow this executor to reach its API socket; or
2. Provide an authorized remote Docker host/context with adequate storage and access for this task.

Once a daemon is reachable and storage is adequate, rerun Compose build/start, verify every health check and live client path, scale to three workers, and execute Locust before changing Docker status from BLOCKED.
