# Building Plan Compliance Pre-Check

A FastAPI and LangGraph prototype for evidence retrieval from building-rule PDFs. It validates structured proposals, runs targeted searches for setback, road-width/height, FAR/coverage, and permitted-use evidence, checks that citations resolve to stored passages, and routes results for professional review.

> This service is not an approval system and does not certify compliance. Its indexed corpus snapshot is historical and has not been confirmed as the complete current rule set for a property. The application therefore routes every run to specialist-review.

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
2. provision_discovery_agent chooses the corpus-search tool for distinct obligations and looks up citation locations. It is capped at six tool calls; the whole workflow has a 30-second timeout.
3. evidence_verification_agent checks each citation against exact stored source, page, and text, then routes the run.

Available tools are lookup_request_fields, search_corpus, and lookup_clauses_by_location. Chroma uses a deterministic offline hashed word/bigram/trigram embedding named local_hash_ngrams_v1; it does not download or call an embedding provider. This is a low-cost lexical baseline and its relevance must be measured.

Citation resolution proves only that cited text exists in the indexed collection. The system does not verify legal currentness or semantic support, detect every conflicting provision, or assess all site-specific plan dimensions. It therefore never returns compliance clearance from the current corpus. Missing evidence, incomplete site dimensions, and unverified applicability are routed to specialist review.

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

The current evaluation runner is retrieval/citation-metadata only. It does not run an LLM, execute the two prompt variants, or compute groundedness, faithfulness, semantic support, or hallucination rate. No A/B score or accuracy claim is made.

The load test measures submit-to-terminal-result time, not just submission latency:

~~~bash
python -m pip install locust
locust -f evaluation/locustfile.py --host http://localhost:8000
~~~

Declared SLO: p95 below 45 seconds end to end. The workflow timeout is 30 seconds; the remainder allows queue wait and polling. No Locust result or worker-scaling result is claimed until Docker is run and the load test is recorded. This application has no external LLM provider, so provider token/cost measurements and an LLM-stub comparison are not applicable to the current implementation.

## Observability and operations

API requests emit JSON logs with correlation ID, normalized route, status, and duration. Run records persist the correlation ID and tool trace. Prometheus scrapes API and worker health/metrics. The Grafana dashboard is provisioned from observability/grafana/dashboards.

See docs/runbook.md for failure procedures and the development incident log. docker-compose.yml defines API, worker, Redis, corpus indexer, frontend, Prometheus, and Grafana services with health checks and shared state volumes.

## Regulatory source status

The local PDF is Bangalore Mahanagara Palike Building Bye-Laws 2003, not the 2017 Karnataka Model Building Bye-Laws claimed in older project notes. The source register records official links and the need to ingest/review the zoning corpus and subsequent amendments before current-property use. See docs/regulation_sources.md.

## Deliberately unimplemented requirements

This is an improved pre-check prototype, not an implementation of all 22 rubric requirements. It does not yet provide an LLM prompt A/B run, TruLens-equivalent semantic metrics, toxicity screening, token/cost attribution, a provider circuit breaker, OpenTelemetry export, per-container resource dashboard, measured load-test/scaling results, or measured caching/rate-limit effects. Do not present these as complete. The assignment says all 22 are not expected; prioritize a stable valid-request demo, evidence trace, difficult multi-rule case, honest escalation, and clear report.

## Project structure

- backend/app/: FastAPI, persistent run/quarantine/feedback store, queue, worker
- agents/workflow.py: LangGraph planning, retrieval, and evidence verification
- agents/rag/: offline embeddings, PDF parsing/chunking, Chroma indexing/retrieval
- data/bye_laws/: source PDFs
- evaluation/: 20-scenario configuration, retrieval runner, load test
- observability/: Prometheus configuration and Grafana dashboard
- docs/: source register, reference case, runbook, final report
- tests/: API, workflow, evaluation-configuration, and RAG tests
