# ARGO Agent — Documentation

ARGO Agent v3.0 is an open-source, multilingual AI agent platform built from a
**Rust gateway** (`argo-core`) and a **Python brain** (`argo-brain`). It is
specially optimized for Central Asian languages and DevOps workflows.

> **Status:** alpha. ARGO is a multi-sprint project; some subsystems are still
> being filled in. See [`../CHANGELOG.md`](../CHANGELOG.md) for the current
> state.

## Table of contents

| Page | What it covers |
|---|---|
| [Introduction](introduction.md) | What ARGO is, the two-component architecture, project goals. |
| [Installation](installation.md) | Installing via `scripts/setup.sh`, manual install, requirements. |
| [Quickstart](quickstart.md) | First run — setup wizard, chat, TUI, HTTP gateway, Telegram. |
| [Architecture](architecture.md) | The Rust core and Python brain, IPC, the memory layers, the agent loop. |
| [Configuration](configuration.md) | `~/.argo/config.json`, `ARGO_*` environment variables, provider API keys. |
| [Tools](tools.md) | The built-in tool toolsets and how tools work. |
| [Channels](channels.md) | The supported messaging channels and how to connect them. |
| [CLI reference](cli.md) | Every `argo_brain` command with usage. |
| [Contributing](contributing.md) | How to contribute and run the test suites. |

## Quick links

- Repository README: [`../README.md`](../README.md)
- Change history: [`../CHANGELOG.md`](../CHANGELOG.md)
- Contributing guide: [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- Deployment guide: [`../DEPLOYMENT.md`](../DEPLOYMENT.md)
- Full technical specification:
  [`../ARGO_AGENT_v3_Technical_Specification.md`](../ARGO_AGENT_v3_Technical_Specification.md)

## License

ARGO is distributed under the MIT license. See [`../LICENSE`](../LICENSE).
</content>
