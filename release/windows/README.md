# ARGO Agent v3.0 — Windows beta

> **Status: BETA.** Native Windows support is new and has known limitations.
> Linux and macOS remain the fully supported platforms. See
> [`../../docs/platforms.md`](../../docs/platforms.md) for the support matrix.

ARGO consists of two components:

- **argo-brain** — the Python 3.12, **standard-library-only** brain. It runs
  the agent loop, tools, memory and channels. No `pip install` is required.
- **argo-core** — the Rust gateway (HTTP API on port `8000`). It is
  **optional**: the brain runs standalone without it. Building it on Windows
  requires the Rust toolchain.

On Windows the brain works well in standalone mode. The argo-core ↔
argo-brain IPC link is the part still being hardened — see
[Known limitations](#known-limitations).

---

## Prerequisites

| Requirement | Needed for | How to get it |
|---|---|---|
| Windows 10 (build 17063+) or Windows 11 | All of ARGO | — |
| **Python 3.12 or newer** | argo-brain (required) | <https://www.python.org/downloads/windows/> or `winget install Python.Python.3.12` |
| **Rust / Cargo** | argo-core (optional) | <https://rustup.rs> |
| PowerShell 5.1+ (ships with Windows) | Running the installer | — |

When installing Python, tick **"Add python.exe to PATH"** so the installer
can find it.

---

## One-command install

Open **PowerShell**, change into the repository's `release\windows` folder,
and run:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

`-ExecutionPolicy Bypass` is needed only for this one invocation; it does not
change your system's policy permanently.

What the installer does (it is **idempotent** — safe to re-run):

1. Finds a Python 3.12+ interpreter (`python`, `python3` or the `py` launcher).
2. Detects Cargo. If present, it builds `argo-core` with
   `cargo build --release`; if absent, that step is **skipped with a note**
   and ARGO runs in brain-only mode.
3. Copies the stdlib-only `argo_brain` package to `%USERPROFILE%\.argo\lib`.
4. Creates the `%USERPROFILE%\.argo\` directory layout.
5. Installs an `argo.cmd` launcher into `%USERPROFILE%\.argo\bin` and adds
   that directory to your **per-user PATH** (no Administrator rights needed).

Useful options:

```powershell
# Install to a custom data directory:
powershell -ExecutionPolicy Bypass -File install.ps1 -ArgoHome D:\argo

# Force brain-only mode even if Cargo is installed:
powershell -ExecutionPolicy Bypass -File install.ps1 -SkipCore
```

> **Open a new terminal after installing** so the updated PATH takes effect.

---

## Running ARGO

From a new terminal (cmd.exe or PowerShell):

```powershell
argo setup      # interactive first-run setup wizard
argo doctor     # diagnostics
argo chat       # interactive conversation (Mock provider, no API key)
argo serve      # HTTP gateway on http://127.0.0.1:8000
argo ipc        # IPC server (the link argo-core connects to)
```

If `argo-core` was built, `argo core` launches the Rust gateway:

```powershell
argo core
```

### Running ARGO in the background

To keep the brain's IPC server running unattended, use the service helper:

```powershell
# Register and start. Run "As Administrator" for a Windows Service;
# otherwise it falls back to a per-user Scheduled Task automatically.
powershell -ExecutionPolicy Bypass -File argo-service.ps1 -Action Install

# Check status / remove:
powershell -ExecutionPolicy Bypass -File argo-service.ps1 -Action Status
powershell -ExecutionPolicy Bypass -File argo-service.ps1 -Action Uninstall
```

Force a particular backend with `-Mode Service` or `-Mode Task`.

---

## Verification

```powershell
# 1. The brain imports and reports its version:
argo version

# 2. Diagnostics — checks Python version, config, data dir, argo-core:
argo doctor

# 3. Smoke test — exercises the agent loop, tools, memory, kanban:
argo selftest

# 4. A one-shot offline conversation:
argo chat
#    then type:  hello
#    then:       /exit
```

A healthy beta install shows `argo doctor` passing every check except
optionally `ANTHROPIC_API_KEY` (mock mode is fine) and `argo-core binary`
(brain-only mode is fine). `argo selftest` should print **"All checks
passed."**

If `argo serve` is running, in another terminal:

```powershell
curl http://127.0.0.1:8000/api/health
```

---

## Known limitations (beta)

Be aware of these before relying on Windows for anything important:

- **IPC socket (AF_UNIX).** argo-core and argo-brain talk over a Unix-domain
  socket. Windows 10 build 17063+ and Windows 11 support `AF_UNIX`, and
  Python's `socket` module exposes it — but this path is **less exercised**
  than on Linux. If the IPC link misbehaves, run the brain standalone
  (`argo serve` / `argo chat`) which does not need the socket, or run
  argo-core under WSL2. A TCP fallback for the IPC link is on the roadmap.
- **Sandbox backends are Unix-oriented.** ARGO's command/process sandboxing
  is built around Unix primitives (namespaces, `seccomp`, POSIX permissions).
  On native Windows these protections are **not enforced** the same way.
  Treat tool execution on Windows as less isolated; do not run untrusted
  skills/plugins. For full sandboxing, use Linux or WSL2.
- **Service registration is best-effort.** The plain `sc.exe` service has no
  built-in auto-restart and runs in a console-less context. For production,
  wrap `argo ipc` with a dedicated service host (NSSM or WinSW). The
  Scheduled Task fallback is per-user and starts at logon.
- **Path / shell tools.** Some built-in tools assume POSIX paths and shells.
  Behaviour of shell/file tools may differ from Linux/macOS.
- **Not all channels are tested on Windows.** Network channels generally
  work (stdlib `http`/`ssl`), but they receive less Windows-specific testing.

### Recommended alternative: WSL2

For a fully supported experience on a Windows machine, install
[WSL2](https://learn.microsoft.com/windows/wsl/) and run ARGO inside a Linux
distribution using `scripts/setup.sh`. WSL2 gives you the complete sandbox
and IPC behaviour. The native installer in this folder is for users who
specifically want ARGO running on Windows itself.

---

## Uninstalling

ARGO does not write outside `%USERPROFILE%\.argo`. To remove it:

```powershell
# Remove the background service/task (if registered):
powershell -ExecutionPolicy Bypass -File argo-service.ps1 -Action Uninstall

# Remove the data/install directory:
Remove-Item -Recurse -Force "$env:USERPROFILE\.argo"
```

Then remove `%USERPROFILE%\.argo\bin` from your user PATH via
**Settings → System → About → Advanced system settings → Environment
Variables**, or with PowerShell.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `install.ps1` cannot find Python | Install Python 3.12+ and ensure "Add to PATH" was selected, then re-run. |
| `argo` is not recognised | Open a **new** terminal; the PATH change applies only to new shells. |
| argo-core was skipped | Cargo is not installed. Install Rust from <https://rustup.rs> and re-run `install.ps1`. |
| Script blocked by execution policy | Always invoke as `powershell -ExecutionPolicy Bypass -File install.ps1`. |
| IPC errors between core and brain | Run the brain standalone (`argo serve`), or run argo-core under WSL2. |

For the general FAQ see [`../../docs/troubleshooting.md`](../../docs/troubleshooting.md).
