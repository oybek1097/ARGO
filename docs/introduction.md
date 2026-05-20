# Introduction

## What is ARGO?

**ARGO Agent v3.0** is an open-source, multilingual AI agent platform. It lets
you run a conversational AI agent that can call tools, remember conversations,
connect to messaging platforms, coordinate multiple agents and integrate with
external services over the Model Context Protocol (MCP).

ARGO is built for two niches in particular:

- **Central Asian and multilingual use** — built-in language detection for
  Uzbek, Russian, Kazakh, Kyrgyz, Tajik and English (`uz`/`ru`/`kk`/`ky`/
  `tg`/`en`), with the agent replying in the user's detected language.
- **DevOps and sovereign deployment** — audited tool wrappers for Git, Docker,
  kubectl, Vault, SSH, Ansible and Terraform, plus compliance modules and a
  design that runs fully on-premises.

## The two-component architecture

ARGO is split into two cooperating processes:

```
User ─► Channel adapter ─► argo-core (Rust) ──IPC──► argo-brain (Python)
                           HTTP/WS gateway          agent loop + tools
```

### argo-core — the Rust gateway

`argo-core` is a small, hardened external face built on **Axum + Tokio**. It
handles the HTTP/WebSocket surface, holds the L0 working-memory ring buffer,
exposes Prometheus metrics, and forwards requests to the brain. Its release
binary is about 1.3 MB. It exposes `/api/health`, `/api/version`, `/api/chat`,
`/api/history/:uid`, `/metrics`, a `/ws/:uid` WebSocket endpoint and an
OpenAI-compatible `/v1/chat/completions` endpoint.

### argo-brain — the Python brain

`argo-brain` holds the rich AI logic: the agent loop, tool dispatch, memory
orchestration, LLM providers, skills, plugins, multi-agent coordination,
channels and MCP. It runs on the **Python standard library only** — no
third-party packages are required to try it.

The two processes communicate over a **Unix domain socket** using
line-delimited JSON (one JSON object per line).

> The Python brain can run completely on its own. It includes its own HTTP
> gateway (the `serve` command) that stands in for `argo-core` when the Rust
> binary is not built. Building `argo-core` is optional.

## Key goals

- **Run with no setup** — the default `MockProvider` works without any API
  key, so you can try the full agent loop offline.
- **Stdlib-only brain** — minimal dependencies, easy to audit and deploy.
- **Multilingual by design** — first-class Central Asian language support.
- **DevOps-ready** — audited CLI tool wrappers that fail cleanly when a CLI
  is absent.
- **Sovereign deployment** — on-premises friendly, with PII redaction, an
  append-only audit log and region-specific compliance modules
  (UZ-152, RU-152-FZ, GDPR, CN-PIPL).
- **Extensible** — a tool ABC, a 5-hook plugin API, markdown skills and MCP
  client/server support.

## Where to go next

- [Installation](installation.md) — get ARGO onto your machine.
- [Quickstart](quickstart.md) — your first conversation.
- [Architecture](architecture.md) — a deeper look at how the pieces fit.
- [FAQ](faq.md) — honest answers about project status and scope.
