# Building Plan Compliance Pre-Check

A FastAPI and LangGraph prototype for evidence retrieval from building-rule PDFs. It validates structured proposals, runs targeted searches for setback, road-width/height, FAR/coverage, and permitted-use evidence, checks that citations resolve to stored passages, and routes results for professional review.

> This service is not an approval system and does not certify compliance. The checked-in Bangalore corpus is historical and is not confirmed as the current complete rule set. It can compare supported values against retrieved historical table cells, but current legal applicability remains for a specialist to confirm.

## Run from a clean clone

Requirements: Docker Engine or Docker Desktop with Compose v2.

~~~bash
git clone https://github.com/bhuvzzs24-spec/building-plan-compliance-agent-ops-mini-project.git
cd building-plan-compliance-agent-ops-mini-project
docker compose up --build
~~~

Compose uses the checked-in .env.example as runtime configuration. It builds the API/worker image, indexes the included PDF corpus into a named volume, starts Redis, the API, one worker, the frontend, Prometheus, and Grafana. Stop with Ctrl+C. To scale workers:

~~~bash
docker compose up --build --scale agent-worker=3
~~~

Open the frontend on port 5500, API documentation on port 8000/docs, Prometheus on port 9090, and Grafana on port 3000. Grafana is configured for anonymous read-only access for this local demonstration stack; do not expose these ports to an untrusted network.

The stack keeps queued jobs in Redis and run/feedback records in a shared SQLite volume. With Redis unavailable in a local non-Compose run, the API falls back to a bounded in-process worker pool. That fallback is not durable across process restarts.

For provider-backed semantic verification, configure `LLM_BASE_URL`, `LLM_MODEL`, and `LLM_API_KEY` in an untracked `.env` file or the shell environment before starting Compose. The provider must implement the OpenAI-compatible `/chat/completions` API. The application uses bounded retries, a process-local circuit breaker, strict JSON output validation, and specialist-review fallback. Provider token counts are recorded only when returned by the provider. Cost is labeled as an estimate and is emitted only when both `LLM_INPUT_USD_PER_MILLION` and `LLM_OUTPUT_USD_PER_MILLION` are supplied. Never commit provider credentials.

The delayed deterministic model stub is only for fault injection/load-test plumbing. It deliberately omits token counts and price data, so it cannot produce model quality, token, or cost results.

## Lightweight local demo on macOS (no Docker)

The local launcher uses already-installed Python packages when available, reuses an unchanged local Chroma index, and starts the API plus static frontend. It does not install dependencies unless explicitly requested.

~~~bash
./scripts/start_local.sh
~~~

