# Changelog

All notable changes to the ARGO Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and
the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — argo-brain (Python brain)
- Agent core: the Plan → Execute loop (spec section 4.2)
- Memory: L0 working memory (deque) + L1 persistent (SQLite + FTS5) +
  L2 vector store (stdlib hashing vectorizer, cosine-similarity search)
- Tool system: the `Tool` ABC, a registry, and 39 built-in tools across the
  basic, web, terminal, file, text, memory, devops and data toolsets
- DevOps tools: Git, Docker, kubectl, Vault, SSH, Ansible and Terraform —
  thin, audited CLI wrappers that fail cleanly if a CLI is absent
- Data tools: sql_query, json_query, hash_text, base64, uuid, datetime
- LLM providers: `MockProvider` (no key) + real `AnthropicProvider`,
  `OpenAIProvider` and `GeminiProvider` adapters
- RL: a trajectory collector with ShareGPT / SFT / JSONL export
- Compliance modules: UZ-152, RU-152-FZ, GDPR and CN-PIPL policy modules
- Skills: an agentskills.io-compatible markdown loader with trigger matching
- Plugin system: a 5-hook API and registry (pre/post tool, on_response)
- Multi-agent: a durable SQLite Kanban board (claim/complete/retry/block),
  task delegation, mixture-of-agents and a DAG workflow runner
- Cron: a scheduler with a natural-language schedule parser
- Language detection: a uz/ru/kk/ky/tg/en heuristic
- Channels: the `Channel` ABC plus Telegram (long polling), Email
  (IMAP/SMTP), IRC (TCP), Matrix (client-server API), a generic webhook
  adapter and Slack (Events API); a `/webhook/<platform>` route
- MCP client + server: connects to external MCP servers over stdio
  (newline-delimited JSON-RPC 2.0) exposing their tools as
  `mcp_<server>_<tool>`, and exposes ARGO's own tools as an MCP server
- Security: PII redaction pipeline (email/phone/card/IP/IBAN) and an
  append-only SQLite audit log
- HTTP gateway and IPC server (Unix socket)
- CLI: `setup`, `doctor`, `chat`, `serve`, `ipc`, `telegram`, `mcp`, `selftest`
- 291 unit tests (stdlib `unittest`)

### Added — argo-core (Rust gateway)
- An Axum + Tokio HTTP gateway: `/api/health`, `/api/version`, `/api/chat`,
  `/api/history/:uid`, `/metrics`, a `/ws/:uid` WebSocket endpoint and an
  OpenAI-compatible `/v1/chat/completions` endpoint
- L0 working memory (DashMap, a per-user ring buffer)
- A Unix-socket IPC client to argo-brain
- Prometheus metrics
- Release binary: 1.3 MB

### Added — infrastructure
- `scripts/setup.sh` — a one-shot installer
- README, CHANGELOG, CONTRIBUTING, .gitignore

[Unreleased]: https://github.com/oybek1097/ARGO
