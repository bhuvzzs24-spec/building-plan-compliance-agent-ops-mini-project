# Performance plan and results

## Declared SLO

Before load measurement, the target is p95 below 45 seconds from request submission to a terminal workflow result. The graph timeout is 30 seconds; the additional 15 seconds allow queue delay and status polling. The target concerns a working run, not only the fast HTTP 202 response.

## Method

Run Locust against the Compose stack with the API and Redis-backed agent-worker service. The Locust task submits a valid narrow-road proposal, polls until a terminal result, and records a custom end-to-end WORKFLOW sample. The test uses the application's local deterministic embedder and no external LLM provider. Scale workers using Compose's --scale option and compare throughput and p95 at identical user/load settings.

Example command after the stack is running:

    locust -f evaluation/locustfile.py --host http://localhost:8000 --headless -u 10 -r 2 --run-time 2m --csv=work/locust-baseline

Repeat with three workers and the same concurrency/ramp. Include RPS, p50, p95, first concurrency level that misses the SLO, and the responsible bottleneck in this document after measurement.

## Measurement status

Not measured in this development environment: Docker Desktop's Linux engine was not running. No RPS, p50/p95, failure-concurrency, or worker-scaling value is claimed.
