# ARGO Agent v3.0 — Documentation

ARGO Agent v3.0 is an open-source, multilingual AI agent platform built from a
**Rust gateway** (`argo-core`) and a **Python brain** (`argo-brain`). It is
specially optimized for Central Asian languages and DevOps workflows, and is
designed to run fully on-premises.

> **Project status — alpha approaching GA.** ARGO is a 12-sprint project per
> the [technical specification](../ARGO_AGENT_v3_Technical_Specification.md).
> Most core subsystems are implemented and tested; a few features are still
> roadmap-only and are marked as such on each page. See
> [`../CHANGELOG.md`](../CHANGELOG.md) for the precise current state and the
> [FAQ](faq.md) for an honest assessment.

## Where to start

If you have never run ARGO before, read these three pages in order:

1. [Installation](installation.md) — get ARGO onto your machine.
2. [Quickstart](quickstart.md) — your first conversation in five minutes.
3. [Configuration](configuration.md) — switch LLM providers and tune the agent.

## Documentation map

### Getting started

| Page | What it covers |
|---|---|
| [Installation](installation.md) | Every install path: try-it (stdlib, no install), Docker Compose, Helm, native install, PyPI. |
| [Quickstart](quickstart.md) | First run — `setup`, `doctor`, `chat`, `serve`, `telegram`. |
| [Configuration](configuration.md) | The `~/.argo/config.json` model, `ARGO_*` environment variables, provider API keys. |

### Understanding ARGO

| Page | What it covers |
|---|---|
| [Architecture](architecture.md) | The two-component design, the IPC protocol, the request flow. |
| [Memory](memory.md) | The L0–L3 memory layers. |
| [Tools](tools.md) | The built-in tool system and how tools are invoked. |
| [Skills](skills.md) | The agentskills.io-compatible skill format and the curator. |
| [Channels](channels.md) | Setting up each messaging-channel adapter. |
| [Multi-agent](multi-agent.md) | Delegation, mixture-of-agents, the DAG runner and the Kanban board. |
| [Hub & Marketplace](hub.md) | The `.argopkg` package format, signing/trust, publishing and installing. |

### Operating ARGO

| Page | What it covers |
|---|---|
| [Deployment](deployment.md) | Docker Compose, Helm and cloud options (summary of `DEPLOYMENT.md`). |
| [Troubleshooting](troubleshooting.md) | Common problems and their fixes. |
| [FAQ](faq.md) | Honest answers: project status, languages, self-hosting, vs. Hermes. |

### Reference

| Page | What it covers |
|---|---|
| [CLI reference](cli.md) | Every `argo_brain` command with usage. |
| [Contributing](contributing.md) | How to contribute and run the test suites. |
| [Introduction](introduction.md) | A short overview of ARGO and its goals. |

## Quick links

- Repository README: [`../README.md`](../README.md)
- Change history: [`../CHANGELOG.md`](../CHANGELOG.md)
- Contributing guide: [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- Deployment guide: [`../DEPLOYMENT.md`](../DEPLOYMENT.md)
- Full technical specification:
  [`../ARGO_AGENT_v3_Technical_Specification.md`](../ARGO_AGENT_v3_Technical_Specification.md)

## License

ARGO is distributed under the **MIT** license. See [`../LICENSE`](../LICENSE).
