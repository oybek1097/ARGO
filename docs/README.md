# ARGO Agent — Documentation

This directory is the ARGO Agent v3.0 documentation site. It renders both on
GitHub and as an [MkDocs](https://www.mkdocs.org/) (Material theme) site.

**The documentation home is [`index.md`](index.md)** — start there for the
full table of contents.

## Building the site

```bash
pip install mkdocs mkdocs-material
mkdocs serve            # live preview at http://127.0.0.1:8000
mkdocs build            # static site into ./site
```

The MkDocs configuration is [`mkdocs.yml`](mkdocs.yml).

## All pages

### Getting started

- [Introduction](introduction.md) — what ARGO is and its goals.
- [Installation](installation.md) — every install path, from try-it to Helm.
- [Quickstart](quickstart.md) — your first conversation in five minutes.
- [Configuration](configuration.md) — `~/.argo/config.json`, environment
  variables, provider API keys.

### Understanding ARGO

- [Architecture](architecture.md) — the two-component design and the IPC
  protocol.
- [Memory](memory.md) — the L0–L3 memory layers.
- [Tools](tools.md) — the built-in tool system.
- [Skills](skills.md) — the agentskills.io skill format and the curator.
- [Channels](channels.md) — messaging-channel adapters.
- [Multi-agent](multi-agent.md) — delegation, DAG workflows and the Kanban
  board.
- [Hub & Marketplace](hub.md) — the `.argopkg` format, signing, publishing.

### Operating ARGO

- [Deployment](deployment.md) — Docker Compose, Helm and cloud options.
- [Troubleshooting](troubleshooting.md) — common problems and fixes.
- [FAQ](faq.md) — honest answers about status, languages and self-hosting.

### Reference

- [CLI reference](cli.md) — every `argo_brain` command.
- [Contributing](contributing.md) — how to contribute and run the tests.

## Quick links

- Repository README: [`../README.md`](../README.md)
- Change history: [`../CHANGELOG.md`](../CHANGELOG.md)
- Contributing guide: [`../CONTRIBUTING.md`](../CONTRIBUTING.md)
- Deployment guide: [`../DEPLOYMENT.md`](../DEPLOYMENT.md)
- Full technical specification:
  [`../ARGO_AGENT_v3_Technical_Specification.md`](../ARGO_AGENT_v3_Technical_Specification.md)

## License

ARGO is distributed under the MIT license. See [`../LICENSE`](../LICENSE).
