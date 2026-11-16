# Demonstration guide and recorded results

Run commands from the repository root. The checked-in corpus is historical. No output is municipal approval or a determination of current legal compliance.

## Reproduce the local verified path

```bash
python -m agents.rag.index_pdfs
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl -i http://127.0.0.1:8000/health/ready
curl -i -H 'Content-Type: application/json' -d '{"building_use":"residential","plot_area":200,"road_width":6,"proposed_height":9,"zone":"A - intensely developed area","site_width":10,"site_depth":20,"proposed_coverage_percent":60,"proposed_far":0.7}' http://127.0.0.1:8000/runs
curl -i -H 'Content-Type: application/json' -d '{"building_use":"invalid","plot_area":-1}' http://127.0.0.1:8000/runs
```

Poll the `poll_url` returned from the valid request until `completed` or `failed`. Fetch the full run with `GET /runs/{run_id}`. The run includes citations, findings, obligations, trace, verification metadata, correlation ID, elapsed duration and configured limits. There is no model prompt or model cost because no model provider is configured.

For container demonstrations use `docker compose up --build`; scale with `docker compose up --build --scale agent-worker=3`. These require Docker Engine and were not executable in the verification environment described in `FINAL_ACCEPTANCE_REPORT.md`.

## Ten required demonstrations

| # | Scenario | Status at verification | Evidence / limitation |
|---:|---|---|---|
| 1 | Clean-clone Docker Compose startup | BLOCKED | Docker executable/Engine is unavailable in the current environment. No container health claim is made. |
| 2 | Valid proposal with cited findings and route | PASS (limited pre-check) | After the lexical reranker, local API returned 202 and completed; four obligation findings and ten citations were returned. The justified route was specialist review due to the historical/incomplete corpus. No SATISFIED/VIOLATED legal determination is produced. |
| 3 | Full run reconstruction including prompt/cost | PARTIAL | API run reconstruction includes tool trace, retrieved passages, citation verification, duration and correlation. Prompt version and cost are unavailable because no LLM is configured. |
| 4 | Malformed proposal quarantined without agent | PASS | Local API returned 422, field-level errors, quarantine ID and `agent_started=false`. |
| 5 | Out-of-corpus proposal escalates | PARTIAL | Dedicated out-of-jurisdiction API proposal completed and returned specialist-review. The workflow does not detect corpus mismatch robustly and returned potentially irrelevant passages, so the explanation is not yet a reliable out-of-corpus detector. |
| 6 | Unsupported evidence causes re-search/escalation | BLOCKED | Citation identity is rechecked, but semantic support and adaptive alternate-strategy retries are not implemented. |
| 7 | Prompt injection guardrail behavior | PARTIAL | No LLM is called, so retrieved text cannot steer model reasoning. Input/output injection and toxicity safeguards are not implemented or tested. |
| 8 | Provider outage breaker/fallback | NOT APPLICABLE / PARTIAL | No provider is configured; circuit breaker behavior cannot be demonstrated. |
| 9 | Locust SLO, bottleneck and worker scale | BLOCKED | Docker/Redis and measured load infrastructure are unavailable; no load numbers are claimed. |
| 10 | Small-plot narrow-road reference case retrieves separate rules | PASS (retrieval scope) | Source PDF confirms Table 4 at PDF page 22 and Table 6 at page 24. After reranking, the local API completed with ten citations and included page 22 in the setbacks finding and page 24 in the FAR/coverage finding. It does not calculate compliance; values remain historical. |

Do not present PARTIAL, BLOCKED, or NOT APPLICABLE as a successful demonstration. Update this table only with recorded executions and preserved output.
