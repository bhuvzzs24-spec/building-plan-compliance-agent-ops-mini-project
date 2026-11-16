# Performance plan and measurement status

## Declared SLO

The end-to-end target is p95 below 45 seconds from submission to a terminal run result. The graph has a 30-second execution timeout; the remaining budget allows queue delay and status polling. This is a declared target, not a measured result.

## Reproducible workload

The Locust task submits the historical narrow-road proposal, polls until a terminal result, and records a custom workflow-duration sample. The opt-in load profile uses a delayed deterministic OpenAI-compatible stub for queue/load plumbing. It does not return model usage, cost, or quality scores.

On a Docker-capable host with sufficient storage:

```bash
python3 -m pip install -r requirements-loadtest.txt
./evaluation/run_locust_compare.sh
```

The script validates service readiness, runs equivalent one-worker and three-worker workloads and stores CSV output in ignored `evaluation/artifacts/`. It does not tear down persistent volumes. It prints commands and output locations; use the actual Locust reports to record RPS, p50/p95, error rate, terminal duration, SLO misses and bottlenecks. Compare the first concurrency level that misses the SLO and the one-vs-three-worker throughput and p95. Do not infer these results from configuration.

## Results

**Not measured.** The current user requested no local Docker runtime due limited storage, and no remote Docker environment is available. The Locust comparison and worker scaling therefore remain blocked. No throughput, percentile, error-rate, concurrency, or cache-effect figure is claimed. See `DOCKER_VERIFICATION_REPORT.md` for environment limits and `FINAL_ACCEPTANCE_REPORT.md` for the declared acceptance boundary.
