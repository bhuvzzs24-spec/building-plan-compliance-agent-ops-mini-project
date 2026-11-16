# Final Acceptance Report

**Verification date:** 16 November 2026
**Repository:** `bhuvzzs24-spec/building-plan-compliance-agent-ops-mini-project`
**Local mode:** macOS, Python 3.13, no Docker
**Readiness verdict:** **READY WITH LIMITATIONS for local demonstration; NOT READY for Docker/deployment acceptance**

The central local API-to-LangGraph-to-Chroma-to-result path was executed successfully, including evidence-grounded historical numerical comparisons, citations, polling, a violation route, incomplete-data escalation and malformed-input quarantine. The static frontend server returned HTTP 200. Browser-driven interactions were not completed. Docker Engine, Redis workers, worker scaling, container health, Prometheus/Grafana runtime and load tests were not run. Local execution does not satisfy those requirements. This is a historical pre-check only and must not be represented as municipal approval or current legal compliance.

The official assignment PDF was not present in this checkout/task workspace. Requirement labels below use the user-supplied task descriptions provisionally; exact rubric wording remains unverified.

## 1. Requirement matrix

### Functional requirements

| ID | Provisional area | Status | Evidence / remaining gap |
|---|---|---|---|
| F1 | Proposal API and request/response contract | PASS (local path) | `backend/app/main.py`; live HTTP 202 submit and polling completed. |
| F2 | Strict validation and quarantine | PASS (tested) | Pydantic schema; malformed live request returned 422, field errors, quarantine ID, `agent_started=false`; quarantine metadata lookup succeeded. |
| F3 | Async runs and persistent state | PASS locally / PARTIAL overall | Local bounded thread pool, SQLite and polling worked. Local jobs are not crash-durable; Redis not run. |
| F4 | Regulatory corpus and RAG | PARTIAL | Historical Bangalore 2003 PDF indexed locally; no verified current zoning/amendment corpus. |
| F5 | Evidence retrieval and citations | PASS for reference pages / PARTIAL overall | Exact retrieved-text citation resolution; live reference returned Table 4 PDF page 22 and Table 6 page 24. Semantic support is not measured. |
| F6 | Findings and routing | PASS for supported historical numeric rules / PARTIAL overall | Six source-derived numeric comparisons; observed SATISFIED and VIOLATED outcomes. Currentness remains specialist-reviewed; feedback endpoints were not exercised here. |
| F7 | Frontend | PARTIAL | Frontend HTTP 200 and static form/assets checked. Browser-driven submission/display was unavailable. |
| F8 | Health, logs and metrics | PARTIAL | Live health/readiness and API metrics route available; local structured logs observed. Dashboard/trace runtime not tested. |

### Agent requirements

| ID | Provisional area | Status | Evidence / remaining gap |
|---|---|---|---|
| A1 | Distinct workflow stages and hand-offs | PARTIAL | LangGraph planner, discovery and verification nodes execute in sequence; not autonomous LLM agents. |
| A2 | Agent-selectable tools | PARTIAL | Proposal-field lookup, corpus search and citation-location lookup are distinct tools; no model selects tools. |
| A3 | Bounded/adaptive workflow | PASS locally / PARTIAL overall | Eight-call cap, 30-second timeout and up to two targeted table searches; adaptive recovery unit test passed. Crash cancellation and all timeout/retry cases not exercised. |
| A4 | Redis queue and independent workers | BLOCKED | Local mode only; Docker/Redis unavailable for this verification. |
| A5 | Evidence verification and routing | PARTIAL | Citation text re-resolved; semantic claim support is false/unavailable. Supported historical violations route to revise-and-recheck; incomplete cases to specialist-review. |
| A6 | Regulatory numeric findings | PASS for supported historical cells | Extracts Table 4 and Table 6 values from verified retrieved passages and compares supplied setbacks, coverage and FAR. Scope is limited to supported categories and historical pages. |
| A7 | Reliability/fallback | PARTIAL | In-process queue and bounded retrieval are present; worker crash recovery/provider breaker not verified or configured. |
| A8 | Safety/escalation | PARTIAL | Historical/currentness caveat and conservative routing are present; full injection/toxicity and conflict-analysis controls are unavailable without model path. |

### LLMOps requirements

