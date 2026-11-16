from __future__ import annotations

import threading
import time
import sys


class Metrics:
    """Small dependency-free Prometheus text exporter for the API process."""
    def __init__(self):
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._observations: dict[str, list[float]] = {}
        self._gauges: dict[str, float] = {}
        self._started = time.monotonic()

    def increment(self, name: str, value: float = 1.0, labels: dict[str, str] | None = None):
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    def observe(self, name: str, value: float):
        with self._lock:
            values = self._observations.setdefault(name, [])
            values.append(float(value))
            if len(values) > 10_000:
                del values[:5_000]

    def set_gauge(self, name: str, value: float):
        with self._lock:
            self._gauges[name] = float(value)

    def render(self, service: str = "api") -> str:
        lines = [
            f"# HELP building_compliance_{service}_up {service} process availability.",
            f"# TYPE building_compliance_{service}_up gauge",
            f"building_compliance_{service}_up 1",
        ]
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                label_text = ""
                if labels:
                    escaped = []
                    for key, val in labels:
                        escaped_value = val.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                        escaped.append(f'{key}="{escaped_value}"')
                    label_text = "{" + ",".join(escaped) + "}"
                lines.append(f"building_compliance_{name}{label_text} {value:g}")
            gauges = dict(self._gauges)
            observations = {name: sorted(values) for name, values in self._observations.items()}
        lines.extend([
            "# TYPE building_compliance_process_uptime_seconds gauge",
            f"building_compliance_process_uptime_seconds {time.monotonic() - self._started:.3f}",
        ])
        for name, value in gauges.items():
            lines.append(f"# TYPE building_compliance_{name} gauge")
            lines.append(f"building_compliance_{name} {value:g}")
        for name, values in observations.items():
            count = len(values)
            total = sum(values)
            lines.append(f"# TYPE building_compliance_{name} histogram")
            for bound in (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf")):
                label = "+Inf" if bound == float("inf") else str(bound)
                bucket_count = count if bound == float("inf") else sum(sample <= bound for sample in values)
                lines.append(f'building_compliance_{name}_bucket{{le="{label}"}} {bucket_count}')
            lines.append(f"building_compliance_{name}_count {count}")
            lines.append(f"building_compliance_{name}_sum {total:.9f}")
        return "\n".join(lines) + "\n"


metrics = Metrics()


def refresh_process_metrics() -> None:
    """Expose portable process peak-RSS telemetry without another package."""
    try:
        import resource
        usage = resource.getrusage(resource.RUSAGE_SELF)
        peak = float(usage.ru_maxrss)
        # macOS reports bytes; Linux and the container runtime report KiB.
        metrics.set_gauge("process_max_rss_bytes", peak if sys.platform == "darwin" else peak * 1024)
        metrics.set_gauge("process_cpu_seconds", float(usage.ru_utime + usage.ru_stime))
    except (ImportError, AttributeError, OSError):
        pass

