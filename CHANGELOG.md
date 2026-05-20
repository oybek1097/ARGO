# Changelog

All notable changes to the ARGO Agent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and
the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — argo-brain (Python brain)
- Agent core: the Plan → Execute loop (spec section 4.2)
- Memory: L0 working memory (deque) + L1 persistent (SQLite + FTS5) +
  L2 vector store (cosine-similarity search) + L3 knowledge graph
- Tool system: the `Tool` ABC, a registry, and 49 built-in tools across the
  basic, web, terminal, file, text, system, workflow, memory, devops and
  data toolsets
- Checkpoint & handoff: file-snapshot checkpoints with restore, and
  SQLite-backed handoff tickets (create/claim/pending)
- DevOps tools: Git, Docker, kubectl, Vault, SSH, Ansible and Terraform —
  thin, audited CLI wrappers that fail cleanly if a CLI is absent
- Data tools: sql_query, json_query, hash_text, base64, uuid, datetime
- LLM providers: `MockProvider` (no key) + real `AnthropicProvider`,
  `OpenAIProvider`, `GeminiProvider`, `OllamaProvider`, a generic
  `OpenAICompatibleProvider` (DeepSeek/Groq/Mistral/OpenRouter/Together),
  and CIS-region `YandexGPTProvider` and `GigaChatProvider`
- Observability: a Prometheus `MetricsCollector`, trace spans and a
  structured JSON logger
- Session/prompt cache: a fingerprinted per-user TTL cache
- Built-in plugins: security audit, language enforcer, PII redactor
- RL: a trajectory collector with ShareGPT / SFT / JSONL export
- Compliance modules: UZ-152, RU-152-FZ, GDPR and CN-PIPL policy modules
- Skills: an agentskills.io-compatible markdown loader with trigger matching
- Plugin system: a 5-hook API and registry (pre/post tool, on_response)
- Multi-agent: a durable SQLite Kanban board (claim/complete/retry/block),
  task delegation, mixture-of-agents and a DAG workflow runner
- Cron: a scheduler with a natural-language schedule parser
- Language detection: a uz/ru/kk/ky/tg/en heuristic
- Channels: the `Channel` ABC plus Telegram, Email (IMAP/SMTP), IRC (TCP),
  Matrix, Mattermost, Rocket.Chat, LINE, Viber, WhatsApp, Twilio SMS,
  Google Chat, Microsoft Teams, a generic webhook adapter and Slack
  (Events API); a `/webhook/<platform>` route
- Skills: an agentskills.io-compatible markdown loader and a curator
  (grading, duplicate detection, archive recommendations)
- Hub & Marketplace: an `.argopkg` package format, HMAC-signed publishing,
  a file-backed registry and a verifying install client
- Interfaces: a rich terminal UI (`tui`) and a web dashboard served at `/`
- MCP client + server: connects to external MCP servers over stdio
  (newline-delimited JSON-RPC 2.0) exposing their tools as
  `mcp_<server>_<tool>`, and exposes ARGO's own tools as an MCP server
- Security: PII redaction pipeline (email/phone/card/IP/IBAN) and an
  append-only SQLite audit log
- HTTP gateway and IPC server (Unix socket)
- CLI: `setup`, `doctor`, `chat`, `tui`, `serve`, `ipc`, `telegram`, `mcp`,
  `selftest`
- 651 unit tests (stdlib `unittest`)

### Added — argo-core (Rust gateway)
- An Axum + Tokio HTTP gateway: `/api/health`, `/api/version`, `/api/chat`,
  `/api/history/:uid`, `/metrics`, a `/ws/:uid` WebSocket endpoint and
  OpenAI-compatible `/v1/chat/completions` and `/v1/models` endpoints
- 8 Rust unit tests (memory ring buffer, config loading)
- L0 working memory (DashMap, a per-user ring buffer)
- A Unix-socket IPC client to argo-brain
- Prometheus metrics
- Release binary: 1.3 MB

### Added — infrastructure
- `scripts/setup.sh` — a one-shot installer
- Deployment: docker-compose.yml, Dockerfiles for argo-core and argo-brain,
  a Helm chart, and DEPLOYMENT.md
- Documentation: a `docs/` site (introduction, installation, quickstart,
  architecture, configuration, tools, channels, CLI, contributing)
- Release packaging: PyPI metadata, a Debian package, a Homebrew formula,
  and a cloud-init deployment template
- README, CHANGELOG, CONTRIBUTING, .gitignore

[Unreleased]: https://github.com/oybek1097/ARGO
