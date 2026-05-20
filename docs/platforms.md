# Platform support

ARGO Agent v3.0 runs on several platforms, with different levels of
maturity. This page summarises what is supported, what is beta, and the
caveats for each.

ARGO has two components:

- **argo-brain** — the Python 3.12, **standard-library-only** brain
  (agent loop, tools, memory, channels). No third-party Python packages.
- **argo-core** — the Rust HTTP gateway (port `8000`). **Optional**: the
  brain runs standalone without it. The two talk over a Unix-domain socket.

## Support matrix

| Platform | Status | argo-brain | argo-core | Sandbox | Background service |
|---|---|---|---|---|---|
| **Linux** (x86-64, arm64) | ✅ Full | ✅ | ✅ builds with Cargo | ✅ namespaces / seccomp | ✅ systemd |
| **macOS** (Apple Silicon & Intel) | ✅ Full | ✅ | ✅ builds with Cargo | ⚠️ POSIX-level only | ✅ launchd |
| **Windows 10/11** | 🟡 Beta | ✅ | ⚠️ builds if Rust present | ❌ not enforced | 🟡 Service / Scheduled Task |
| **Android (Termux)** | 🟡 Beta | ✅ | ❌ not built (brain-only) | ➖ Android app sandbox | 🟡 wake-lock only |

Legend: ✅ supported · 🟡 beta · ⚠️ partial / with caveats · ❌ not available
· ➖ not applicable.

---

## Linux — fully supported

The primary, best-tested platform. Both components build and run; the IPC
socket, the namespace/seccomp sandbox and the systemd integration all work.

- Install: `./scripts/setup.sh` (one-shot) or `./scripts/install.sh`
  (native install with a systemd user service).
- Containers: `docker-compose.yml` and the Helm chart in `helm/argo-agent/`.

See [installation.md](installation.md) and
[`../DEPLOYMENT.md`](../DEPLOYMENT.md).

## macOS — fully supported

Both components build and run on Apple Silicon and Intel Macs.

- Install: `./scripts/setup.sh` or `./scripts/install.sh` (registers a
  `launchd` agent for argo-core).
- **Caveat:** ARGO's command sandbox falls back to POSIX-level isolation on
  macOS — the Linux namespace/seccomp backend is not available. Tool
  execution is somewhat less isolated than on Linux.

## Windows — beta

Native Windows support is **beta**. The stdlib brain runs well; the parts
still being hardened are the IPC link and sandboxing.

- Install: `release\windows\install.ps1` (PowerShell). It installs the
  brain, builds argo-core if Rust is present, and adds an `argo` launcher
  to the per-user PATH.
- Background service: `release\windows\argo-service.ps1` registers a
  Windows Service (when elevated) or a per-user Scheduled Task.
- Guide: [`../release/windows/README.md`](../release/windows/README.md).

**Caveats:**

- **IPC socket (AF_UNIX).** Windows 10 build 17063+ and Windows 11 support
  `AF_UNIX`, and Python exposes it, but the argo-core ↔ argo-brain link is
  less exercised on Windows. If it misbehaves, run the brain standalone
  (`argo serve`) or run argo-core under WSL2. A TCP fallback is on the
  roadmap.
- **Sandbox not enforced.** ARGO's namespace/seccomp sandbox is
  Unix-specific and does not apply on native Windows. Do not run untrusted
  skills or plugins there.
- **Service registration is best-effort** — for production wrap `argo ipc`
  with a dedicated service host (NSSM / WinSW).
- **Recommended alternative:** for a fully supported experience on a
  Windows machine, run ARGO inside **WSL2** with `scripts/setup.sh`.

## Android (Termux) — beta, brain-only

ARGO runs on Android through [Termux](https://termux.dev) in **brain-only
mode**: the stdlib Python brain runs standalone and `argo-core` is **not**
built.

- Setup: `release/termux/setup.sh` installs `python` via `pkg`, sets up
  `~/.argo`, and installs an `argo` launcher.
- Guide: [`../release/termux/README.md`](../release/termux/README.md).

**Caveats:**

- **Brain-only** — no `argo-core` and no IPC link. The brain's built-in
  `argo serve` provides the HTTP gateway role.
- ARGO's own sandbox does not apply; the Android app sandbox isolates
  Termux at the OS level instead.
- Android suspends background processes — use `termux-wake-lock` for
  long-running sessions.
- Phone-class CPU, memory and storage constraints apply.

---

## Choosing a platform

| If you want… | Use |
|---|---|
| Production deployments, full sandboxing, the IPC gateway | **Linux** (bare metal, Docker or Kubernetes) |
| Local development on a Mac | **macOS** |
| ARGO running on a Windows machine, fully supported | **WSL2** on Windows |
| ARGO running on Windows itself | **Windows native (beta)** |
| ARGO on an Android phone or tablet | **Termux (beta, brain-only)** |

## Common ground

Regardless of platform:

- The brain needs **Python 3.12+** and **no third-party packages**.
- `argo-core` is optional everywhere; building it needs the **Rust
  toolchain** (Cargo).
- Configuration and data live under `~/.argo` (`%USERPROFILE%\.argo` on
  Windows), relocatable with the `ARGO_HOME` environment variable.
- Verify any install with `argo doctor` and `argo selftest`.
