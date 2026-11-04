# Building Plan Compliance Pre-Check — Project Report

## Summary

This project is a runnable prototype for collecting potentially relevant building-rule evidence and routing a proposal for human review. It is not an approval system and does not determine legal compliance. Every run returns `specialist-review`, because the checked-in rule corpus is historical and incomplete for a current parcel-specific decision.

## Implemented

- FastAPI proposal contract with categorical, numeric, range, cross-field, and unknown-field validation.
- Rejected-request quarantine records containing a payload hash and field errors, without retaining the rejected body.
- Three-stage LangGraph workflow: request inspection and planning, targeted provision retrieval, and citation re-resolution against persisted source/page/text.
- Offline deterministic lexical embeddings and idempotent PDF indexing, including a source hash/index manifest and removal of stale corpus sources.
- Persistent SQLite run, quarantine, and feedback records; Redis queue and worker with local bounded-pool fallback.
- Correlation IDs, structured API logs, Prometheus metrics, health/readiness checks, rate limiting, bounded run time, and retry policy.
- Static frontend, Docker Compose services, Prometheus scrape configuration, Grafana provisioning, runbook, reference case, and Locust workload definition.

## Evidence and source limits

The bundled PDF is *Bangalore Mahanagara Palike Building Bye-Laws, 2003*. It is not the Karnataka Model Building Bye-Laws 2017 described by older project notes. The official zoning regulations and a verified consolidated set of later amendments are not in the indexed corpus. Currentness, parcel zoning, and legal applicability are therefore unverified. The source register and historic narrow-road case document the exact limits. Retrieved text and metadata can be checked, but semantic entailment is not.

## Validation

Validation performed on 29 October 2026:

- `python -m pytest -q`: **27 passed**.
- `python -m agents.rag.index_pdfs`: **84 pages, 243 chunks, zero indexing failures**; index build completed in 2.57 seconds at 94.69 chunks/second on this machine.
- Real-corpus API smoke check: readiness returned 200 with 243 chunks; a valid narrow-road request completed with four evidence obligations, eight resolved citations, and `specialist-review`.
- `python evaluation/run_evaluation.py`: **20/20 scenarios processed, zero execution errors**. It measures retrieval/citation metadata only, not prompt variants or semantic support.
- `docker compose config`: passed. Docker Engine was unavailable (`dockerDesktopLinuxEngine` pipe not found), so images, multi-container startup, worker scaling, Grafana, and Locust were not run.
- Frontend JavaScript syntax checks passed with Node.

A successful local test run does not prove current legal accuracy or full assignment-rubric completion. Deployment, load, scale, and dashboard behavior must be reported only after the relevant runtime checks have actually run.

## Assignment completion status

This submission prioritizes a valid end-to-end demo, evidence trace, failure routing, reproducible indexing, and transparent operations. It does not claim all 22 rubric items are complete. Specifically, it has no executed LLM prompt A/B comparison, semantic faithfulness/groundedness scores, toxicity screening, provider token/cost attribution, provider circuit breaker, OpenTelemetry traces, container resource dashboard, or measured load/scaling/cache/rate-limit results. See `README.md`, `docs/regulation_sources.md`, and `docs/runbook.md` for reproducible commands and remaining limits.

## Grade outlook

The implementation covers several demonstrable functional and operational requirements, but no one can guarantee a grade from repository inspection alone. Rubric interpretation, live demonstration, report quality, and instructor checks affect the result. The most grade-critical remaining work is a successful clean Docker startup plus execution evidence for the rubric's evaluation and operational requirements.
