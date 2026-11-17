# Individual Testing Report
## Building Plan Compliance Pre-Check Service

**Team Member:** Saanvi  
**Role:** Frontend Integration, Testing, Monitoring and Performance Testing

### 1. F1 – REST API and Frontend Integration Testing

- Started the backend API and frontend successfully.
- Verified API health using `/health`.
- Verified readiness using `/health/ready`.
- Submitted building proposals through the frontend.
- Confirmed that findings, clauses, citations, verification results and workflow traces were displayed.
- Tested invalid proposal submission and confirmed that validation errors were returned and stored in quarantine.

**Result:** Successful.

### 2. F6 – Recommendation Route Display Testing

- Tested the recommendation display in the frontend.
- Confirmed that the workflow displayed the `specialist-review` recommendation.
- Verified that the recommendation included an explanation about regulatory currentness and property-specific applicability requiring professional confirmation.

**Result:** Successful.

### 3. F8 – Health Endpoints, Metrics and Structured Logs

- Verified `/health` returned a healthy status.
- Verified `/health/ready` returned ready status with 243 indexed chunks.
- Verified `/metrics` exposed Prometheus metrics.
- Checked API request counters and request-duration histograms.
- Confirmed structured logs included run IDs and correlation IDs.

**Result:** Successful for the tested endpoints and metrics.

### 4. D5 – Dashboard and Correlation ID Testing

- Verified correlation IDs in API responses and workflow logs.
- Confirmed that the same correlation ID appeared in the run submission and workflow completion logs.
- Checked Prometheus metrics for request counts, feedback submissions and retrieval-cache activity.

**Result:** Core correlation-ID and logging checks successful. Full Grafana dashboard operation was not independently verified.

### 5. D6 – Functional and Performance Testing

- Tested successful proposal submission and completed workflow retrieval.
- Tested invalid input and quarantine handling.
- Verified feedback submission and feedback summary.
- Executed 10 sequential readiness requests.

**Readiness response times:**
- Average: 14.36 ms
- Minimum: 9.12 ms
- Maximum: 46.95 ms

**Run performance:**
- Submission response: approximately 37.14 ms (request acceptance).
- Recorded workflow duration: 82.246 ms for one completed run.

**Limitation:** Locust was not installed, so concurrent load testing and full load-test performance validation were not completed.

### 6. D7 – Rate Limiting and Caching Testing

**Caching:**
- Identified an LRU cache with a maximum of 512 entries.
- Verified cache-hit and cache-miss metrics.
- Observed 8 cache hits and 4 cache misses.
- Calculated an observed cache hit rate of 66.7%.

**Rate limiting:**
- Identified a configured default limit of 30 submissions per minute.
- Confirmed that the limiter is applied to `POST /runs`.
- Temporarily configured a limit of 2 requests per minute.
- Three valid submissions returned HTTP 202 instead of the expected third-request HTTP 429.
- Restored the original default configuration.

**Result:** Cache implementation and metrics verified. Rate-limit enforcement remains inconclusive and requires further investigation.

### 7. Overall Conclusion

The frontend integration, functional checks, recommendation display, health endpoints, metrics and correlation-ID logging were tested successfully.

Basic sequential performance measurements were collected. Cache metrics were verified. Concurrent load testing, complete dashboard verification and actual rate-limit enforcement remain outstanding.

The service displayed a specialist-review recommendation rather than claiming confirmed legal compliance. This is consistent with the need for professional confirmation of regulatory currentness and applicability.

**Overall status:** Core assigned testing activities completed, with the above limitations documented.