"""The default ARGO benchmark suite — spec section 9 / Sprint 10.

Defines the concrete benchmarks for the latency-sensitive brain operations
listed in the spec section-9 "Brain agent loop" table: language detection,
L0 working-memory access, and the unified L0+L1+L2 memory write.

Each benchmark is self-contained — it captures its own fixtures in a closure
so the suite can be run with nothing more than a scratch directory.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from pathlib import Path

from argo_brain.language import detect
from argo_brain.memory import MemoryManager
from argo_brain.memory.working import WorkingMemory
from argo_brain.perf.harness import Benchmark, BenchmarkSuite

# Representative inputs covering Latin and Cyrillic scripts so the language
# detector is exercised on its real branches rather than one cached path.
_SAMPLE_TEXTS = (
    "Bugun ob-havo qanday bo'ladi?",
    "Какая сегодня погода в городе?",
    "What is the weather going to be like today?",
    "Hisobotni tayyorlab bering, iltimos.",
)


def build_default_suite(workdir: Path | str) -> tuple[BenchmarkSuite, Callable[[], None]]:
    """Build the standard suite under ``workdir``.

    Returns the suite and a ``close()`` callable that releases the SQLite
    handle opened for the memory benchmarks; callers must invoke it when done.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    suite = BenchmarkSuite("argo-brain")

    # -- language detection — spec §9 "Lang detect" (P50 1ms / P99 5ms) ----
    text_cycle = itertools.cycle(_SAMPLE_TEXTS)

    def bench_lang_detect() -> None:
        detect(next(text_cycle))

    suite.add(Benchmark(
        "lang_detect", bench_lang_detect,
        target_p50_ms=1.0, target_p99_ms=5.0,
        note="spec §9 brain loop — language detection",
    ))

    # -- L0 working-memory write — part of §9 "Memory write (L0+L1)" -------
    working = WorkingMemory()

    def bench_working_add() -> None:
        working.add("perf-user", "user", "a representative chat message")

    suite.add(Benchmark(
        "working_memory_add", bench_working_add,
        target_p50_ms=2.0, target_p99_ms=10.0,
        note="spec §9 brain loop — L0 memory write",
    ))

    # -- L0 history read — part of §9 "Build context (L0+L1+L2 fusion)" ----
    context_memory = WorkingMemory()
    for i in range(50):
        context_memory.add("ctx-user", "user", f"prior message number {i}")

    def bench_working_history() -> None:
        context_memory.history("ctx-user", 20)

    suite.add(Benchmark(
        "working_memory_history", bench_working_history,
        note="spec §9 brain loop — L0 context fetch",
    ))

    # -- unified L0+L1+L2 write — spec §9 "Memory write (L0+L1)" -----------
    manager = MemoryManager(workdir / "perf-bench.db")
    write_counter = itertools.count()

    async def bench_memory_add() -> None:
        n = next(write_counter)
        await manager.add("perf-user", "user", f"benchmark message {n}")

    suite.add(Benchmark(
        "memory_add", bench_memory_add,
        target_p50_ms=2.0, target_p99_ms=10.0,
        iterations=300, warmup=20,
        note="spec §9 brain loop — unified L0+L1+L2 memory write",
    ))

    def close() -> None:
        manager.close()

    return suite, close
