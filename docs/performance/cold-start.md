# Cold-start optimization — `argo-brain`

> Status: **alpha, approaching GA.** The numbers in this document are
> *targets* and design budgets, not measured release figures. Where a
> measurement exists it is labelled as such. Treat every "target" row as
> something the benchmark harness (`python3 -m argo_brain.perf`, see
> [`benchmarking.md`](benchmarking.md)) is expected to verify before GA.

## 1. What "cold start" means here

Cold start is the wall-clock time from invoking the brain process until it
is ready to accept its first request on the IPC socket:

```
process exec  ->  interpreter up  ->  imports resolved  ->  config loaded
              ->  subsystems initialised  ->  IPC socket bound  ->  READY
```

It matters in three situations:

1. **Container / pod startup** — Kubernetes readiness gating, autoscaling
   scale-up latency, and rolling-deploy churn.
2. **CLI / TUI invocation** — a developer running `argo-brain` ad hoc feels
   every millisecond before the first prompt.
3. **Serverless / on-demand workers** — where the process may be spawned
   per burst of traffic.

Warm latency (steady-state request handling) is covered separately in
[`benchmarking.md`](benchmarking.md); this document is only about the
*first* request.

## 2. What contributes to startup time

Startup cost in `argo-brain` breaks down into four buckets. The split below
is the working model used to prioritise optimization; absolute numbers are
budgets pending harness confirmation.

| Phase | What happens | Budget (target) |
|---|---|---|
| Interpreter bootstrap | CPython process exec, site init | 15-30 ms |
| Module import | Resolving the `argo_brain` package tree + stdlib | 40-120 ms |
| Config load | Reading env / config file, validation | 2-10 ms |
| Subsystem init | Memory (SQLite), cache, channels, IPC bind | 20-80 ms |
| **Total cold start** | exec -> READY | **target < 250 ms** |

### 2.1 Module imports

This is normally the single largest contributor. `argo_brain` has a wide
package tree — `api`, `channels`, `core`, `memory`, `providers`, `skills`,
`tools`, `tui`, `mcp`, `multi_agent`, and more. A naive top-level
`import argo_brain` that eagerly pulls in every subpackage pays for code
paths the current invocation will never touch (for example, the TUI is
irrelevant to a headless IPC server, and most channel adapters are unused
on any given deployment).

Imports are also recursive: importing `memory` pulls `sqlite3`, importing a
channel may pull `http`/`email`/`ssl`, and `ssl` in particular is not free.

### 2.2 Config load

Reading and validating configuration (`argo_brain/config.py`) is cheap in
absolute terms, but it can trigger filesystem stat storms if it probes many
candidate paths, and it can pull heavyweight imports if validation is done
with a third-party library. Keep it stdlib and keep the search path short.

### 2.3 Memory / SQLite init

The L0 layer is an in-process structure and is essentially free to create.
The L1 layer is SQLite-backed. First-touch costs include:

- Opening the database file (or creating it on first run).
- Running schema migrations / `CREATE TABLE IF NOT EXISTS` statements.
- Applying `PRAGMA` settings (`journal_mode`, `synchronous`, `foreign_keys`).
- Building any indexes on a fresh database.

On a *fresh* database this is the worst case. On an existing database it is
a few stat + open calls plus PRAGMA application.

### 2.4 Other subsystem init

Cache warm-up, channel adapter registration, plugin discovery (scanning a
plugin directory), and binding the IPC socket. Plugin discovery in
particular is a directory walk and should not block READY.

## 3. Optimization techniques

The guiding principle: **do nothing at import time that the first request
does not strictly need.** Concretely:

### 3.1 Lazy imports

Move heavy or rarely-used imports out of module top level and into the
function that actually needs them. Two patterns:

- **Function-local import** — `import` inside the function body. Simple,
  effective for a leaf dependency used on one code path.
- **Module-level `__getattr__`** (PEP 562) — lets a package expose names
  lazily so `from argo_brain import X` does not eagerly import `X`'s module
  until `X` is first accessed.

Priority candidates for laziness: the TUI stack, unused channel adapters,
provider SDKs, anything pulling `ssl` / `http` / `xml` / `email`.

