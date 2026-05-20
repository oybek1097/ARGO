# Installation

ARGO offers several install paths. Pick the one that matches your goal:

| Path | Best for | Needs |
|---|---|---|
| [Try it — no install](#option-0-try-it-no-install) | A quick offline look at the agent loop | Python 3.11+, the repo |
| [One-shot installer](#option-1-one-shot-installer-recommended) | A normal local install | Python 3.11+, optionally Cargo |
| [Manual install](#option-2-manual-install) | Full control over each step | Python 3.11+, optionally Cargo |
| [PyPI](#option-3-pypi) | Installing the brain as a package | Python 3.11+ |
| [Docker Compose](#option-4-docker-compose) | A two-service local/server deployment | Docker |
| [Helm / Kubernetes](#option-5-helm-kubernetes) | A cluster deployment | A Kubernetes cluster, Helm |

## Requirements

- **Python 3.11 or newer** — required for the `argo-brain` Python brain.
- **Rust / Cargo** — *optional*. Needed only to build the `argo-core` Rust
  gateway. If Cargo is absent, the brain still runs on its own.
- No third-party Python packages are required: the brain runs on the standard
  library only.

## Option 0 — try it, no install

Because the brain is **stdlib-only**, you can run the full agent loop straight
from a clone with no install step and no API key:

```bash
git clone https://github.com/oybek1097/ARGO.git
cd ARGO/argo-brain
python3 -m argo_brain chat
```

This uses the built-in `MockProvider`, which deterministically simulates the
agent loop offline. It is the fastest way to see ARGO work. When you are ready
for a real install, continue with one of the options below.

## Option 1 — one-shot installer (recommended)

The repository ships a single installer script. From the repository root:

```bash
./scripts/setup.sh
```

The script:

1. Checks the toolchain (verifies Python 3.11+, detects Cargo).
2. Creates the `~/.argo` directory layout (`data/`, `skills/`, `plugins/`).
3. Builds `argo-core` with `cargo build --release` **if** Cargo is available.
4. Hands off to the interactive `argo_brain setup` wizard.

The script is safe to re-run. You can override the install location by setting
`ARGO_HOME` before running it:

```bash
ARGO_HOME=/opt/argo ./scripts/setup.sh
```

## Option 2 — manual install

If you prefer to do it by hand:

```bash
git clone https://github.com/oybek1097/ARGO.git
cd ARGO/argo-brain

# Run the interactive setup wizard
python3 -m argo_brain setup

# Verify the installation
python3 -m argo_brain doctor
```

Building the optional Rust gateway:

```bash
cd ARGO/argo-core
cargo build --release
# binary: argo-core/target/release/argo-core  (~1.3 MB)
```

## Option 3 — PyPI

A published PyPI package (`pip install argo-brain`) is planned for the GA
release so the brain can be installed as a standalone package and invoked as
`argo` / `python3 -m argo_brain` from anywhere.

> **Roadmap.** PyPI publication is not yet available. Until then, install from
> a clone with Option 0, 1 or 2. The brain has no third-party dependencies, so
> the only practical difference a PyPI release adds is the convenience of not
> cloning the repository.

## Option 4 — Docker Compose

The repository ships a `docker-compose.yml` at its root that runs both
services (argo-core and argo-brain) with shared volumes for the IPC socket and
persistent data:

```bash
git clone https://github.com/oybek1097/ARGO.git
cd ARGO
docker compose up -d --build
curl http://localhost:8000/api/health
```

See [Deployment](deployment.md) and [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for
the full Compose reference.

## Option 5 — Helm / Kubernetes

A Helm chart lives in `helm/argo-agent/`. It deploys argo-core and argo-brain
as two containers in one pod, sharing an `emptyDir` volume for the IPC socket:

```bash
helm install argo ./helm/argo-agent
```

See [Deployment](deployment.md) for chart values and overrides.

## The `~/.argo` directory layout

Both the installer and the setup wizard create a per-user data directory.
By default this is `~/.argo`; it can be relocated with the `ARGO_HOME`
environment variable.

```
~/.argo/
├── config.json     # main configuration file
├── env             # optional: exported API keys (created if you give a key)
├── data/           # SQLite databases (memory, kanban, audit log, ...)
├── skills/         # markdown skill files
└── plugins/        # plugin files
```

## Verifying the install

Run the built-in diagnostics:

```bash
python3 -m argo_brain doctor
```

`doctor` checks the Python version, the configuration file, the data
directory, whether `ANTHROPIC_API_KEY` is set, the presence of the `argo-core`
binary, and that the brain package imports cleanly. A missing API key
(mock mode) and a missing `argo-core` binary are not treated as fatal.

You can also run the smoke test, which exercises the main subsystems:

```bash
python3 -m argo_brain selftest
```

## Containers

The repository also ships `docker-compose.yml`, Dockerfiles for both
components and a Helm chart. See [`../DEPLOYMENT.md`](../DEPLOYMENT.md) for
container and Kubernetes deployment.

## Next steps

- [Quickstart](quickstart.md) — run ARGO for the first time.
- [Configuration](configuration.md) — tune `~/.argo/config.json` and the
  environment variables.
- [Deployment](deployment.md) — Docker Compose and Helm in detail.
- [Troubleshooting](troubleshooting.md) — fixes if the install misbehaves.