Open [http://localhost:5500](http://localhost:5500); API docs are at [http://localhost:8000/docs](http://localhost:8000/docs). The launcher binds to loopback, disables Redis, checks both ports, and stops both processes with Ctrl+C. It indexes `data/bye_laws/` before startup; an unchanged source/index manifest is reused. If packages are missing, the script exits with the missing-import notice and no download. To opt into a project-local install only, run `INSTALL_LOCAL_DEPS=1 ./scripts/start_local.sh`; this uses `.venv` and `requirements-local.txt`.

Local mode uses a four-thread in-process queue and SQLite run state. Jobs are asynchronous while the process is alive, but queued work is not durable across process crashes and this mode does not verify Redis, independent worker scaling, Docker health, Prometheus/Grafana, or container networking. Keep Compose files for those deployment checks on a Docker-capable host; local mode is not evidence that Docker requirements passed. See [docs/local_mode.md](docs/local_mode.md).

## Local development

Create and activate a Python virtual environment, then install dependencies:

~~~bash
python -m venv .venv
~~~

Windows PowerShell:

~~~powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
~~~

macOS/Linux:

~~~bash
source .venv/bin/activate
python -m pip install -r requirements.txt
~~~

Index the local PDFs, then start the API:

~~~bash
python -m agents.rag.index_pdfs
python -m uvicorn backend.app.main:app --reload
~~~

Serve the static frontend separately:

~~~bash
python -m http.server 5500 --directory frontend
~~~

For local runs, set REDIS_URL to a reachable Redis instance to use the queue. Without it, runs execute in the API process pool. Local run state defaults to data/run_state.sqlite3; the vector index defaults to data/chroma_db.

## Proposal contract

POST /runs accepts JSON with:

- building_use: residential, commercial, mixed-use, or institutional
- plot_area: positive square metres, at most 2,000,000
- road_width: positive metres, at most 200
- proposed_height: positive metres, at most 300
- zone: non-empty label, at most 100 characters
- site_width, site_depth: optional positive metres; both are needed for setback-table review
- proposed_coverage_percent: optional value from 0 through 100
- proposed_far: optional value from 0 through 50
- development_area: optional historical Table 6 category A, B or C
- proposed_left_setback, proposed_right_setback, proposed_front_setback, proposed_rear_setback: optional metres

Unknown fields, missing required fields, invalid categories, out-of-range values, and impossible site dimensions are rejected at ingestion. The API returns HTTP 422, a quarantine ID, field-level errors, and agent_started=false. The quarantine record stores only a payload hash and error fields, not the original proposal body.

Example:

~~~json
{
  "building_use": "residential",
  "plot_area": 200,
  "road_width": 6,
  "proposed_height": 9,
  "zone": "A - intensely developed area",
  "site_width": 10,
  "site_depth": 20,
  "development_area": "A",
  "proposed_left_setback": 1.5,
  "proposed_right_setback": 1.5,
  "proposed_front_setback": 4,
  "proposed_rear_setback": 3,
  "proposed_coverage_percent": 60,
  "proposed_far": 0.7
}
~~~

This is the historical-corpus scenario documented in docs/reference_case.md. It tests multi-rule retrieval and is not a current legal determination.

## API

- GET /health: API process health
- GET /health/ready: readiness check for indexed Chroma chunks
- GET /metrics: Prometheus-compatible request/run counters and latency histogram
- POST /check: validate proposal fields only
- POST /runs: enqueue a run and return its ID immediately
- GET /runs/{run_id}: poll status, findings, citations, verification limits, and tool trace
- GET /quarantine/{quarantine_id}: retrieve hashed rejection metadata and field errors
- POST /runs/{run_id}/feedback: persist caller feedback and a reason
- GET /feedback/summary: aggregated feedback counts

Completed responses include an evidence item per searched provision, citation records, a correlation ID, call/step limits, and a trace of query text, tool calls, result counts, timings, and citation re-resolution.

## Agent/workflow design

The LangGraph workflow has separate responsibilities and explicit hand-offs:

1. retrieval_planner_agent inspects request fields and plans targeted searches.
2. provision_discovery_agent searches distinct obligations, performs up to two targeted table searches when evidence is missing, and resolves citation locations. The graph is capped at eight tool calls; the whole workflow has a 30-second timeout.
3. evidence_verification_agent checks each citation against exact stored source, page, and text, then routes the run.

Available tools are lookup_request_fields, search_corpus, and lookup_clauses_by_location. Chroma uses a deterministic offline hashed word/bigram/trigram embedding named local_hash_ngrams_v1; it does not download or call an embedding provider. This is a low-cost lexical baseline and its relevance must be measured.

Citation resolution proves only that cited text exists in the indexed collection. For supported residential/commercial proposals up to 9.5m, the workflow extracts matching historical Table 4 setback cells and Table 6 coverage/FAR cells from verified passages, compares supplied proposal measurements, and reports SATISFIED, VIOLATED or UNRESOLVED findings. A supported violation can recommend revise-and-recheck. Missing dimensions or table evidence remain unresolved; currentness and property-specific applicability are always stated as limitations. No route represents municipal approval or legal clearance.

## Indexing and freshness

Place authority-issued PDFs under data/bye_laws, then run:

~~~bash
python -m agents.rag.index_pdfs
~~~

The pipeline parses pages, chunks with source/page metadata, embeds locally, replaces stale chunks for each source, removes sources no longer present, and writes data/index_manifest.json with source SHA-256 hashes, pages/chunks, build time, elapsed time, throughput, and failures. Re-embedding uses the same idempotent CLI. The manifest describes indexed bytes; it does not establish that a source is legally current.

## Evaluation and tests

Run automated checks:

~~~bash
python -m pytest -q
~~~

Run the existing retrieval evaluation:

~~~bash
python evaluation/run_evaluation.py
~~~

`python evaluation/run_evaluation.py` measures retrieval execution and citation metadata, not labeled compliance accuracy. `python evaluation/run_prompt_ab.py` executes both configured prompt variants and a model-as-judge score for groundedness, context relevance, faithfulness and hallucination rate. It requires an actual configured provider and reports provider usage plus rate-based cost estimates when available. With no credentials/provider it exits without publishing scores. Judge scores are model estimates, not human gold labels. No provider is configured in this checkout, so prompt A/B quality scores and model token/cost totals have not been measured.

The load test measures submit-to-terminal-result time, not just submission latency:

~~~bash
python -m pip install -r requirements-loadtest.txt
./evaluation/run_locust_compare.sh
~~~

The comparison script builds and starts the optional delayed-stub Compose profile, then runs the same Locust workload with one and three workers. It writes raw CSV files to ignored `evaluation/artifacts/`. It does not tear down or remove volumes. Locust is optional and separate from the local app dependencies.

Declared SLO: p95 below 45 seconds end to end. The workflow timeout is 30 seconds; the remainder allows queue wait and polling. No Locust result or worker-scaling result is claimed until Docker is run and the load test is recorded. The application supports an optional OpenAI-compatible provider. No provider credentials are configured in this checkout, so model prompt A/B scores, provider token counts and cost remain unmeasured. The delayed stub is for queue/load plumbing only and intentionally reports no usage or quality scores.

## Observability and operations

API requests emit JSON logs with correlation ID, normalized route, status, and duration. Run records persist the correlation ID and tool trace. Prometheus scrapes API and worker health/metrics. The Grafana dashboard is provisioned from observability/grafana/dashboards.

See docs/runbook.md for failure procedures and the development incident log. docker-compose.yml defines API, worker, Redis, corpus indexer, frontend, Prometheus, and Grafana services with health checks and shared state volumes.

## Regulatory source status

The local PDF is Bangalore Mahanagara Palike Building Bye-Laws 2003, not the 2017 Karnataka Model Building Bye-Laws claimed in older project notes. The source register records official links and the need to ingest/review the zoning corpus and subsequent amendments before current-property use. See docs/regulation_sources.md.

## Remaining verification limits

Provider-backed A/B and semantic evaluation require credentials and have not been executed in this environment. Docker Compose configuration is validated without starting containers; Docker runtime, Redis-backed processing, scaled workers, Prometheus/Grafana runtime, and Locust measurements still require a Docker-capable machine. Browser-driven interactions have not been executed: Playwright/Selenium are not installed, Chrome aborts in headless mode with exit 134, and SafariDriver requires administrator authentication to enable remote automation. No browser package or browser binary was downloaded. See [WEBSITE_VERIFICATION_REPORT.md](WEBSITE_VERIFICATION_REPORT.md) for the exact checks and blocker. The historical corpus remains incomplete for current-property decisions, and the app preserves specialist escalation for unresolved currentness/applicability.

## Project structure

- backend/app/: FastAPI, persistent run/quarantine/feedback store, queue, worker
- agents/workflow.py: LangGraph planning, retrieval, and evidence verification
- agents/rag/: offline embeddings, PDF parsing/chunking, Chroma indexing/retrieval
- data/bye_laws/: source PDFs
- evaluation/: 20-scenario configuration, retrieval runner, load test
- observability/: Prometheus configuration and Grafana dashboard
- docs/: source register, reference case, runbook, final report
- tests/: API, workflow, evaluation-configuration, and RAG tests

## Team responsibility allocation

The authoritative assignment supplied for this project allocates responsibility as follows. This records responsibility areas only; it does not assert individual Git authorship or that each person completed every item.

| Contributor | Assigned areas |
|---|---|
| Bhuvana | Platform, deployment and operations: A4, A7, D1, D3, D4, D5, D6, D8, L5, L6 |
| Harshitha | Agent workflow and backend logic: F3, F6, F7, A1, A2, A3, A5, L4 |
| Sloka | RAG, corpus and evaluation: F4, F5, L1, L2, L3, D2, demonstrations 2 and 10 |
| Saanvi | Frontend, testing and integration; remaining shared demonstrations and QA |

See [docs/contributions.md](docs/contributions.md). The official assignment PDF was not present in the checkout or task workspace, so exact rubric wording for F/A/L/D identifiers remains unverified; see `FINAL_ACCEPTANCE_REPORT.md`.
