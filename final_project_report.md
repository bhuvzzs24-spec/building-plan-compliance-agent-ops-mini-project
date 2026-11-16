# Building Plan Compliance Pre-Check — Final Project Report

## Problem and objective

Building proposals must be checked against multiple interacting planning provisions, tables, zoning conditions, and amendments. This prototype accepts structured building inputs, retrieves relevant text from an indexed historical PDF, verifies that citation text exists at the cited source and page, records a trace, and routes the case for specialist review. It is a research pre-check only and does not certify compliance or municipal approval.

## Architecture and design decisions

The service comprises a FastAPI contract/API, SQLite run/quarantine/feedback persistence, Redis list queue and worker, LangGraph workflow, Chroma retrieval, local deterministic word/bigram/trigram embeddings with lexical reranking, a static web frontend, Prometheus/Grafana configuration, and Docker Compose deployment. The workflow stages inspect proposal fields, plan separate provision searches, retrieve evidence, resolve citations against stored source/page/text, and route the result. The configured limits include up to six tool calls and a 30-second workflow timeout. A standalone local mode falls back to an in-process worker pool and is not durable across restarts.

The deterministic retrieval and no-provider architecture avoid uncommitted credentials and network model downloads. The tradeoff is that there is no genuine LLM tool selection, semantic entailment check, prompt evaluation, model safety layer, provider circuit breaker, or token/cost accounting.

## Corpus and regulatory limits

The indexed source is *Bangalore Mahanagara Palike Building Bye-Laws, 2003*, 84 extracted pages, 243 chunks. The local index manifest records source SHA-256 `0f2d473bd910733c21d24572ebb36f96c85d03c96bd5e8df9c58d41e7df49cf9`. The BBMP portal's official RMP 2015 zoning PDF and amendment directory were identified. The PDF identifies approval under a 2007 Government Order, but local acquisition timed out and amendment pages could not be inspected. Neither source is indexed; currentness and parcel applicability are unknown. Metadata and exact text re-resolution prove citation identity only. They do not prove currentness, legal applicability, semantic support, or completeness.

The historical reference passages were checked directly in the PDF: Table 4 (Bye-law 9.2) is on PDF page 22; Table 6 (Bye-laws 9.2 and 9.10) is on PDF page 24. The documented extracted values are recorded in `docs/reference_case.md` and must remain labeled historical. The initial end-to-end run did not cite those pages, leading to a lexical reranking improvement and regression test. After restarting the API, the reference proposal completed and returned page 22 under setbacks and page 24 under FAR/coverage. This verifies retrieval only; it does not calculate compliance.

## Evaluation

`python -m agents.rag.index_pdfs` completed on 16 November 2026: 84 pages, 243 chunks, zero failures, 0.809 seconds, 300.228 chunks/second on this machine. These are one-run local observations, not an SLO or throughput guarantee.

`python evaluation/run_evaluation.py` completed 20/20 retrieval scenarios with zero runtime errors after indexing. Every scenario returned passages. The dataset lacks labeled expected sources/outcomes, so source-hit and outcome accuracy are unavailable. The runner does not execute the two configured prompt variants and does not measure groundedness, semantic evidence support, faithfulness, hallucination, abstention accuracy, or compliance accuracy. The runner was corrected to exit nonzero if a scenario errors or is skipped.

The declared end-to-end SLO is p95 under 45 seconds. It has not been measured. No before/after model quality, cost-per-100-runs, Locust, concurrency, cache-effect, one-vs-three-worker, or throughput measurements are available. No fabricated metric is reported.

## Local integration verification

On 16 November 2026, the API was started locally with Uvicorn and a freshly built corpus index:

- `/health`: HTTP 200.
- `/health/ready`: HTTP 200, 243 indexed chunks.
- Valid proposal `POST /runs`: HTTP 202, then `completed`, four obligation findings, ten citations, six tool calls, `specialist-review`; the run includes Table 4/page 22 and Table 6/page 24 in separate findings.
- Invalid proposal: HTTP 422, field-level validation errors, quarantine ID, and `agent_started=false`.

The valid run was local fallback mode, not Redis-backed. It returned a source/page trace and exact citation checks. These results establish a backend-to-workflow-to-persisted-result path, not a full frontend-to-backend demonstration.

## Deployment, frontend and operations

`docker --version` and `docker compose version` could not run because Docker is not installed in this execution environment. Therefore Compose configuration/startup, container health, Redis integration/recovery, scaling, Prometheus/Grafana runtime, browser interaction, and Locust are BLOCKED here. No browser test or container-health result is claimed. The static frontend exists, but its full interactive behavior was not verified in a browser.

The project includes JSON API request logs/correlation IDs, Prometheus counters/histograms, health endpoints, a Grafana dashboard, run traces, rate limiting, a runbook, and incident-log history. Distributed OpenTelemetry, container resource metrics, outage recovery tests, and runtime dashboard checks remain incomplete or unverified.

## Team responsibility allocation

The authoritative allocation supplied for this project is recorded in `docs/contributions.md`, the README, synopsis, and demonstration guide:

- Bhuvana: platform, deployment and operations — A4, A7, D1, D3, D4, D5, D6, D8, L5, L6.
- Harshitha: agent workflow and backend logic — F3, F6, F7, A1, A2, A3, A5, L4.
- Sloka: RAG, corpus and evaluation — F4, F5, L1, L2, L3, D2, demonstrations 2 and 10.
- Saanvi: frontend, testing and integration, and remaining shared demos/QA.

No student-specific implementation or commit authorship is inferred. The official assignment PDF named in the task was not present in the workspace or repository checkout, so exact rubric wording for the identifiers could not be transcribed or checked.

## Remaining limitations

The workflow retrieves rather than substantively adjudicates compliance. It currently sends every case to specialist review. It does not compute rule comparisons/findings such as SATISFIED or VIOLATED, validate conflicting or applicable rules, or support current property decisions. LLMOps requirements, provider handling, injection/toxicity controls, Redis/worker runtime, full frontend path, performance evidence, clean Docker startup, and all ten demos are not complete. See `FINAL_ACCEPTANCE_REPORT.md` for criterion-level status and commands.
