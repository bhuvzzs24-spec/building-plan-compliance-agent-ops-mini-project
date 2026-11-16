# Demonstration guide and recorded results

Run commands from the repository root. The checked-in corpus is historical. No output is municipal approval or a determination of current legal compliance.

## Reproduce the local no-Docker path

```bash
./scripts/start_local.sh
```

Open `http://localhost:5500`. The API and OpenAPI docs are at `http://localhost:8000` and `/docs`. The launcher reuses an unchanged index and starts the local in-process queue. For manual API verification:

```bash
curl -i http://127.0.0.1:8000/health/ready
curl -i -H 'Content-Type: application/json' -d '{"building_use":"residential","plot_area":200,"road_width":6,"proposed_height":9,"zone":"Residential R1","development_area":"A","site_width":10,"site_depth":20,"proposed_left_setback":1.5,"proposed_right_setback":1.5,"proposed_front_setback":4,"proposed_rear_setback":3,"proposed_coverage_percent":60,"proposed_far":0.7}' http://127.0.0.1:8000/runs
curl -i -H 'Content-Type: application/json' -d '{"building_use":"invalid","plot_area":-1}' http://127.0.0.1:8000/runs
```

Poll the `poll_url` returned from the valid request until `completed` or `failed`. Fetch the full run with `GET /runs/{run_id}`. The run includes citations, findings, obligations, trace, verification metadata, correlation ID, elapsed duration and configured limits. There is no model prompt or model cost because no model provider is configured. A complete reference input including proposed setback values is in `reference_case.md`.

For container demonstrations use `docker compose up --build`; scale with `docker compose up --build --scale agent-worker=3`. These require Docker Engine and were not executable in the verification environment described in `FINAL_ACCEPTANCE_REPORT.md`.

## Ten required demonstrations

| # | Scenario | Status at verification | Evidence / limitation |
|---:|---|---|---|
| 1 | Clean-clone Docker Compose startup | BLOCKED | This local run did not start Docker. No container health claim is made. |
| 2 | Valid proposal with cited findings and route | PASS (historical pre-check only) | Live local API returned 202 and completed. It produced six numerical findings: four Table 4 setback comparisons citing PDF page 22 and two Table 6 coverage/FAR comparisons citing page 24. Values at the historical thresholds were SATISFIED; recommendation remained specialist-review because currentness and applicability are unverified. |
| 3 | Full run reconstruction including prompt/cost | PARTIAL | API run reconstruction includes tool trace, retrieved passages, citation verification, duration and correlation. Prompt version and cost are unavailable because no LLM is configured. |
| 4 | Malformed proposal quarantined without agent | PASS | Live API returned 422, field-level errors, a quarantine ID and `agent_started=false`; the quarantine lookup returned the payload hash and errors. |
| 5 | Out-of-corpus proposal escalates | PARTIAL | Dedicated out-of-jurisdiction API proposal completed and returned specialist-review. The workflow does not detect corpus mismatch robustly and returned potentially irrelevant passages, so the explanation is not yet a reliable out-of-corpus detector. |
| 6 | Unsupported evidence causes re-search/escalation | PARTIAL | A unit test forced both table pages to be missed and verified targeted adaptive re-search within the tool budget. Semantic support verification and unsupported-evidence fault injection are not implemented, so the full demo is not passed. |
| 7 | Prompt injection guardrail behavior | PARTIAL | No LLM is called, so retrieved text cannot steer model reasoning. Input/output injection and toxicity safeguards are not implemented or tested. |
| 8 | Provider outage breaker/fallback | NOT APPLICABLE / PARTIAL | No provider is configured; circuit breaker behavior cannot be demonstrated. |
| 9 | Locust SLO, bottleneck and worker scale | BLOCKED | Docker/Redis and measured load infrastructure are unavailable; no load numbers are claimed. |
| 10 | Small-plot narrow-road reference case retrieves separate rules | PASS (historical numeric demo) | Live API returned page 22 and page 24 citations and compared 1.5/1.5/4/3 m setbacks, 60% coverage and 0.7 FAR to extracted historical limits of 1.5/1.5/4/3 m, 65% and 0.75. The proposal still routes to specialist review. |

Frontend static HTTP returned 200 and the page includes the form and result rendering code. Browser-driven form submission was not executed because Playwright/Puppeteer are not installed and the available Chromium process could not expose its debugging endpoint in this sandbox. Do not count this as a browser UI pass.

Do not present PARTIAL, BLOCKED, or NOT APPLICABLE as a successful demonstration. Update this table only with recorded executions and preserved output.
