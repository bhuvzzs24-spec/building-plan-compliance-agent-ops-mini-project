from __future__ import annotations

from collections import defaultdict, deque
import math
import threading
import time


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests = defaultdict(deque)
        self._lock = threading.Lock()

    def consume(self, client_key: str) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            history = self._requests[client_key]
            while history and history[0] <= cutoff:
                history.popleft()
            if len(history) >= self.limit:
                retry_after = max(1, math.ceil(history[0] + self.window_seconds - now))
                return False, retry_after
            history.append(now)
            if len(self._requests) > 10_000:
                expired = [key for key, items in self._requests.items() if not items or items[-1] <= cutoff]
                for key in expired:
                    self._requests.pop(key, None)
            return True, 0
