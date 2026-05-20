# argo-brain

The Python "brain" of ARGO Agent v3.0 — the agent loop, tool dispatch,
memory orchestration, plugins, multi-agent coordination and channel logic.

> **Status:** Working foundation. The core runs on the **Python stdlib only**
> — no install required. The real `AnthropicProvider` activates automatically
> when `ANTHROPIC_API_KEY` is set. This covers a substantial part of TZ
> Sprints 2-8 for the brain; `argo-core` (Rust) and the TUI/web front-ends
> are separate, still-pending components.

## Quick start

```bash
cd argo-brain

# Interactive chat (Mock provider — no API key needed)
python3 -m argo_brain chat

# HTTP API gateway (stands in for argo-core until the Rust binary exists)
python3 -m argo_brain serve --port 8000

# IPC server (Unix socket, line-delimited JSON — argo-core connects here)
python3 -m argo_brain ipc

# Self-check (smoke test across all subsystems)
python3 -m argo_brain selftest

# Version
python3 -m argo_brain version
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

65 tests, all passing. Written with stdlib `unittest`, so they run without
`pytest`.

## What works today

| Subsystem | Status |
|---|---|
| Agent loop (Plan → Execute) | ✅ language detect, context, tool loop, persistence |
| Memory L0 (deque) + L1 (SQLite + FTS5) | ✅ |
| LLM providers | ✅ `MockProvider` + real `AnthropicProvider` (stdlib HTTP) |
| Tools | ✅ 13 built-in: time, calc, file r/w, find, grep, http, web fetch, shell, memory |
| Skills | ✅ agentskills.io-style markdown loader + trigger matching |
| Plugins | ✅ 5-hook plugin API + registry (pre/post tool, on_response) |
| Multi-agent | ✅ durable SQLite Kanban (claim/complete/retry/block lifecycle) |
| Cron | ✅ scheduler + natural-language schedule parser |
| HTTP gateway | ✅ `/api/health`, `/api/chat`, `/api/history` |
| IPC server | ✅ Unix socket, line-delimited JSON |

## Not yet built (see the TZ roadmap)

`argo-core` (Rust gateway), 100+ more tools, 30+ messaging channels,
30+ native LLM adapters, MCP server/client, vector memory (L2), the skill
curator, TUI and web dashboard, compliance modules. These map to later
sprints in `ARGO_AGENT_v3_Texnik_Zadacha.md` section 13.

## Layout

```
argo_brain/
├── __main__.py        # CLI: chat / serve / ipc / selftest / version
├── config.py          # Settings (env + ~/.argo/config.json)
├── core/agent.py      # AgentCore — Plan→Execute loop
├── memory/            # L0 (deque) + L1 (SQLite + FTS5) + manager
├── tools/             # Tool ABC, registry, 13 built-in tools
├── skills/            # markdown skill loader (agentskills.io)
├── plugin/            # 5-hook plugin API + registry
├── multi_agent/       # durable Kanban board
├── cron/              # scheduler + NL schedule parser
├── language/          # language detection (uz/ru/kk/ky/tg/en)
├── providers/         # LLM abstraction + Mock + Anthropic
├── api/server.py      # HTTP API gateway
└── ipc/server.py      # argo-core ↔ argo-brain Unix socket IPC
```

## Providers

The default is `MockProvider`: it needs no API key and deterministically
simulates tool calls (for demos and tests). When `ANTHROPIC_API_KEY` is set
and a non-`mock` model is configured, `AnthropicProvider` is used — it calls
the real Anthropic Messages API (with tool use) over the stdlib HTTP client.

MIT license.
