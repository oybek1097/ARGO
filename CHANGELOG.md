# Changelog

All notable changes to the ARGO Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and
the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — argo-brain (Python brain)
- Agent core: the Plan → Execute loop (spec section 4.2)
- Memory: L0 working memory (deque) + L1 persistent (SQLite + FTS5)
- Tool system: the `Tool` ABC, a registry, and 21 built-in tools across the
  basic, web, terminal, file, memory and devops toolsets
- DevOps tools: Git (status/log/diff/branch/commit), Docker (ps/images)
  and kubectl — thin, audited CLI wrappers that fail cleanly if a CLI is
  absent
- LLM providers: `MockProvider` (no key) + a real `AnthropicProvider`
- Skills: an agentskills.io-compatible markdown loader with trigger matching
- Plugin system: a 5-hook API and registry (pre/post tool, on_response)
- Multi-agent: a durable SQLite Kanban board (claim/complete/retry/block)
- Cron: a scheduler with a natural-language schedule parser
- Language detection: a uz/ru/kk/ky/tg/en heuristic
- Channels: the `Channel` ABC plus Telegram (long polling), a generic
  webhook adapter and Slack (Events API); a `/webhook/<platform>` route
- MCP client: connects to external MCP servers over stdio (newline-delimited
  JSON-RPC 2.0) and exposes their tools as `mcp_<server>_<tool>`
- HTTP gateway and IPC server (Unix socket)
- CLI: `setup`, `doctor`, `chat`, `serve`, `ipc`, `telegram`, `mcp`, `selftest`
- 92 unit tests (stdlib `unittest`)

### Added — argo-core (Rust gateway)
- An Axum + Tokio HTTP gateway: `/api/health`, `/api/version`, `/api/chat`,
  `/api/history/:uid`, `/metrics`
- L0 working memory (DashMap, a per-user ring buffer)
- A Unix-socket IPC client to argo-brain
- Prometheus metrics
- Release binary: 1.3 MB

### Added — infrastructure
- `scripts/setup.sh` — a one-shot installer
- README, CHANGELOG, CONTRIBUTING, .gitignore

[Unreleased]: https://github.com/oybek1097/ARGO
