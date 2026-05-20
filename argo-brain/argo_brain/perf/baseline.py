"""Performance baseline + regression gate — spec section 11 / Sprint 10.

The CI ``performance`` stage records a baseline of benchmark timings and
fails a pull request whose timings regress by more than a threshold (the
spec mandates 10%). This module persists a baseline as JSON and compares a
fresh `SuiteReport` against it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from argo_brain.perf.harness import SuiteReport

# Spec section 11: "fail if >10% regression".
DEFAULT_REGRESSION_PCT = 10.0


def save_baseline(report: SuiteReport, path: Path | str) -> None:
    """Write a benchmark report to ``path`` as the new performance baseline."""
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "benchmarks": {
            name: data["stats"] for name, data in report.to_dict().items()
        },
    }
    p.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_baseline(path: Path | str) -> dict[str, dict]:
    """Load a baseline file; return ``{}`` if it does not exist."""
    p = Path(path).expanduser()
    if not p.is_file():
        return {}
    doc = json.loads(p.read_text(encoding="utf-8"))
    return doc.get("benchmarks", {})


@dataclass
class Regression:
    """One benchmark that ran slower than its baseline beyond the threshold."""

    name: str
    metric: str
    baseline_ms: float
    current_ms: float

    @property
    def delta_pct(self) -> float:
        if self.baseline_ms <= 0:
            return 0.0
        return (self.current_ms - self.baseline_ms) / self.baseline_ms * 100.0

    def __str__(self) -> str:
        return (
            f"{self.name}.{self.metric}: {self.baseline_ms:.3f}ms → "
            f"{self.current_ms:.3f}ms (+{self.delta_pct:.1f}%)"
        )


@dataclass
class RegressionReport:
    """The result of comparing a run against a baseline."""

    regressions: list[Regression]
    # Benchmarks present in the run but absent from the baseline.
    new_benchmarks: list[str]
    threshold_pct: float

    @property
    def ok(self) -> bool:
        """True when no benchmark regressed beyond the threshold."""
        return not self.regressions


def check_regression(
    report: SuiteReport,
    baseline: dict[str, dict],
    *,
    threshold_pct: float = DEFAULT_REGRESSION_PCT,
    metrics: tuple[str, ...] = ("p50_ms", "p99_ms"),
) -> RegressionReport:
    """Compare ``report`` to ``baseline``, flagging >threshold slowdowns.

    A benchmark missing from the baseline is reported as new, not as a
    regression — a first run simply establishes the baseline.
    """
    regressions: list[Regression] = []
    new: list[str] = []
    for name, data in report.to_dict().items():
        base = baseline.get(name)
        if base is None:
            new.append(name)
            continue
        stats = data["stats"]
        for metric in metrics:
            base_ms = base.get(metric)
            cur_ms = stats.get(metric)
            if base_ms is None or cur_ms is None:
                continue
            allowed = base_ms * (1.0 + threshold_pct / 100.0)
            if cur_ms > allowed:
                regressions.append(
                    Regression(name, metric, base_ms, cur_ms)
                )
    return RegressionReport(regressions, new, threshold_pct)