### 3.2 Deferred subsystem initialization

Bind the IPC socket and report READY *before* doing optional work. Defer:

- Plugin / skill directory scanning — run it on a background task after
  READY, or lazily on first use.
- L2 / vector-memory connections — connect on first query, not at boot.
- Cache pre-warming — warm in the background.

Required work (config load, L0/L1 memory ready enough to serve, IPC bind)
stays on the critical path; everything else moves off it.

### 3.3 Profiling with `python -X importtime`

`importtime` is the primary tool for finding import hotspots:

```bash
python -X importtime -m argo_brain 2> importtime.log
```

The `cumulative` column shows the total cost of each import subtree. Sort
the log to find the worst offenders:

```bash
sort -t '|' -k2 -n -r importtime.log | head -30
```

Each expensive subtree is then a candidate for §3.1 or §3.2. Re-profile
after every change — import graphs are easy to regress.

### 3.4 `__pycache__` warming

CPython compiles `.py` to `.pyc` on first import. A cold container with no
`__pycache__` pays that compilation cost on the first request. Mitigations:

- **Pre-compile at build time** — run `python -m compileall argo_brain`
  in the Docker image build so the layer ships populated `__pycache__`.
- **Ship the `.pyc` files** — ensure the build does not strip them.
- Optionally set `PYTHONPYCACHEPREFIX` to a writable, persistent location
  when the source tree itself is read-only.

This removes compilation from the cold path; only deserialization of the
`.pyc` remains.

### 3.5 Smaller wins

- Avoid module-level work with side effects (no network, no file I/O, no
  expensive constant computation at import).
- Keep `argo_brain/__init__.py` thin — it should not import the world.
- Consider `python -X frozen_modules=on` (default on modern CPython) and
  avoid `-X importtime` / `-v` in production.

## 4. How to measure

### 4.1 End-to-end cold start

Measure exec -> READY honestly by spawning a fresh process and timing until
the socket accepts a connection. The benchmark harness exposes this:

```bash
python3 -m argo_brain.perf --suite cold-start
```

For a quick manual check, time the process to a known "ready" log line, and
always discard the first run after a `git pull` (it pays compilation cost
unless `__pycache__` was warmed — which is itself the point of §3.4).

### 4.2 Import cost only

```bash
python -X importtime -c "import argo_brain" 2>&1 | tail -1
```

### 4.3 Methodology

- Run on a quiescent machine; report median of >= 20 runs, plus P99.
- Measure two scenarios separately: **cold cache** (no `__pycache__`, fresh
  SQLite DB) and **warm** (compiled, existing DB). Both are real — cold is
  the first container start, warm is every restart after.
- Pin the Python version; cold start is interpreter-version sensitive.

## 5. Current vs target

Presented honestly: the project is alpha. The "current" column is a working
estimate from local runs of a partial system and **must be re-baselined by
the harness before GA**. The "target" column is the GA budget.

| Metric | Current (estimate) | Target (GA) |
|---|---|---|
| Import cost (`import argo_brain`) | ~80-150 ms | < 60 ms |
| Config load | ~5 ms | < 5 ms |
| Memory/SQLite init (existing DB) | ~10-30 ms | < 20 ms |
| Memory/SQLite init (fresh DB) | ~40-90 ms | < 60 ms |
| Cold start, warm cache (exec -> READY) | ~200-350 ms | < 250 ms |
| Cold start, cold cache (exec -> READY) | not yet measured | < 500 ms |

### Optimization roadmap

1. Profile with `-X importtime`, rank the import subtrees (§3.3).
2. Make the TUI, unused channels and provider SDKs lazy (§3.1).
3. Defer plugin discovery and L2 connections past READY (§3.2).
4. Add `compileall` to the Docker build (§3.4).
5. Wire the `cold-start` suite into the weekly performance run and gate on
   a >10% regression, consistent with spec section 11.

## References

- Spec section 9 — performance targets.
- Spec section 11 — quality, CI, performance regression gate.
- [`benchmarking.md`](benchmarking.md) — the full performance target tables
  and how the harness measures them.
