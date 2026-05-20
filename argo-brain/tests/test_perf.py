"""Performance harness tests — spec section 9 / Sprint 10."""

import tempfile
import unittest
from pathlib import Path

from argo_brain.perf import (
    Benchmark,
    BenchmarkSuite,
    build_default_suite,
    check_regression,
    load_baseline,
    run_benchmark,
    save_baseline,
)
from argo_brain.perf.harness import Stats, _percentile


class TestPercentile(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_percentile([], 50), 0.0)

    def test_single(self):
        self.assertEqual(_percentile([7.0], 99), 7.0)

    def test_median(self):
        self.assertEqual(_percentile([1.0, 2.0, 3.0], 50), 2.0)

    def test_extremes(self):
        data = [float(i) for i in range(1, 101)]
        self.assertEqual(_percentile(data, 0), 1.0)
        self.assertEqual(_percentile(data, 100), 100.0)

    def test_interpolation(self):
        # Between 1.0 and 2.0, 50th percentile of a 2-sample list is the mean.
        self.assertAlmostEqual(_percentile([1.0, 2.0], 50), 1.5)


class TestStats(unittest.TestCase):
    def test_from_samples(self):
        s = Stats.from_samples("x", [10.0, 20.0, 30.0, 40.0])
        self.assertEqual(s.samples, 4)
        self.assertEqual(s.min_ms, 10.0)
        self.assertEqual(s.max_ms, 40.0)
        self.assertEqual(s.mean_ms, 25.0)

    def test_unsorted_input(self):
        # Stats must sort internally before computing percentiles.
        s = Stats.from_samples("x", [40.0, 10.0, 30.0, 20.0])
        self.assertEqual(s.min_ms, 10.0)
        self.assertEqual(s.max_ms, 40.0)

    def test_to_dict_round(self):
        s = Stats.from_samples("x", [1.111111, 2.222222])
        self.assertEqual(s.to_dict()["name"], "x")
        self.assertIn("p99_ms", s.to_dict())


class TestRunBenchmark(unittest.TestCase):
    def test_sync_benchmark(self):
        calls = []
        bench = Benchmark("sync", lambda: calls.append(1), iterations=20, warmup=5)
        result = run_benchmark(bench)
        self.assertEqual(result.stats.samples, 20)
        self.assertEqual(len(calls), 25)  # warmup + iterations

    def test_async_benchmark(self):
        state = {"n": 0}

        async def fn():
            state["n"] += 1

        result = run_benchmark(Benchmark("async", fn, iterations=15, warmup=3))
        self.assertEqual(result.stats.samples, 15)
        self.assertEqual(state["n"], 18)

    def test_target_pass(self):
        bench = Benchmark("fast", lambda: None, target_p50_ms=1000.0,
                          target_p99_ms=1000.0, iterations=10, warmup=1)
        result = run_benchmark(bench)
        self.assertTrue(result.meets_p50)
        self.assertTrue(result.meets_p99)
        self.assertTrue(result.passed)

    def test_target_miss(self):
        # An impossibly small target → guaranteed miss.
        bench = Benchmark("slow", lambda: sum(range(1000)),
                          target_p50_ms=0.0, iterations=10, warmup=1)
        result = run_benchmark(bench)
        self.assertFalse(result.meets_p50)
        self.assertFalse(result.passed)

    def test_no_target_is_not_a_failure(self):
        result = run_benchmark(Benchmark("info", lambda: None, iterations=5))
        self.assertIsNone(result.meets_p50)
        self.assertTrue(result.passed)


class TestSuite(unittest.TestCase):
    def test_suite_runs_all(self):
        suite = BenchmarkSuite("t")
        suite.add(Benchmark("a", lambda: None, iterations=5, warmup=1))
        suite.add(Benchmark("b", lambda: None, iterations=5, warmup=1))
        self.assertEqual(len(suite), 2)
        report = suite.run()
        self.assertEqual(len(report.results), 2)
        self.assertTrue(report.all_passed)


class TestBaseline(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "baseline.json"
        suite = BenchmarkSuite("t")
        suite.add(Benchmark("op", lambda: None, iterations=10, warmup=1))
        self.report = suite.run()

    def tearDown(self):
        self._tmp.cleanup()

    def test_save_and_load(self):
        save_baseline(self.report, self.path)
        self.assertTrue(self.path.is_file())
        loaded = load_baseline(self.path)
        self.assertIn("op", loaded)
        self.assertIn("p50_ms", loaded["op"])

    def test_load_missing_returns_empty(self):
        self.assertEqual(load_baseline(self.path / "nope.json"), {})

    def test_no_regression_against_self(self):
        reg = check_regression(self.report, {
            name: data["stats"] for name, data in self.report.to_dict().items()
        })
        self.assertTrue(reg.ok)

    def test_detects_regression(self):
        # Baseline far faster than the current run → flagged.
        fake_baseline = {"op": {"p50_ms": 0.0001, "p99_ms": 0.0001}}
        reg = check_regression(self.report, fake_baseline, threshold_pct=10.0)
        self.assertFalse(reg.ok)
        self.assertTrue(reg.regressions)
        self.assertGreater(reg.regressions[0].delta_pct, 10.0)

    def test_within_threshold_is_ok(self):
        current = self.report.to_dict()["op"]["stats"]
        # Baseline 5% faster — under the 10% threshold.
        base = {"op": {
            "p50_ms": current["p50_ms"] / 1.05,
            "p99_ms": current["p99_ms"] / 1.05,
        }}
        reg = check_regression(self.report, base, threshold_pct=10.0)
        self.assertTrue(reg.ok)

    def test_new_benchmark_not_a_regression(self):
        reg = check_regression(self.report, {})
        self.assertTrue(reg.ok)
        self.assertEqual(reg.new_benchmarks, ["op"])


class TestDefaultSuite(unittest.TestCase):
    def test_default_suite_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            suite, close = build_default_suite(tmp)
            try:
                self.assertEqual(len(suite), 4)
                report = suite.run()
            finally:
                close()
        names = {r.benchmark.name for r in report.results}
        self.assertEqual(
            names,
            {"lang_detect", "working_memory_add",
             "working_memory_history", "memory_add"},
        )
        # Every benchmark produced real samples.
        for result in report.results:
            self.assertGreater(result.stats.samples, 0)


if __name__ == "__main__":
    unittest.main()
