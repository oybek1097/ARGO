"""Performance benchmark CLI — ``python3 -m argo_brain.perf``.

Runs the default ARGO benchmark suite (spec section 9) and prints a table of
P50/P99 timings against their targets. Supports recording a baseline and a
regression gate for the CI ``performance`` stage (spec section 11).

    python3 -m argo_brain.perf                      # run and print results
    python3 -m argo_brain.perf --save-baseline      # record a new baseline
    python3 -m argo_brain.perf --check              # fail on >10% regression
    python3 -m argo_brain.perf --check --strict     # also fail on a missed target
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from argo_brain.perf.baseline import (
    DEFAULT_REGRESSION_PCT,
    check_regression,
    load_baseline,
    save_baseline,
)
from argo_brain.perf.harness import SuiteReport
from argo_brain.perf.suite import build_default_suite

_DEFAULT_BASELINE = Path("~/.argo/perf-baseline.json").expanduser()


def _format_table(report: SuiteReport) -> str:
    rows = [
        f"{'benchmark':<26} {'p50 ms':>9} {'p99 ms':>9} "
        f"{'target p50/p99':>18}  status",
        "-" * 74,
    ]
    for result in report.results:
        b = result.benchmark
        s = result.stats
        if b.target_p50_ms is None and b.target_p99_ms is None:
            target = "—"
            status = "info"
        else:
            target = f"{b.target_p50_ms or 0:.1f}/{b.target_p99_ms or 0:.1f}"
            status = "PASS" if result.passed else "MISS"
        rows.append(
            f"{b.name:<26} {s.p50_ms:>9.3f} {s.p99_ms:>9.3f} "
            f"{target:>18}  {status}"
        )
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="argo_brain.perf",
        description="Run the ARGO performance benchmark suite (spec section 9).",
    )
    parser.add_argument(
        "--baseline", type=Path, default=_DEFAULT_BASELINE,
        help=f"baseline file path (default: {_DEFAULT_BASELINE})",
    )
    parser.add_argument(
        "--save-baseline", action="store_true",
        help="record this run as the new baseline",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="compare against the baseline and fail on a regression",
    )
    parser.add_argument(
        "--threshold", type=float, default=DEFAULT_REGRESSION_PCT,
        help=f"regression threshold percent (default: {DEFAULT_REGRESSION_PCT})",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="also fail when a spec section-9 latency target is missed",
    )
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="argo-perf-") as tmp:
        suite, close = build_default_suite(tmp)
        try:
            print(f"Running {len(suite)} benchmarks...\n")
            report = suite.run()
        finally:
            close()

    print(_format_table(report))
    print()

    exit_code = 0

    if args.strict and not report.all_passed:
        missed = [r.benchmark.name for r in report.results if not r.passed]
        print(f"FAIL (strict): missed latency target(s): {', '.join(missed)}")
        exit_code = 1

    if args.save_baseline:
        save_baseline(report, args.baseline)
        print(f"Baseline saved to {args.baseline}")

    if args.check:
        baseline = load_baseline(args.baseline)
        if not baseline:
            print(f"No baseline at {args.baseline} — nothing to compare against.")
        else:
            reg = check_regression(report, baseline, threshold_pct=args.threshold)
            for name in reg.new_benchmarks:
                print(f"new benchmark (not in baseline): {name}")
            if reg.ok:
                print(f"No regressions beyond {args.threshold:.0f}%.")
            else:
                print(f"REGRESSION — slowdowns beyond {args.threshold:.0f}%:")
                for r in reg.regressions:
                    print(f"  {r}")
                exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
