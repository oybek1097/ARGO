# ARGO Agent v3.0

> An open-source, multilingual AI agent platform — **Rust gateway + Python brain**.
> Specially optimized for Central Asian languages and DevOps.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-alpha-orange)
![Tests](https://img.shields.io/badge/tests-84%20passing-brightgreen)

ARGO aims for feature parity with the Hermes Agent ecosystem and adds
exclusive functionality for Central Asian and sovereign-deployment niches.
Full technical specification:
[`ARGO_AGENT_v3_Technical_Specification.md`](ARGO_AGENT_v3_Technical_Specification.md).

---

## Quick start

```bash
# One-shot install (checks the toolchain, builds argo-core, configures)
./scripts/setup.sh

# or manually:
cd argo-brain
python3 -m argo_brain setup      # interactive setup wizard
python3 -m argo_brain doctor     # diagnostics
python3 -m argo_brain chat       # interactive conversation (no API key)
python3 -m argo_brain serve      # HTTP gateway
python3 -m argo_brain telegram   # Telegram bot
```

The `argo-brain` core runs on the **Python stdlib only** — no install
needed to try it.

## Repository layout

```
ARGO/
├── argo-core/          # Rust gateway (Axum + Tokio) — HTTP, IPC, L0 memory, metrics
├── argo-brain/         # Python brain — agent loop, tools, memory, channels, plugins
├── scripts/setup.sh    # one-shot installer
├── ARGO_AGENT_v3_Technical_Specification.md   # full technical spec
├── ARGO_Executive_Summary.md                  # one-page summary
├── ARGO_Hermes_Parity_Matrix.md               # Hermes ↔ ARGO feature matrix
└── LICENSE             # MIT
```

## Current status (alpha)

ARGO is a **12-sprint** project per the spec. Completed so far:

| Component | Status |
|---|---|
| `argo-core` — Rust gateway (`/api/health`, `/api/chat`, `/api/history`, `/metrics`) | ✅ working (1.3 MB binary) |
| `argo-brain` — agent loop (Plan→Execute), 13 built-in tools | ✅ working |
| Memory — L0 (deque) + L1 (SQLite + FTS5) | ✅ |
| LLM providers — Mock + Anthropic | ✅ |
| Skills, plugins (5 hooks), Kanban multi-agent, cron | ✅ |
| Language detection — uz/ru/kk/ky/tg/en | ✅ |
| Channels — Telegram, generic webhook, Slack | ✅ |
| IPC (argo-core ↔ argo-brain) | ✅ |
| Setup wizard + doctor | ✅ |
| Remaining 27+ channels, TUI, web dashboard, MCP, 100+ tools | 🔜 later sprints |

Roadmap: spec section 13. Change history: [`CHANGELOG.md`](CHANGELOG.md).

## Architecture

```
User ─► Channel adapter ─► argo-core (Rust) ──IPC──► argo-brain (Python)
                           HTTP/WS gateway          agent loop + tools
```

`argo-core` is the small, hardened external face; `argo-brain` holds the
rich AI logic. They communicate over a Unix socket using line-delimited
JSON (spec section 3.4).

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE).
