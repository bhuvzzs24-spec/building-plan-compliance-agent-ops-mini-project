# Local development mode (macOS, no Docker)

Local mode is intended for lightweight development and the faculty workflow demo on a Mac where Docker is unavailable or storage-constrained. It keeps the Compose configuration intact for later deployment verification.

## Start

From the repository root:

```bash
./scripts/start_local.sh
```

The launcher checks for FastAPI, Uvicorn, Pydantic, LangGraph, ChromaDB and pypdf imports before doing anything. It prefers the active virtual environment, then an already-provisioned Python, then `.venv`. It does not install packages automatically. If dependencies are missing, opt into a project-local install with `INSTALL_LOCAL_DEPS=1 ./scripts/start_local.sh`; this uses `requirements-local.txt` and `.venv` only.

The script verifies the two ports are free, unsets `REDIS_URL`, reuses the index when source hashes match, launches FastAPI on `http://localhost:8000` and serves the frontend on `http://localhost:5500`. Ctrl+C stops both child processes. Run records persist in `data/run_state.sqlite3` and the local Chroma collection lives under `data/chroma_db` by default.

## What is exercised

`POST /runs` returns HTTP 202 and submits to the existing bounded local thread-pool queue. Poll the returned URL until completed. The LangGraph stages inspect the proposal, retrieve evidence with at most two adaptive table searches, resolve citations against Chroma, and compare supported numeric inputs with historical Table 4 and Table 6 cells. A supported violation can recommend `revise-and-recheck`; unknown or incomplete cases route to `specialist-review`. Historical SATISFIED findings are not a statement of current legal compliance.

## Local versus Compose mode

| Capability | Local mode | Docker Compose mode |
|---|---|---|
| API and frontend | Two local processes, ports 8000 and 5500 | Separate API and frontend containers |
| Async queue | In-process bounded thread pool | Redis-backed queue and independent workers |
| Run persistence | Local SQLite file | Shared mounted SQLite volume |
| Corpus | Local PDF and persistent Chroma directory | Corpus indexer and named persistent index volume |
| Restart recovery / worker scaling | Not provided; work can be lost on process crash | Intended to be verified with Redis and scaled workers |
| Prometheus / Grafana | API `/metrics` is available; dashboards are not launched | Prometheus and Grafana services are configured |
| Deployment evidence | Does not establish containerization or Docker health | Requires successful Engine startup and container checks |

Local execution does not satisfy Docker deployment, Redis durability, independent worker scaling, container health, or Compose monitoring requirements. Do not report those as passed based on local runs.

## Demo checks

The exact live checks recorded for this checkout are in `FINAL_ACCEPTANCE_REPORT.md`; reference values and historical limitations are in `reference_case.md`. The browser automation packages are not bundled. If no browser automation facility is available, report browser interaction as blocked and do not infer UI submission from API tests alone.
