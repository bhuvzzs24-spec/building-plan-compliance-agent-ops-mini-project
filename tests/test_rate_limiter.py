from backend.app.rate_limiter import SlidingWindowRateLimiter


def test_sliding_window_limits_and_expires_requests(monkeypatch):
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
    now = [100.0]
    monkeypatch.setattr("backend.app.rate_limiter.time.monotonic", lambda: now[0])

    assert limiter.consume("client-a") == (True, 0)
    assert limiter.consume("client-a") == (True, 0)
    allowed, retry_after = limiter.consume("client-a")
    assert allowed is False
    assert retry_after == 60

    now[0] += 60
    assert limiter.consume("client-a") == (True, 0)
    assert limiter.consume("client-b") == (True, 0)
