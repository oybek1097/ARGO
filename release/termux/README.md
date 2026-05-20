# ARGO Agent v3.0 — Termux (Android) beta

> **Status: BETA — brain-only.** ARGO runs on Android via
> [Termux](https://termux.dev) in **brain-only mode**: the Python brain runs
> standalone and the Rust gateway (`argo-core`) is **not** installed. See
> [`../../docs/platforms.md`](../../docs/platforms.md) for the support matrix.

[Termux](https://termux.dev) is a terminal-emulator app that gives Android a
Linux-like userland. ARGO's brain (`argo-brain`) is **standard-library-only**
Python, so it runs there directly — no third-party Python packages, no
compilation step.

The Rust gateway `argo-core` is **optional** on every platform. On Termux it
is intentionally **left out**: cross-compiling Rust on a phone is heavy and
brings little benefit, because the stdlib brain already provides its own HTTP
gateway (`argo serve`). This is "brain-only mode".

---

## What works in brain-only mode

- The full agent loop (Plan → Execute) and the built-in tools.
- Memory (L0 in-process deque + L1 SQLite/FTS5).
- The LLM providers (Mock with no API key; Anthropic with a key).
- Skills, plugins, the cron scheduler, multi-agent kanban.
- `argo serve` — the brain's own HTTP gateway on port `8000`.
- Network channels (Telegram, webhook, Slack, …) over the stdlib.

## What is not available

- `argo-core` (the Rust HTTP gateway) and therefore the argo-core ↔
  argo-brain IPC link. The brain's built-in `serve` covers the HTTP role.
- Unix sandboxing primitives — Android's app sandbox already isolates
  Termux, but ARGO's own namespace/seccomp sandboxing does not apply.

---

## Prerequisites

1. **Install Termux.** Get it from
   [F-Droid](https://f-droid.org/packages/com.termux/) or
   [GitHub releases](https://github.com/termux/termux-app/releases).
   The Google Play build is outdated — prefer F-Droid.
2. **A copy of the ARGO repository on the device.** Either:

   ```bash
   pkg install -y git
   git clone https://github.com/oybek1097/ARGO.git
   cd ARGO
   ```

`python` itself is installed by the setup script — you do not need to
install it beforehand.

---

## Setup

From inside the ARGO repository checkout, run:

```bash
bash release/termux/setup.sh
```

The script (it is **idempotent** — safe to re-run):

1. Runs `pkg update` and installs `python` via `pkg`.
2. Verifies Python 3.11+ (3.12 recommended).
3. Creates the `~/.argo/` directory layout (`data/`, `skills/`, `plugins/`).
4. Copies the stdlib-only `argo_brain` package into `~/.argo/lib`.
5. Installs an `argo` launcher into Termux's `bin` directory (already on
   `PATH`).
6. Runs `argo doctor` and prints next steps.

Relocate the data directory with `ARGO_HOME` if you wish:

```bash
ARGO_HOME=/sdcard/argo bash release/termux/setup.sh
```

---

## Running ARGO on Android

```bash
argo setup     # interactive first-run setup wizard
argo doctor    # diagnostics
argo chat      # interactive conversation (Mock provider, no API key)
argo serve     # HTTP gateway on http://127.0.0.1:8000
```

To reach the gateway from another app on the same phone, browse to
`http://127.0.0.1:8000/api/health`.

> **Tip — keep it running.** Android aggressively suspends background apps.
> Run `termux-wake-lock` before `argo serve` to hold a wake-lock so the
> process is not killed while the screen is off. Release it later with
> `termux-wake-unlock`.

---

## Verification

```bash
# 1. The brain imports and reports its version:
argo version

# 2. Diagnostics (a missing argo-core binary is expected and not fatal):
argo doctor

# 3. Smoke test — exercises the agent loop, tools, memory, kanban:
argo selftest

# 4. A one-shot offline conversation:
argo chat
#    type:  hello
#    then:  /exit
```

A healthy brain-only install shows `argo selftest` printing **"All checks
passed."** In `argo doctor`, the `argo-core binary` and `ANTHROPIC_API_KEY`
checks may report as not found — both are expected in brain-only / mock mode
and are **not** treated as failures.

With `argo serve` running, from another Termux session:

```bash
curl http://127.0.0.1:8000/api/health
```

---

## Limitations (beta)

- **Brain-only.** No `argo-core`; use `argo serve` for the HTTP API.
- **Background suspension.** Android may kill the process; use
  `termux-wake-lock` for long-running sessions.
- **Performance.** Phones are constrained — large skill sets, big memory
  databases and heavy tool runs are slower than on a desktop.
- **Storage.** App-private storage is small. Point `ARGO_HOME` at shared
  storage (e.g. `/sdcard`) only after running `termux-setup-storage`, and
  note that SQLite on FUSE-backed shared storage can be slower.
- **Less tested.** Termux gets less coverage than Linux/macOS; treat it as
  beta.

---

## Uninstalling

ARGO writes only inside `~/.argo` and one launcher file:

```bash
rm -rf "$HOME/.argo"
rm -f "$PREFIX/bin/argo"
```

To remove Python as well: `pkg uninstall python`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pkg: command not found` | You are not in Termux — install the Termux app. |
| `python3` too old | Run `pkg upgrade python`. |
| `argo` not found after setup | Open a new Termux session, or run `hash -r`. |
| Process killed when screen off | Run `termux-wake-lock` before `argo serve`. |

See also [`../../docs/troubleshooting.md`](../../docs/troubleshooting.md).
