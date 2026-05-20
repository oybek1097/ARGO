"""Performance benchmarking — spec section 9 / Sprint 10.

A standard-library micro-benchmark harness for the latency-sensitive brain
operations, plus a JSON baseline and a >10% regression gate for the CI
``performance`` stage. Run it with ``python3 -m argo_brain.perf``.
"""

from argo_brain.perf.baseline import (
    DEFAULT_REGRESSION_PCT,
    Regression,
    RegressionReport,
    check_regression,
    load_baseline,
    save_baseline,
)
from argo_brain.perf.harness import (
    Benchmark,
    BenchmarkResult,
    BenchmarkSuite,
    Stats,
    SuiteReport,
    run_benchmark,
)
from argo_brain.perf.suite import build_default_suite

__all__ = [
    "Benchmark",
    "BenchmarkResult",
    "BenchmarkSuite",
    "Stats",
    "SuiteReport",
    "run_benchmark",
    "build_default_suite",
    "DEFAULT_REGRESSION_PCT",
    "Regression",
    "RegressionReport",
    "check_regression",
    "load_baseline",
    "save_baseline",
]
