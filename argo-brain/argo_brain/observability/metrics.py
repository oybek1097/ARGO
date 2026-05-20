"""Prometheus-compatible metrics collection (spec section 8).

Provides :class:`MetricsCollector`, a stdlib-only metrics registry that
supports counters, gauges and histograms, and can render its state into
the Prometheus text-exposition format.
"""

from __future__ import annotations

import threading
from typing import Dict, Mapping, Optional, Tuple

# Default histogram bucket upper bounds (in seconds / generic units).
# Mirrors the conventional Prometheus client default buckets.
DEFAULT_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0,
)

# A label set is normalised to a sorted tuple of (key, value) pairs so it
# can be used as a dictionary key.
_LabelKey = Tuple[Tuple[str, str], ...]


def _normalise_labels(labels: Optional[Mapping[str, str]]) -> _LabelKey:
    """Return a stable, hashable representation of a label mapping."""
    if not labels:
        return ()
    return tuple(sorted((str(k), str(v)) for k, v in labels.items()))


def _format_labels(label_key: _LabelKey, extra: Optional[Tuple[str, str]] = None) -> str:
    """Render a label key into Prometheus ``{k="v",...}`` syntax."""
    pairs = list(label_key)
    if extra is not None:
        pairs = pairs + [extra]
    if not pairs:
        return ""
    body = ",".join('{}="{}"'.format(k, _escape(v)) for k, v in pairs)
    return "{" + body + "}"


def _escape(value: str) -> str:
    """Escape a label value per the Prometheus exposition format."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class MetricsCollector:
    """Thread-safe registry for counters, gauges and histograms.

    All metric operations accept an optional ``labels`` mapping; metrics
    sharing a name but differing in labels are tracked independently.
    """

    def __init__(self, buckets: Optional[Tuple[float, ...]] = None) -> None:
        self._buckets: Tuple[float, ...] = tuple(buckets) if buckets else DEFAULT_BUCKETS
        self._lock = threading.Lock()
        # name -> {label_key -> float}
        self._counters: Dict[str, Dict[_LabelKey, float]] = {}
        self._gauges: Dict[str, Dict[_LabelKey, float]] = {}
        # name -> {label_key -> {"buckets": [counts], "sum": float, "count": int}}
        self._histograms: Dict[str, Dict[_LabelKey, Dict[str, object]]] = {}

    # -- counters ---------------------------------------------------------
    def counter(
        self,
        name: str,
        labels: Optional[Mapping[str, str]] = None,
        value: float = 1.0,
    ) -> float:
        """Increment counter ``name`` by ``value`` (default 1) and return it.

        Counters are monotonically increasing; negative increments raise.
        """
        if value < 0:
            raise ValueError("counter increments must be non-negative")
        key = _normalise_labels(labels)
        with self._lock:
            series = self._counters.setdefault(name, {})
            series[key] = series.get(key, 0.0) + value
            return series[key]

    # -- gauges -----------------------------------------------------------
    def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Mapping[str, str]] = None,
    ) -> float:
        """Set gauge ``name`` to ``value`` and return it."""
        key = _normalise_labels(labels)
        with self._lock:
            self._gauges.setdefault(name, {})[key] = float(value)
            return float(value)

    # -- histograms -------------------------------------------------------
    def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Mapping[str, str]] = None,
    ) -> None:
        """Record an observation of ``value`` into histogram ``name``.

        The observation is counted into every bucket whose upper bound is
        greater than or equal to ``value``; running sum and count are kept.
        """
        key = _normalise_labels(labels)
        with self._lock:
            series = self._histograms.setdefault(name, {})
            data = series.get(key)
            if data is None:
                data = {
                    "buckets": [0 for _ in self._buckets],
                    "sum": 0.0,
                    "count": 0,
                }
                series[key] = data
            bucket_counts = data["buckets"]  # type: ignore[index]
            for i, upper in enumerate(self._buckets):
                if value <= upper:
                    bucket_counts[i] += 1  # type: ignore[index]
            data["sum"] = float(data["sum"]) + float(value)  # type: ignore[index]
            data["count"] = int(data["count"]) + 1  # type: ignore[index]

    # -- introspection ----------------------------------------------------
    def get_counter(
        self, name: str, labels: Optional[Mapping[str, str]] = None
    ) -> float:
        """Return the current value of a counter series (0.0 if unseen)."""
        key = _normalise_labels(labels)
        with self._lock:
            return self._counters.get(name, {}).get(key, 0.0)

    def get_gauge(
        self, name: str, labels: Optional[Mapping[str, str]] = None
    ) -> Optional[float]:
        """Return the current value of a gauge series (None if unseen)."""
        key = _normalise_labels(labels)
        with self._lock:
            return self._gauges.get(name, {}).get(key)

    def get_histogram(
        self, name: str, labels: Optional[Mapping[str, str]] = None
    ) -> Optional[Dict[str, object]]:
        """Return a copy of a histogram series' state (None if unseen)."""
        key = _normalise_labels(labels)
        with self._lock:
            data = self._histograms.get(name, {}).get(key)
            if data is None:
                return None
            return {
                "buckets": list(data["buckets"]),  # type: ignore[index]
                "sum": float(data["sum"]),  # type: ignore[index]
                "count": int(data["count"]),  # type: ignore[index]
            }

    # -- rendering --------------------------------------------------------
    def render_prometheus(self) -> str:
        """Render all metrics in Prometheus text-exposition format."""
        lines: list[str] = []
        with self._lock:
            for name in sorted(self._counters):
                lines.append("# TYPE {} counter".format(name))
                for label_key in sorted(self._counters[name]):
                    value = self._counters[name][label_key]
                    lines.append(
                        "{}{} {}".format(
                            name, _format_labels(label_key), _fmt(value)
                        )
                    )
            for name in sorted(self._gauges):
                lines.append("# TYPE {} gauge".format(name))
                for label_key in sorted(self._gauges[name]):
                    value = self._gauges[name][label_key]
                    lines.append(
                        "{}{} {}".format(
                            name, _format_labels(label_key), _fmt(value)
                        )
                    )
            for name in sorted(self._histograms):
                lines.append("# TYPE {} histogram".format(name))
                for label_key in sorted(self._histograms[name]):
                    data = self._histograms[name][label_key]
                    bucket_counts = data["buckets"]  # type: ignore[index]
                    cumulative = 0
                    for i, upper in enumerate(self._buckets):
                        cumulative += int(bucket_counts[i])  # type: ignore[index]
                        lines.append(
                            "{}_bucket{} {}".format(
                                name,
                                _format_labels(label_key, ("le", _fmt(upper))),
                                cumulative,
                            )
                        )
                    total = int(data["count"])  # type: ignore[index]
                    lines.append(
                        "{}_bucket{} {}".format(
                            name,
                            _format_labels(label_key, ("le", "+Inf")),
                            total,
                        )
                    )
                    lines.append(
                        "{}_sum{} {}".format(
                            name,
                            _format_labels(label_key),
                            _fmt(float(data["sum"])),  # type: ignore[index]
                        )
                    )
                    lines.append(
                        "{}_count{} {}".format(
                            name, _format_labels(label_key), total
                        )
                    )
        return "\n".join(lines) + ("\n" if lines else "")


def _fmt(value: float) -> str:
    """Format a numeric value, rendering whole numbers without a decimal."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return repr(value)
