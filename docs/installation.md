# Installation

## Requirements

- **Python 3.11 or newer** — required for the `argo-brain` Python brain.
- **Rust / Cargo** — *optional*. Needed only to build the `argo-core` Rust
  gateway. If Cargo is absent, the brain still runs on its own.
- No third-party Python packages are required: the brain runs on the standard
  library only.

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
</content>