| ID | Provisional area | Status | Evidence / remaining gap |
|---|---|---|---|
| L1 | Versioned prompts/provider | NOT IMPLEMENTED | No model provider configured or called. |
| L2 | Executed prompt A/B | NOT IMPLEMENTED | No prompt variants executed. |
| L3 | Groundedness/faithfulness/hallucination metrics | NOT IMPLEMENTED | Retrieval-only evaluation cannot measure semantic support. |
| L4 | Token/cost attribution | NOT APPLICABLE / UNAVAILABLE | No model calls; no tokens or costs fabricated. |
| L5 | Prompt safeguards | PARTIAL | No LLM input path; explicit toxicity/injection filter is not implemented. |
| L6 | Feedback quality monitoring | PARTIAL | Feedback storage/aggregation exists; sampled scoring and trend evaluation not measured. |

### Deployment requirements

| ID | Provisional area | Status | Evidence / remaining gap |
|---|---|---|---|
| D1 | Dockerized startup | BLOCKED | No Docker containers started in this local-mode verification. Prior Docker audit found daemon/socket unavailable and disk-full logs. |
| D2 | Corpus indexing/evaluation | PASS for execution / PARTIAL for quality | Index reuse succeeded; 20/20 retrieval scenarios ran without runtime errors. Labeled accuracy is unavailable. |
| D3 | Container health/dependencies | BLOCKED | Compose config was previously validated, but container readiness/health was not executed. |
| D4 | Prometheus/Grafana monitoring | BLOCKED | Local API `/metrics` answered; Prometheus/Grafana containers/dashboards were not run. |
| D5 | SLO, load and scaling | BLOCKED | No Locust, measured p95, concurrency limit, or one-vs-three-worker results. |
| D6 | Cache and rate limiting | PARTIAL | Retrieval cache and API limiter code exist; effect and load behavior not measured. |
| D7 | Browser UX/responsiveness | BLOCKED | No browser automation package was installed; sandbox Chromium debugging endpoint could not be started. |
| D8 | Runbook/recovery | PARTIAL | Runbook exists; container incident recovery and independent worker recovery not verified in this environment. |

## 2. Main implementation and evidence

- `scripts/start_local.sh`, `requirements-local.txt`, `docs/local_mode.md`: low-download local launcher, dependency import check, optional project-only install, index reuse, API/frontend startup and local-vs-Compose limitations.
- `agents/compliance.py`, `agents/workflow.py`: historical Table 4/Table 6 parsing and numeric comparisons, bounded adaptive retrieval, evidence citation association and conservative routing.
- `agents/rag/index_pdfs.py`: source-hash/index-presence reuse and opt-in `--force` re-index.
- `backend/app/main.py`: optional area category and proposed setback fields added to the API contract.
- `frontend/index.html`, `frontend/app.js`, `frontend/style.css`: area/setback inputs and structured findings/citations/verification rendering.
- `tests/test_compliance_workflow.py`, `tests/test_rag.py`: historical numeric outcomes, violation route, adaptive retrieval and index-reuse coverage.
- `README.md`, `docs/demo_guide.md`, `docs/reference_case.md`, `docs/local_mode.md`: local workflow and limits.

## 3. Exact commands and results

Commands executed from the repository root on 16 November 2026:

```text
python3 -m pytest -q
32 passed in 1.67s

python3 -m agents.rag.index_pdfs
PASS: unchanged source reused; 84 pages, 243 indexed chunks, 243 reused, 0 rebuilt, 0 failures

python3 evaluation/run_evaluation.py
PASS for execution: 20/20 scenarios returned retrieval results, 0 runtime errors
Outcome accuracy: unavailable (the dataset does not provide verified labeled outcomes)

node --check frontend/app.js
PASS

bash -n scripts/start_local.sh
PASS

./scripts/start_local.sh
PASS: API readiness returned 200; frontend and API processes stayed running locally
```

Additional live HTTP checks against the running local stack:

- `GET /health`: HTTP 200.
- `GET /health/ready`: HTTP 200, 243 indexed chunks.
- `GET http://localhost:5500/`: HTTP 200.
- Valid reference proposal: HTTP 202, `queue_mode=local`, polling reached `completed`; 17 passages resolved to citations; six numerical findings: left/right/front/rear setbacks SATISFIED against 1.5/1.5/4/3 m on page 22, coverage SATISFIED against 65% and FAR SATISFIED against 0.75 on page 24. Route was `specialist-review` because regulatory currentness/applicability is unchecked.
- Violating proposal: polling reached `completed`; below-minimum left setback and above-limit coverage/FAR were VIOLATED; route was `revise-and-recheck`.
- Incomplete proposal: polling reached `completed`; missing numeric proposal values were UNRESOLVED and route was `specialist-review`.
- Malformed proposal: HTTP 422; field-level errors, quarantine identifier and `agent_started=false`. `GET /quarantine/{id}` returned the payload hash and error metadata.
- `GET /metrics`: HTTP 200.

