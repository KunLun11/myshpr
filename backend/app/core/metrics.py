"""Lightweight in-process metrics exposed in Prometheus text format.

No third-party client: a pilot needs request counts, latency buckets and a
couple of gauges, not a full metrics SDK. In a multi-worker deployment each
worker exposes its own counters; the scrape target (sidecar or platform) can
aggregate with ``sum by (...)``.

Cardinality is bounded: routes are recorded by their OpenAPI path template
(``/api/v1/teacher/projects/{id}``) and unmatched paths collapse into
``unmatched``.
"""

from dataclasses import dataclass, field

# Prometheus default latency buckets, in seconds.
_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

# Hard cap so a flood of unknown paths cannot blow up memory.
_MAX_ROUTES = 200


@dataclass
class _Histogram:
    buckets: tuple[float, ...]
    counts: list[int] = field(default_factory=lambda: [0] * (len(_BUCKETS) + 1))
    total: float = 0.0
    count: int = 0

    def observe(self, value: float) -> None:
        self.total += value
        self.count += 1
        for index, boundary in enumerate(self.buckets):
            if value <= boundary:
                self.counts[index] += 1
                return
        self.counts[-1] += 1


class MetricsRegistry:
    def __init__(self) -> None:
        self._requests: dict[tuple[str, str, str], int] = {}
        self._latency: dict[str, _Histogram] = {}
        self.background_runs: dict[str, int] = {}
        self.background_failures: dict[str, int] = {}

    def observe_request(self, *, method: str, route: str, status: int, seconds: float) -> None:
        key = (method, route, str(status))
        self._requests[key] = self._requests.get(key, 0) + 1
        if route not in self._latency and len(self._latency) < _MAX_ROUTES:
            self._latency[route] = _Histogram(_BUCKETS)
        if route in self._latency:
            self._latency[route].observe(seconds)

    def record_background(self, task: str, *, ok: bool) -> None:
        self.background_runs[task] = self.background_runs.get(task, 0) + 1
        if not ok:
            self.background_failures[task] = self.background_failures.get(task, 0) + 1

    def reset(self) -> None:
        self._requests.clear()
        self._latency.clear()
        self.background_runs.clear()
        self.background_failures.clear()

    def render(self, *, db_pool: dict[str, int] | None = None) -> str:
        lines: list[str] = []

        lines.append("# HELP http_requests_total Total HTTP requests.")
        lines.append("# TYPE http_requests_total counter")
        for (method, route, status), value in sorted(self._requests.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"http_requests_total{{{labels}}} {value}")

        lines.append("# HELP http_request_duration_seconds Request latency.")
        lines.append("# TYPE http_request_duration_seconds histogram")
        for route, histogram in sorted(self._latency.items()):
            for index, boundary in enumerate(histogram.buckets):
                lines.append(
                    "http_request_duration_seconds_bucket"
                    f'{{route="{route}",le="{boundary}"}} {histogram.counts[index]}'
                )
            lines.append(
                "http_request_duration_seconds_bucket"
                f'{{route="{route}",le="+Inf"}} {histogram.counts[-1]}'
            )
            lines.append(
                f'http_request_duration_seconds_sum{{route="{route}"}} {histogram.total:.6f}'
            )
            lines.append(
                f'http_request_duration_seconds_count{{route="{route}"}} {histogram.count}'
            )

        if db_pool is not None:
            lines.append("# HELP db_pool_connections Database connection pool size.")
            lines.append("# TYPE db_pool_connections gauge")
            for name, value in db_pool.items():
                lines.append(f'db_pool_connections{{state="{name}"}} {value}')

        lines.append("# HELP background_job_runs_total Background job invocations.")
        lines.append("# TYPE background_job_runs_total counter")
        for task, value in sorted(self.background_runs.items()):
            lines.append(f'background_job_runs_total{{task="{task}"}} {value}')

        lines.append("# HELP background_job_failures_total Background job failures.")
        lines.append("# TYPE background_job_failures_total counter")
        for task, value in sorted(self.background_failures.items()):
            lines.append(f'background_job_failures_total{{task="{task}"}} {value}')

        return "\n".join(lines) + "\n"


registry = MetricsRegistry()
