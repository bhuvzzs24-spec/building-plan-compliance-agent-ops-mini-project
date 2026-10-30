from __future__ import annotations

import threading


class Metrics:
    """Small dependency-free Prometheus text exporter for the API process."""
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._durations: list[float] = []

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None):
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(self, name: str, value: float):
        if name != "http_request_duration_seconds":
            return
        with self._lock:
            self._durations.append(value)
            if len(self._durations) > 10_000:
                del self._durations[:5_000]

    def render(self) -> str:
        lines = [
            "# HELP building_compliance_up API process availability.",
            "# TYPE building_compliance_up gauge",
            "building_compliance_up 1",
        ]
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                label_text = ""
                if labels:
                    label_text = "{" + ",".join(
                        f'{key}="{val.replace(chr(34), "")}"' for key, val in labels
                    ) + "}"
                lines.append(f"building_compliance_{name}{label_text} {value:g}")
            durations = sorted(self._durations)
        if durations:
            count = len(durations)
            total = sum(durations)
            lines.append("# TYPE building_compliance_http_request_duration_seconds histogram")
            for bound in (0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")):
                label = "+Inf" if bound == float("inf") else str(bound)
                bucket_count = count if bound == float("inf") else sum(value <= bound for value in durations)
                lines.append(f'building_compliance_http_request_duration_seconds_bucket{{le="{label}"}} {bucket_count}')
            lines.append(f"building_compliance_http_request_duration_seconds_count {count}")
            lines.append(f"building_compliance_http_request_duration_seconds_sum {total:.9f}")
        return "\n".join(lines) + "\n"


metrics = Metrics()

