# Building Plan Compliance Pre-Check — Final Project Report

## Problem and objectives

Preliminary building-plan review requires locating interacting rules and comparing proposal values against them. This project accepts structured building inputs, retrieves evidence from a locally indexed historical PDF corpus, checks citations against stored source passages, performs supported historical numerical comparisons, and records a traceable result. It is a pre-check service, not municipal approval or legal advice.

## Architecture and agent topology

FastAPI validates requests and stores run, feedback and quarantine data in SQLite. LangGraph hands work through proposal planning, provision discovery, and evidence verification. Agents can inspect proposal fields, search the corpus, and locate clauses. Retrieval uses Chroma and local deterministic hashed word/bigram/trigram vectors; no remote embedding model is required. The workflow has bounded steps, tool calls, retries and wall-clock time. API-local development mode uses a bounded thread pool; Compose mode defines Redis and independent workers with idempotent enqueue/acknowledgement and recovery logic.

For supported historical cases, parsed Table 4 and Table 6 values are compared with submitted setbacks, coverage and FAR only when the relevant source/page/table cell and proposal dimensions can be tied to evidence. Findings include input, threshold, comparison, status, citation and justification. Missing or unsupported evidence remains unresolved. Verified historical violations can recommend revise-and-recheck; unknown applicability/currentness routes to specialist review. No finding is a determination of present legal compliance.

An optional OpenAI-compatible provider can review semantic support. Prompts are versioned; structured outputs, input safeguards, bounded retries, a process-local circuit breaker, fallback routing, provider token reporting and optional configured-rate cost estimates are implemented. No provider is configured in the verified environment, so provider-generated findings, prompt comparison scores, tokens and costs were not measured.

## Corpus and RAG

The indexed source is *Bangalore Mahanagara Palike Building Bye-Laws, 2003* (84 extracted pages, 243 chunks; hash in `data/index_manifest.json`). The local PDF contains Table 4 (Bye-law 9.2) on PDF page 22 and Table 6 (Bye-laws 9.2 and 9.10) on page 24. These separate passages are retrieved for the documented 200 m², 10 m × 20 m, 6 m road, 9 m height reference case. The source is historical and does not establish current zoning, amendments, parcel jurisdiction, or applicability. Official-source discovery and limitations are tracked in `docs/regulation_sources.md`.

The indexer preserves source/page metadata, table context, source hashes, chunk counts, timing and failures. Re-indexing is idempotent. The latest retrieval evaluation processed 20/20 scenarios with 0 runtime errors; outcome accuracy is unavailable because the dataset has no labeled expected outcomes, and semantic support was not measured by that runner.

## LLMOps and evaluation

`evaluation/run_prompt_ab.py` executes both versioned prompt variants and a model-as-judge comparison for groundedness, context relevance, faithfulness and hallucination rate when an actual provider is configured. No provider was available, so the command exited without scores. No before/after quality improvement, cost per 100 runs, token usage, or quality trend is claimed. Provider metrics and the delayed load-test stub are explicitly distinguished; the stub produces no usage or quality data.

## Application and local verification

The local launcher serves the website at `localhost:5500`, API at `localhost:8000`, reuses an unchanged local index, and avoids dependency downloads unless installation is explicitly requested. A local smoke path returned healthy/readiness HTTP 200, accepted a valid request with HTTP 202, completed a run with six historical comparisons and citations, and polled the result. A below-limit proposal produced violation findings and revise-and-recheck. Injection-like input was guarded and escalated. Malformed input returned 422, quarantine metadata, field errors and `agent_started=false`. The frontend static page returned HTTP 200; browser-driven form interaction was not run.

`python3 -m pytest -q` passed 47 tests. Python compile checks, frontend JavaScript syntax checks, startup/load-script shell syntax checks, and Compose configuration validation passed. See `FINAL_ACCEPTANCE_REPORT.md` for exact commands, demonstrations and statuses.

## Deployment, operations and performance

Compose defines the API, worker, Redis, corpus indexer, frontend, Prometheus and Grafana services. The default and load-test overlay configurations validate with `docker compose config --quiet`. Docker images and containers were not built or started because the user directed that local Docker not run due limited storage; no remote Docker environment was attached. Container health, Redis processing, scaling, dashboards, and end-to-end Docker flows remain blocked.

The declared end-to-end SLO is p95 below 45 seconds. Locust and a delayed deterministic LLM stub are provided for a one- vs three-worker comparison. No RPS, p50/p95, error rate, bottleneck, SLO miss point, caching effect, or scaling result was measured. The results must be collected on a Docker-capable host; see `docs/performance.md` and `DOCKER_VERIFICATION_REPORT.md`.

## Team contribution responsibility

The authoritative assignment allocation is recorded in `docs/contributions.md`, README, synopsis, and the acceptance report: Bhuvana owns platform/deployment/operations; Harshitha owns agent workflow/backend logic; Sloka owns RAG/corpus/evaluation; Saanvi owns frontend/testing/integration and remaining QA. This lists responsibility areas only and does not infer commit authorship or individual implementation history.

## Limitations and conclusion

The current corpus is historical and incomplete for present-day legal decisions; semantic provider evaluation, browser automation, Docker runtime, Redis worker scaling, monitoring runtime, and load measurements remain unverified. The application can be demonstrated locally for evidence-grounded historical checks, but it is not ready for Docker runtime acceptance or full assignment sign-off. Final criteria and readiness are in `FINAL_ACCEPTANCE_REPORT.md`.
