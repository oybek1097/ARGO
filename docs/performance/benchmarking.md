# Performance benchmarking — ARGO Agent v3.0

> Status: **alpha, approaching GA.** The tables below restate the
> performance *targets* from the Technical Specification section 9. They are
> design budgets that the benchmark harness is expected to verify before GA;
> they are not certified release measurements.

## 1. Scope

This document describes:

- The performance targets ARGO commits to (spec section 9).
- How those targets are grouped and what each metric means.
- How to run the benchmark harness and read its output.
- How performance gating works in CI.

It does **not** define the harness implementation. The harness is a separate
work-stream living under `argo-brain/argo_brain/perf/` and is invoked as:

```bash
python3 -m argo_brain.perf
```

If that module is not present in your checkout yet, this document is still
the source of truth for *what* the harness must measure.

## 2. The two components under test

| Component | Language | Benchmarked with |
|---|---|---|
| `argo-core` | Rust gateway | `cargo bench` (criterion.rs) |
| `argo-brain` | Python brain | `python3 -m argo_brain.perf` |

End-to-end numbers exercise both via the IPC socket.

## 3. Performance targets (spec section 9)

### 3.1 Core gateway

| Operation | P50 | P99 | Condition |
|---|---|---|---|
| `/api/health` | 0.1 ms | 1 ms | response only |
| `/api/chat` (excl. brain) | 5 ms | 20 ms | with sandbox |
| WebSocket message echo | 0.3 ms | 2 ms | single message |
| OpenAI `/v1/chat/completions` overhead | 10 ms | 30 ms | with streaming |
| MCP `tools/list` | 2 ms | 8 ms | with 50 tools |

### 3.2 Brain agent loop (single iteration, no LLM)

| Operation | P50 | P99 |
|---|---|---|
| Language detection | 1 ms | 5 ms |
| Build context (L0+L1+L2 fusion) | 30 ms | 100 ms |
| Tool dispatch (parallel 8, overhead only) | 5 ms | 20 ms |
| Memory write (L0+L1) | 2 ms | 10 ms |
| Plugin pre/post hooks | 0.5 ms | 5 ms |

### 3.3 End-to-end (Claude Sonnet, no tools)

| Operation | P50 | P99 |
|---|---|---|
| Simple chat (200-token output) | 1.5 s | 4 s |
| With 1 tool call | 3 s | 8 s |
| With 5 parallel tool calls | 4 s | 10 s |
| Voice mode (push-to-talk) | 2.5 s | 6 s |

End-to-end figures are LLM-bound; the relevant ARGO-controlled portion is
the overhead *around* the LLM call, not the model latency itself.

### 3.4 Throughput (per node)

| Workload | Target |
|---|---|
| Concurrent WebSocket connections | >= 50,000 |
| RPS, gateway-only echo | >= 10,000 |
| RPS, full chat with cache hit, no tools | >= 1,000 |
| RPS, full chat with 1 tool call | >= 200 |
| RPS, full chat with LLM call | LLM-bound |

### 3.5 Memory subsystem budgets

| Operation | P50 | P99 |
|---|---|---|
| L0 memory write | < 0.05 ms | < 0.2 ms |
| L0 memory read (1 user, 100 msg) | < 0.1 ms | < 0.5 ms |
| L1 memory write | < 1 ms | < 5 ms |
| Memory write latency (L1 + L2) | — | < 10 ms |
| Memory read latency (full 3-layer context) | — | < 50 ms |

### 3.6 Cold start

Process startup latency has its own document:
[`cold-start.md`](cold-start.md). Summary target: exec -> READY in
**< 250 ms** with a warm cache.

## 4. Running the benchmarks

### 4.1 Brain harness

```bash
# Run the full Python brain suite.
python3 -m argo_brain.perf

# A single named suite (e.g. memory, agent-loop, cold-start).
python3 -m argo_brain.perf --suite memory
```

The harness is expected to report, per metric, the P50/P99 it measured
alongside the spec target and a pass/fail verdict.

### 4.2 Core harness

```bash
# Run criterion benchmarks for the Rust gateway.
cd argo-core && cargo bench
```

### 4.3 Load testing

Gateway throughput and concurrent-connection targets (§3.4) are validated
with an external load tool (k6) against a running stack, as described in
spec section 11. This is a weekly job, not a per-PR job.

## 5. Methodology

For results to be comparable run to run:

- **Warm up.** Discard the first iterations; report steady-state.
- **Sample size.** Report the median of >= 20 runs plus P99; a single run is
  not a measurement.
- **Quiescent host.** No competing load; pin CPU frequency scaling where
  possible.
- **Pin versions.** Record the Python version, Rust toolchain, OS and
  hardware alongside every result.
- **Separate cold and warm.** Cold-cache and warm-cache numbers are both
  real and must not be averaged together.
- **Isolate the LLM.** For agent-loop and memory metrics, exclude real model
  calls so the figure reflects ARGO code, not network or model latency.

## 6. Performance gating in CI

Per spec section 11, performance is checked weekly and the build fails on a
**> 10% regression versus baseline**.

- The `performance` stage runs `python3 -m argo_brain.perf` and
  `cargo bench`, compares results to the stored baseline, and fails on
  regression beyond the threshold.
- The baseline is updated deliberately, not automatically, so an accepted
  intentional change re-baselines explicitly.
- Per-PR runs are kept lightweight; the full load-test sweep runs on the
  weekly schedule to keep PR feedback fast.

## 7. Honest current state

The harness and baselines are being built during Sprint 10. Until baselines
exist and have been published, the tables in section 3 are **targets** the
project is engineering toward, not guarantees. The first published baseline
will be tagged and referenced from this document so readers can distinguish
"target" from "measured".

## References

- Spec section 9 — performance targets (further detail).
- Spec section 11 — quality, testing and the CI performance gate.
- [`cold-start.md`](cold-start.md) — process startup latency analysis.
