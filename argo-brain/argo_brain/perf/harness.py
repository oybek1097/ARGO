"""Performance benchmark harness — spec section 9 / Sprint 10.

Measures latency-sensitive ARGO operations and compares them against the
section-9 P50/P99 targets. The same `BenchmarkResult` objects feed the
baseline regression gate (`argo_brain.perf.baseline`) used by the CI
``performance`` stage described in spec section 11.

Standard library only: timing uses `time.perf_counter`, percentiles are
computed locally — no numpy, no third-party benchmark runner. A benchmark
function may be synchronous or a coroutine function; the harness detects
which and times it accordingly.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from inspect import iscoroutinefunction


def _percentile(ordered: list[float], pct: float) -> float:
    """Linear-interpolation percentile of an already-sorted sample list."""
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


@dataclass
class Stats:
    """Summary statistics for one benchmark's timing samples (milliseconds)."""

    name: str
    samples: int
    p50_ms: float
    p90_ms: float
    p99_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float

    @classmethod
    def from_samples(cls, name: str, samples_ms: list[float]) -> "Stats":
        ordered = sorted(samples_ms)
        n = len(ordered)
        return cls(
            name=name,
            samples=n,
            p50_ms=_percentile(ordered, 50),
            p90_ms=_percentile(ordered, 90),
            p99_ms=_percentile(ordered, 99),
            mean_ms=sum(ordered) / n if n else 0.0,
            min_ms=ordered[0] if ordered else 0.0,
            max_ms=ordered[-1] if ordered else 0.0,
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "samples": self.samples,
            "p50_ms": round(self.p50_ms, 4),
            "p90_ms": round(self.p90_ms, 4),
            "p99_ms": round(self.p99_ms, 4),
            "mean_ms": round(self.mean_ms, 4),
            "min_ms": round(self.min_ms, 4),
            "max_ms": round(self.max_ms, 4),
        }


@dataclass
class Benchmark:
    """One measurable operation plus its spec-section-9 latency targets."""

    name: str
    fn: Callable
    target_p50_ms: float | None = None
    target_p99_ms: float | None = None
    iterations: int = 1000
    warmup: int = 50
    # Free-text note, e.g. the spec table the targets come from.
    note: str = ""


@dataclass
class BenchmarkResult:
    """The outcome of running one `Benchmark`."""

    benchmark: Benchmark
    stats: Stats
    meets_p50: bool | None = None
    meets_p99: bool | None = None

    def __post_init__(self) -> None:
        if self.benchmark.target_p50_ms is not None:
            self.meets_p50 = self.stats.p50_ms <= self.benchmark.target_p50_ms
        if self.benchmark.target_p99_ms is not None:
            self.meets_p99 = self.stats.p99_ms <= self.benchmark.target_p99_ms

    @property
    def passed(self) -> bool:
        """True if every defined target was met (no target → not a failure)."""
        return self.meets_p50 is not False and self.meets_p99 is not False

    def to_dict(self) -> dict:
        return {
            "stats": self.stats.to_dict(),
            "target_p50_ms": self.benchmark.target_p50_ms,
            "target_p99_ms": self.benchmark.target_p99_ms,
            "meets_p50": self.meets_p50,
            "meets_p99": self.meets_p99,
        }


def _measure_sync(fn: Callable, iterations: int, warmup: int) -> list[float]:
    for _ in range(warmup):
        fn()
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return samples


async def _measure_async(fn: Callable, iterations: int, warmup: int) -> list[float]:
    for _ in range(warmup):
        await fn()
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        await fn()
        samples.append((time.perf_counter() - start) * 1000.0)
    return samples


def run_benchmark(bench: Benchmark) -> BenchmarkResult:
    """Run one benchmark and return its measured result."""
    if iscoroutinefunction(bench.fn):
        samples = asyncio.run(
            _measure_async(bench.fn, bench.iterations, bench.warmup)
        )
    else:
        samples = _measure_sync(bench.fn, bench.iterations, bench.warmup)
    return BenchmarkResult(bench, Stats.from_samples(bench.name, samples))


@dataclass
class SuiteReport:
    """The combined results of running a `BenchmarkSuite`."""

    results: list[BenchmarkResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    def to_dict(self) -> dict:
        return {r.benchmark.name: r.to_dict() for r in self.results}


class BenchmarkSuite:
    """An ordered collection of benchmarks run together."""

    def __init__(self, name: str = "argo-brain") -> None:
        self.name = name
        self._benchmarks: list[Benchmark] = []

    def add(self, bench: Benchmark) -> None:
        self._benchmarks.append(bench)

    def __len__(self) -> int:
        return len(self._benchmarks)

    def run(self) -> SuiteReport:
        return SuiteReport([run_benchmark(b) for b in self._benchmarks])