No tests were weakened or deleted. No Docker data or personal files were removed.

## 4. Docker and service health

**BLOCKED / NOT RUN for the current local-mode verification.** No API/worker/Redis/indexer/frontend/Prometheus/Grafana containers were started. This report makes no Compose health, clean-clone container startup, Redis durability, worker scaling, or Docker storage recovery claim. The earlier Docker audit recorded daemon/socket unavailability and Docker Desktop disk-full errors; see `DOCKER_VERIFICATION_REPORT.md`. Dockerfiles and Compose files remain in the repository.

## 5. Browser verification

**BLOCKED.** The frontend static server returned HTTP 200, JavaScript syntax passed, and HTML contains the proposal fields and result UI. Playwright and Puppeteer were not installed. An existing cached Chromium binary was tried but did not expose a CDP debugging endpoint from this sandbox. No claim is made that browser form submission or result rendering passed.

## 6. Ten required demonstrations

| # | Scenario | Status | Recorded result |
|---:|---|---|---|
| 1 | Clean-clone Docker Compose startup | BLOCKED | Docker Engine/container startup not run. |
| 2 | Valid proposal, citations and justified recommendation | PASS (local historical pre-check) | HTTP 202 and completed run; source-derived findings cite pages 22/24; specialist route due to currentness limitation. |
| 3 | Reconstruct run including tools, passages, prompt, latency and cost | PARTIAL | Run ID returns trace, passages, citations, verification and duration. Prompt version/tokens/cost unavailable because no model is configured. |
| 4 | Malformed data quarantined before agent | PASS | HTTP 422, field errors, quarantine metadata, `agent_started=false`. |
| 5 | Out-of-corpus proposal escalates | PARTIAL | General specialist routing exists; robust corpus-mismatch classification was not live-verified. |
| 6 | Unsupported evidence triggers re-search/escalation | PARTIAL | Unit test forced missing table pages and observed adaptive re-search. Semantic support fault injection and verification remain unavailable. |
| 7 | Prompt injection guardrail | PARTIAL | No model call can consume retrieved text as instructions, but explicit input/output injection safeguards were not implemented/tested. |
| 8 | Provider outage breaker/fallback | NOT APPLICABLE / PARTIAL | No provider configured; no breaker demonstration. |
| 9 | Locust SLO, bottleneck and worker scaling | BLOCKED | No Docker/Redis load run or measured load results. |
| 10 | Narrow-road small-plot case retrieves separate provisions | PASS (local historical numeric demo) | Live run retrieved Table 4 page 22 and Table 6 page 24, compared setbacks/coverage/FAR to parsed historical cells, and routed specialist review. |

## 7. Evaluation, SLO and limitations

The declared target remains end-to-end p95 below 45 seconds. It was not measured. The 20-scenario evaluation measures retrieval execution, not expected-outcome accuracy or semantic evidence support. RPS, p50/p95, error rate under load, concurrency failure point, one-vs-three-worker throughput, cache benefit and cost per 100 runs are unavailable and must not be inferred from the local smoke run.

Historical numerical comparisons are deliberately limited: Table 4 page 22 only covers up to 9.5 m and supported uses; Table 6 page 24 requires an explicitly supported development-area category, use, plot band and road band. Conflicting rules, current amendments, zoning applicability and semantic support are not established. Unresolved values route to a specialist. No municipal approval is issued.

## 8. Team ownership

This follows the authoritative team responsibility correction. Ownership records responsibility areas only and does not invent authorship or claim who wrote a particular commit.

| Contributor | Assigned responsibility |
|---|---|
| Bhuvana | Platform, deployment and operations: A4, A7, D1, D3, D4, D5, D6, D8, L5, L6 |
| Harshitha | Agent workflow and backend logic: F3, F6, F7, A1, A2, A3, A5, L4 |
| Sloka | RAG, corpus and evaluation: F4, F5, L1, L2, L3, D2; demonstrations 2 and 10 |
| Saanvi | Frontend, testing and integration; remaining shared demonstrations and QA |

## 9. Git details

Commit/push for the current verified edits: pending. No force-push is permitted. The final remote SHA must be filled after push verification.

## 10. Final verdict

**READY WITH LIMITATIONS for local demonstration only. NOT READY for full assignment/deployment acceptance.** The local valid-request-to-agent-to-cited-result path and historical reference comparisons passed. Browser interaction remains blocked, and Docker/Redis/worker scaling/monitoring/load acceptance remains unverified. Do not describe local mode as satisfying Docker deployment or worker-scaling criteria.
