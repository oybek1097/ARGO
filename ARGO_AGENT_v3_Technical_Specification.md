# ARGO AGENT v3.0 — Technical Specification (TZ)

**Status:** Project document (Draft, May 2026)
**Document version:** 1.0
**Owner:** ARGO Agent Project
**Based on the analysis of:** Hermes Agent v0.14.0 "Foundation Release" (NousResearch, 16 May 2026)

---

## 0. Abstract (Executive Summary)

ARGO Agent is an open-source, independent, multilingual AI agent platform. **Goal:** to achieve a measurable advantage over Hermes Agent and other modern agent frameworks in terms of architecture and performance, while also providing dedicated localization for the Central Asia and DevOps niches.

### About the "100,000x more powerful" claim

This is a marketing phrase — it cannot be measured in engineering terms. Nonetheless, we break down the goal behind it into measurable metrics:

| Metric | Hermes v0.14.0 | ARGO v3.0 target | Ratio |
|---|---|---|---|
| Idle RAM (gateway process) | ~400 MB | **<20 MB** (Rust core) | **20x less** |
| Cold start (interactive CLI) | ~1.5 s (v0.14 optimization) | **<150 ms** | **10x faster** |
| Tool dispatch latency (intra-process) | ~10 ms (Python) | **<1 ms** (Rust IPC) | **10x faster** |
| Concurrent WS connections/node | ~5,000 (Python asyncio) | **>50,000** (Tokio + Axum) | **10x more** |
| Per-request P50 latency (excl. LLM) | ~80 ms | **<30 ms** | **2.7x faster** |
| Memory ingestion throughput | ~500 msg/s | **>10,000 msg/s** | **20x more** |
| Binary size (gateway, stripped) | N/A (Python) | **<5 MB** | new |
| Cold deps (full install) | ~800 MB | **<200 MB** core, lazy extras | **4x smaller** |
| Central Asian languages | 0 (none) | **5 native** (uz, kk, ky, tg, tk) | new |
| Native DevOps integrations | 0 | **Vault, K8s, Proxmox, SSH, Ansible** | new |

**Geometric mean:** ~10x improvement across each metric. "100,000x" is the product of 11 independent 10x improvements. A realistic conclusion: **an order-of-magnitude (10-30x) improvement on each metric, achieved jointly across many metrics**.

### Key differentiators (ARGO Unique Selling Points)

1. **Bicultural-by-design**: first-class language support for English/Russian/Uzbek/Kazakh/Kyrgyz/Tajik/Turkmen — not just at the UI level, but at the agent reasoning and response level
2. **Rust gateway, language-agnostic brain**: argo-core is in Rust, argo-brain is in Python, but the brain can be written in another language (Go, Rust, TypeScript) — via Unix socket IPC
3. **DevOps-native**: Vault, Kubernetes, Proxmox, SSH, Ansible, Docker, Terraform — as built-in tools (in Hermes these are absent or available only through skills)
4. **Hermes-compatible**: fully conformant to the agentskills.io standard, Hermes skills can be imported, connects to Hermes MCP servers, identical OpenAI proxy
5. **Compliance-friendly**: defaults aligned with the Personal Data Law of the Republic of Uzbekistan, Russia 152-FZ, and GDPR. PII redaction, audit log, sovereign deployment
6. **Self-improving + self-maintaining**: skill curator, dialectic user modeling, reflection loop — parity with Hermes, but with new metrics

### Success Criteria

For the ARGO v3.0 GA (General Availability) release, all of the following must be met:

| # | Criterion | Target value |
|---|---|---|
| 1 | Hermes-parity coverage | ≥95% of features (across the 18 categories above) |
| 2 | Performance ratios | all 11 metrics ≥ the target level |
| 3 | Test coverage | ≥85% unit, ≥70% integration |
| 4 | All CI checks green | on every PR: lint, type, test, security scan |
| 5 | Documentation completeness | ≥1 page per feature, API reference 100% |
| 6 | Native bench (vs Hermes) | at least 2x faster on every public benchmark |
| 7 | OS support | Linux/macOS/Windows/WSL2/Termux clean install + smoke test |
| 8 | Security audit | external audit, no open P0 or P1 findings |
| 9 | i18n coverage | UI in 25+ languages, agent reasoning in 7+ languages at native quality |
| 10 | First-month metrics (post-launch) | ≥1,000 GitHub stars, ≥50 contributors, ≥10 published skills |

---

## 1. Goals and boundaries

### 1.1 Functional Goals

| # | Goal | Detail |
|---|---|---|
| F1 | Full Hermes-parity feature set | implementation across every component in this document |
| F2 | Native support for Central Asian languages | tokenization, language detection, response routing, localization |
| F3 | Built-in DevOps tools | Vault, K8s, Proxmox, SSH, Ansible, Terraform, Docker, ArgoCD |
| F4 | 30+ messaging platforms | the 22 in Hermes + Yandex.Messenger, VK, Mango Office, MyChat, Astra Linux Communicator |
| F5 | Multi-runtime brain | Python first; Go and Rust ports in v3.5+ |
| F6 | Sovereign deployment | Russia, Uzbekistan, China data residency; airgapped mode |
| F7 | Programmatic Tool Calling | Python scripts with tool access (Hermes execute_code parity) |
| F8 | Plugin marketplace | Skills Hub + Plugin Hub, both agentskills.io-compatible |

### 1.2 Non-Functional Goals

| # | Goal | Target value |
|---|---|---|
| NF1 | Gateway throughput | ≥10,000 RPS (per node, simple chat) |
| NF2 | Brain throughput | ≥1,000 RPS (per node, tools enabled) |
| NF3 | WebSocket fan-out | ≥50,000 concurrent connections per node |
| NF4 | Memory write latency P99 | <10 ms (L1 + L2) |
| NF5 | Memory read latency P99 | <50 ms (full 3-layer smart context) |
| NF6 | Cold start (CLI) | <150 ms first paint |
| NF7 | Idle RAM (core only) | <20 MB |
| NF8 | Idle RAM (core + brain) | <120 MB |
| NF9 | Binary size (core, release) | <5 MB |
| NF10 | Container image size | <100 MB (core), <300 MB (brain) |
| NF11 | Disk usage (data fresh install) | <50 MB |
| NF12 | Network egress (idle) | 0 (no telemetry by default) |
| NF13 | Uptime SLO (hosted instance) | 99.9% (post-GA) |

### 1.3 Non-goals (what we will not do)

| # | Non-goal | Reason |
|---|---|---|
| NG1 | Closed-source components | MIT-only |
| NG2 | Mandatory cloud account | self-hosted first |
| NG3 | Telemetry default ON | privacy-first |
| NG4 | Single-tenant only | multi-tenancy must be supported |
| NG5 | Mobile-native apps (iOS/Android binary) | reachability via the messaging gateway is sufficient |
| NG6 | LLM training | ARGO consumes models, but model training belongs to Nous Research, OpenAI, and others |
| NG7 | IDE-bound copilot | like Hermes, we add ACP support but it is not the focus |
| NG8 | Tool catalog quality policing | community-driven, but with a signed trust signal |

---

## 2. Hermes vs ARGO target feature matrix

(The full matrix is in Appendix A. This is an abridged version.)

| Category | Hermes v0.14 | ARGO v3.0 | Advantage |
|---|---|---|---|
| Core language | Python | **Rust + Python** | ARGO |
| Cold start | ~1.5s | **<150ms** | ARGO 10x |
| Idle RAM | ~400 MB | **<20 MB** | ARGO 20x |
| Built-in tools | ~70 | **≥120** | ARGO |
| Messaging platforms | 22 | **≥30** | ARGO |
| Terminal backends | 7 | **≥12** | ARGO |
| LLM provider integrations | ~20 native | **≥30 native** + LiteLLM 200+ | ARGO |
| Memory layers | 3 | **4** (+ optional knowledge graph) | ARGO |
| Plugin types | 3 | **5** (+ skill providers, channel adapters) | ARGO |
| UI languages | 7 + 3 content | **25 UI + 7 first-class agent** | ARGO |
| OS support | 5 (L/m/W/WSL/Termux) | **6** (+ FreeBSD) | ARGO |
| MCP | server + client | **server + client + gateway** | ARGO |
| Multi-agent | Kanban + delegate + MoA | **Kanban + delegate + MoA + DAG workflows** | ARGO |
| DevOps stack | none | **Vault, K8s, Proxmox, SSH, Ansible, TF, Docker, ArgoCD** | **ARGO exclusive** |
| Sovereign deployment | none | **RU/UZ/CN compliance, airgapped** | **ARGO exclusive** |
| Central Asian languages | none | **5 native** | **ARGO exclusive** |
| GitHub stars (start) | 140,000 (in 3 months) | 0 → target 5,000 (in 3 months) | Hermes |
| Contributors | 295+ | 1 → target 50+ (in 3 months) | Hermes |
| Documentation site | hermes-agent.nousresearch.com/docs | argo-agent.io/docs (to be created) | Hermes |

---

## 3. System architecture

### 3.1 High-level diagram

```
                            ┌──────────────────────────────────────────┐
                            │                  USER                    │
                            │  (Telegram/Discord/Slack/WhatsApp/CLI…)  │
                            └─────────────────────┬────────────────────┘
                                                  │
                            ┌─────────────────────▼────────────────────┐
                            │    CHANNEL ADAPTERS (30+ platforms)      │
                            │     [Python: argo-brain/channels/]       │
                            └─────────────────────┬────────────────────┘
                                                  │ HTTP / WS
                            ┌─────────────────────▼────────────────────┐
                            │            ARGO-CORE (Rust)              │
                            │  ┌────────────────────────────────────┐  │
                            │  │  Axum HTTP+WS Gateway              │  │
                            │  │  - /api/chat, /api/history         │  │
                            │  │  - /v1/chat/completions            │  │
                            │  │  - /v1/responses                   │  │
                            │  │  - /v1/embeddings                  │  │
                            │  │  - /ws/{uid}, /mcp                 │  │
                            │  │  - /api/jobs, /api/skills          │  │
                            │  └─────────────┬──────────────────────┘  │
                            │  ┌─────────────▼──────────────────────┐  │
                            │  │  L0/L1 Memory (DashMap + SQLite)   │  │
                            │  │  Token Compression                 │  │
                            │  │  Audit Log                          │  │
                            │  │  Rate Limiting + Quotas            │  │
                            │  │  PII Redaction Pipeline            │  │
                            │  │  Linux: seccomp-bpf + rlimits      │  │
                            │  └─────────────┬──────────────────────┘  │
                            └────────────────┼──────────────────────────┘
                                             │ Unix Socket IPC (line-delimited JSON)
                            ┌────────────────▼──────────────────────────┐
                            │           ARGO-BRAIN (Python)              │
                            │  ┌──────────────────────────────────────┐  │
                            │  │  Plan → Execute → Reflect Loop       │  │
                            │  │  /goal Ralph loop                    │  │
                            │  │  Plugin hooks (pre/post/transform)   │  │
                            │  │  Streaming (SSE + chunked)           │  │
                            │  │  Language detection + routing       │  │
                            │  └─────┬───────────────────────┬────────┘  │
                            │   ┌────▼─────┐         ┌──────▼──────┐    │
                            │   │  Tools   │         │   Skills    │    │
                            │   │  120+    │         │   Library   │    │
                            │   │ (registry│         │  + Curator  │    │
                            │   │  + MCP   │         │  + Bundles  │    │
                            │   │  client) │         │  + Taps     │    │
                            │   └────┬─────┘         └─────────────┘    │
                            │   ┌────▼─────────────────────────────┐    │
                            │   │   LLM Provider Layer             │    │
                            │   │   (LiteLLM + 30 native adapters) │    │
                            │   │   - Fallback chain               │    │
                            │   │   - OAuth (Pro accounts)         │    │
                            │   │   - Pluggable transports         │    │
                            │   └──────────────────────────────────┘    │
                            └──┬────────────────────────────────────────┘
                               │
                ┌──────────────┼────────────────────────────────────────┐
                │              │                                        │
       ┌────────▼────────┐  ┌──▼──────────┐  ┌──────────────────────┐ │
       │  L2 Memory     │  │  L3 Memory  │  │  Tool Sandboxes      │ │
       │  SQLite FTS5    │  │  Vector DB  │  │  (per-backend)       │ │
       │  + reflections  │  │  (Qdrant /  │  │  - Docker            │ │
       │  + skills       │  │   Chroma)   │  │  - SSH               │ │
       │  + kanban       │  │             │  │  - K8s pod           │ │
       │  + sessions     │  └─────────────┘  │  - Modal/Daytona     │ │
       │  + cron         │  ┌─────────────┐  │  - Vercel sandbox    │ │
       │  + trajectories │  │  L3+ KG     │  │  - Firecracker       │ │
       └─────────────────┘  │  (Optional) │  │  - Lima/Colima       │ │
                            │  Neo4j /    │  │  - Local             │ │
                            │  Memgraph   │  └──────────────────────┘ │
                            └─────────────┘                            │
                                                                       │
       ┌───────────────────────────────────────────────────────────────┘
       │
       ▼ (observability — out-of-band)
   ┌─────────────────────────────────────────────┐
   │  OpenTelemetry (traces, metrics, logs)      │
   │  Prometheus exporter                        │
   │  Grafana dashboards (bundled)               │
   └─────────────────────────────────────────────┘
```

### 3.2 Component responsibilities

| Component | Language | Main responsibilities | Approximate file size |
|---|---|---|---|
| argo-core | Rust | Gateway, IPC, L1 memory, audit, rate-limit, sandbox | ~15,000 lines |
| argo-brain | Python 3.11+ | Agent loop, tools, skills, channels, providers, MCP | ~50,000 lines |
| argo-cli | Rust | `argo` binary, install, doctor, config, model picker | ~5,000 lines |
| argo-tui | TypeScript/React/Ink | Interactive CLI (Hermes parity) | ~10,000 lines |
| argo-web | Next.js + React | Dashboard (web UI) | ~15,000 lines |
| argo-mcp-tools | Python + TS | Bundled MCP servers (computer-use-linux, browser, etc.) | ~8,000 lines |
| argo-skills | Markdown | 150+ built-in skill markdown files | ~20,000 lines |
| argo-docs | Docusaurus | Documentation site | new |

### 3.3 Deployment topology

**Single-node (default):**
```
┌──────────────────────────────────────────┐
│           Container / VM (1)             │
│  ┌─────────────────────────────────────┐ │
│  │ argo-core (Rust)        :8000      │ │
│  │ argo-brain (Python)     :8080 IPC  │ │
│  │ SQLite                  (local)    │ │
│  │ ChromaDB embedded        (local)   │ │
│  └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

**Multi-node (production):**
```
                ┌─────── Load Balancer ───────┐
                │                              │
   ┌────────────▼─────┐              ┌────────▼────────┐
   │ argo-core node-1 │              │ argo-core node-N│
   └──────┬───────────┘              └────┬────────────┘
          │ IPC                            │ IPC
   ┌──────▼───────────┐              ┌────▼────────────┐
   │ argo-brain node-1│              │ argo-brain node-N│
   └──────┬───────────┘              └────┬────────────┘
          │                                │
          └────────────┬───────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │  Shared services            │
        │  - PostgreSQL (memory L2)   │
        │  - Qdrant (memory L3)       │
        │  - Redis (cache + sessions) │
        │  - HashiCorp Vault          │
        │  - S3-compatible storage    │
        └─────────────────────────────┘
```

**Airgapped (sovereign):**
```
The same multi-node topology, but instead of external LLM providers:
  - Ollama cluster (local GPU)
  - vLLM cluster (local GPU)
  - Yandex GPT API (Russia data residency)
  - SberCloud GigaChat (Russia)
  - Tencent Hunyuan (China)
  No external internet required. A hosts file instead of DNS.
```

### 3.4 IPC protocol (argo-core ↔ argo-brain)

Line-delimited JSON over Unix sockets. Each message is a single line (terminated with `\n`).

**Brain → Core (callbacks and statistics):**
```json
{"action":"get_history","user_id":"u123","limit":30}
{"action":"fts_search","user_id":"u123","query":"vault setup"}
{"action":"save_goal","session_id":"s456","user_id":"u123","goal":"refactor auth"}
{"action":"audit","user_id":"u123","action_name":"tool_call","tool":"kubectl","preview":"..."}
```

**Core → Brain (LLM request):**
```json
{
  "id": "uuid",
  "user_id": "u123",
  "message": "deploy nginx to prod cluster",
  "language": "uz",
  "channel": "telegram",
  "session_id": "s456",
  "attachments": [{"type":"image","url":"s3://..."}],
  "metadata": {"client_ip":"...","trust_level":"low"}
}
```

**Brain → Core (response):**
```json
{
  "id": "uuid",
  "content": "✅ Deploy started. Watching rollout...",
  "language": "uz",
  "model": "claude-sonnet-4-6",
  "tools_used": ["kubectl","vault"],
  "iterations": 3,
  "duration_ms": 4520,
  "tokens": {"input":1200,"output":350},
  "error": null,
  "stream_chunks": null
}
```

**Streaming variant** — `chunk` messages stored by Core may arrive from the brain:
```json
{"id":"uuid","type":"chunk","delta":"deploy "}
{"id":"uuid","type":"chunk","delta":"started"}
{"id":"uuid","type":"tool_start","name":"kubectl","args":{...}}
{"id":"uuid","type":"tool_end","name":"kubectl","result_preview":"..."}
{"id":"uuid","type":"done","model":"...","tools_used":[...]}
```

---

## 4. Components in detail

### 4.1 argo-core (Rust gateway)

**Purpose:** a hardened, robust external face with a small attack surface.

**Modules:**

```
argo-core/
├── src/
│   ├── main.rs              # bootstrap, signal handling
│   ├── config.rs            # env + file config loader
│   ├── gateway/
│   │   ├── mod.rs
│   │   ├── http.rs          # Axum app
│   │   ├── ws.rs            # WebSocket handler
│   │   ├── sse.rs           # Server-Sent Events
│   │   ├── openai.rs        # OpenAI-compatible endpoints
│   │   ├── mcp.rs           # MCP HTTP + SSE transport
│   │   └── webhooks.rs      # platform webhook router
│   ├── ipc/
│   │   ├── mod.rs
│   │   ├── server.rs        # Brain → Core requests
│   │   └── client.rs        # Core → Brain calls
│   ├── memory/
│   │   ├── mod.rs
│   │   ├── working.rs       # L0 DashMap
│   │   ├── persistent.rs    # L1 SQLite (tokio-rusqlite)
│   │   └── schema.rs        # SQL schema + migrations
│   ├── security/
│   │   ├── mod.rs
│   │   ├── sandbox.rs       # Linux seccomp-bpf, rlimit
│   │   ├── redaction.rs     # PII redaction pipeline
│   │   ├── audit.rs         # append-only audit log
│   │   ├── rbac.rs          # role-based access control
│   │   └── quota.rs         # per-user rate limits
│   ├── compression/
│   │   ├── mod.rs
│   │   ├── token.rs         # context compression
│   │   └── tokenize.rs      # tiktoken-rs bindings
│   ├── observability/
│   │   ├── mod.rs
│   │   ├── otel.rs          # OpenTelemetry exporter
│   │   ├── prom.rs          # Prometheus metrics
│   │   └── log.rs           # structured tracing
│   └── lib.rs
```

**Public HTTP endpoints (Axum routes):**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | health probe + version |
| GET | `/api/version` | semver, build hash, features |
| POST | `/api/chat` | sync chat (for channel APIs) |
| POST | `/api/chat/stream` | streaming chat (SSE) |
| GET | `/api/history/:uid` | message history |
| GET | `/api/search/:uid?q=` | FTS search |
| GET | `/api/profile/:uid` | user profile |
| PUT | `/api/profile/:uid` | update profile |
| POST | `/api/goal/:sid` | set session goal |
| GET | `/api/audit?from=&to=` | audit log filter |
| WS | `/ws/:uid` | duplex stream (text + binary) |
| POST | `/v1/chat/completions` | OpenAI-compatible |
| POST | `/v1/responses` | OpenAI Responses API parity |
| POST | `/v1/embeddings` | embedding |
| GET | `/v1/models` | available models |
| POST | `/mcp` | MCP JSON-RPC |
| GET | `/mcp/sse` | MCP SSE transport |
| POST | `/api/jobs` | cron job CRUD |
| GET | `/api/jobs` | list jobs |
| POST | `/webhook/:platform` | platform webhook receiver |
| GET | `/metrics` | Prometheus scraping |

**Headers (supported by every endpoint):**

- `Idempotency-Key: <uuid>` — an identical request is executed only once within 24 hours
- `X-ARGO-Session-Id: <id>` — session continuity
- `X-ARGO-Session-Key: <hmac>` — for pluggable memory providers
- `Authorization: Bearer <token>` — JWT or API key
- `X-Request-Id: <id>` — distributed tracing (autogenerated if absent)

**Performance budgets:**

| Operation | Target P50 | Target P99 |
|---|---|---|
| HTTP route → IPC | <0.5 ms | <2 ms |
| L0 memory write | <0.05 ms | <0.2 ms |
| L0 memory read (1 user, 100 msg) | <0.1 ms | <0.5 ms |
| L1 memory write | <1 ms | <5 ms |
| L1 FTS5 query | <5 ms | <20 ms |
| Token compress (10KB) | <2 ms | <10 ms |
| Audit log write | <0.5 ms | <2 ms |
| End-to-end chat (excl. brain) | <10 ms | <30 ms |

**Security:**

- **Linux sandbox:** `seccomp-bpf` filter — the following syscalls are blocked: `mount`, `umount`, `pivot_root`, `chroot`, `ptrace`, `bpf`, `clone3` (with CLONE_NEWUSER), `unshare`, `setns`, `keyctl`, `kexec_load`, `init_module`. Only basic I/O, networking, and dynamic memory are permitted.
- **rlimit:** `RLIMIT_NOFILE=4096`, `RLIMIT_NPROC=512`, `RLIMIT_AS=4GB`, `RLIMIT_CPU=indefinite`
- **TLS:** rustls (Ring/aws-lc-rs backend), TLS 1.3 only by default, mTLS optional
- **DDoS:** per-IP rate limit (default: 100 RPS), per-user rate limit (default: 30 chat/min), per-token budget (default: 100k tokens/day free tier)
- **Audit:** every tool call, every auth event, every admin action — append-only log
- **PII redaction:** in inbound and outbound messages and logs — phone, email, IBAN/INN/STIR, credit card, IP, MAC, SSH key. Configuration: `security.redaction.enabled = true` (default ON), `security.redaction.replacements = {phone: "[PHONE]", ...}`

### 4.2 argo-brain (Python)

**Purpose:** the AI agent core — tool dispatching, memory orchestration, channel logic.

**Modules:**

```
argo_brain/
├── __init__.py
├── __main__.py             # python -m argo_brain
├── config.py               # pydantic-settings unified config
├── core/
│   ├── agent.py            # AgentCore — main loop
│   ├── lazy.py             # deferred import infrastructure
│   ├── guidance.py         # prompt optimizer
│   ├── prompt_builder.py   # system prompt assembly
│   └── personality.py      # SOUL.md loader, /personality presets
├── memory/
│   ├── manager.py          # L0+L1+L2 unified API
│   ├── working.py          # L0 deque
│   ├── persistent.py       # L1 SQLite (aiosqlite)
│   ├── vector.py           # L2 ChromaDB / Qdrant
│   ├── graph.py            # L3 KG (optional)
│   ├── user_model.py       # Honcho-style dialectic
│   ├── context_files.py    # MEMORY.md, USER.md, AGENTS.md, .argo.md
│   └── refs.py             # @ context reference expansion
├── skills/
│   ├── loader.py           # SkillLoader
│   ├── curator.py          # autonomous curator (grading, archive)
│   ├── bundles.py          # YAML skill bundles
│   ├── manifest.py         # .bundled_manifest tracking
│   └── manage.py           # skill_manage tool
├── tools/
│   ├── base.py             # Tool ABC + Toolset
│   ├── registry.py         # unified registry
│   ├── builtin/            # 120+ tools (one file per group)
│   │   ├── web.py          # web_search, x_search, http_get/post
│   │   ├── terminal.py     # shell_exec (multi-backend)
│   │   ├── file.py         # read/write/patch/list/find/grep
│   │   ├── memory.py       # memory_search, memory_remember
│   │   ├── session.py      # session_search, session_list
│   │   ├── delegation.py   # delegate_task, mixture_of_agents
│   │   ├── kanban.py       # kanban_create, kanban_claim, kanban_complete...
│   │   ├── cron.py         # cronjob
│   │   ├── code_exec.py    # execute_code (with tool access)
│   │   ├── browser.py      # 10+ browser tools
│   │   ├── computer_use.py # cross-platform
│   │   ├── vision.py       # vision_analyze
│   │   ├── image_gen.py    # image_generate
│   │   ├── video.py        # video_analyze, video_generate
│   │   ├── voice.py        # text_to_speech, speech_to_text
│   │   ├── todo.py
│   │   ├── clarify.py
│   │   ├── process.py
│   │   ├── send_message.py # cross-platform
│   │   ├── devops/
│   │   │   ├── kubectl.py
│   │   │   ├── proxmox.py
│   │   │   ├── vault.py
│   │   │   ├── ssh.py
│   │   │   ├── ansible.py
│   │   │   ├── docker.py
│   │   │   ├── terraform.py
│   │   │   └── argocd.py
│   │   ├── data/
│   │   │   ├── sql.py
│   │   │   ├── notion.py
│   │   │   └── rss.py
│   │   ├── home_assistant.py
│   │   ├── spotify.py
│   │   ├── git.py
│   │   └── email.py
│   └── mcp_client.py       # load tools from external MCP servers
├── terminals/              # multi-backend terminal
│   ├── base.py
│   ├── local.py
│   ├── docker.py
│   ├── ssh.py
│   ├── k8s_pod.py
│   ├── singularity.py
│   ├── modal.py
│   ├── daytona.py
│   ├── vercel.py
│   ├── lima.py
│   ├── firecracker.py
│   ├── podman.py
│   └── e2b.py
├── providers/
│   ├── registry.py         # KNOWN_MODELS catalog
│   ├── litellm_wrapper.py
│   ├── transports/         # pluggable transport per provider
│   │   ├── anthropic.py
│   │   ├── chat_completions.py
│   │   ├── responses_api.py
│   │   ├── bedrock.py
│   │   └── gemini.py
│   ├── oauth/              # subscription OAuth flows
│   │   ├── claude_pro.py
│   │   ├── chatgpt_pro.py
│   │   ├── supergrok.py
│   │   ├── codex.py
│   │   └── moonshot.py
│   └── failover.py
├── channels/
│   ├── base.py
│   ├── telegram.py
│   ├── discord.py
│   ├── slack.py
│   ├── whatsapp.py
│   ├── signal.py
│   ├── email.py
│   ├── teams.py            # Graph auth + webhook + delivery
│   ├── google_chat.py
│   ├── matrix.py
│   ├── mattermost.py
│   ├── line.py
│   ├── viber.py
│   ├── wechat.py
│   ├── wecom.py
│   ├── feishu.py           # + comment intelligent reply
│   ├── dingtalk.py
│   ├── qqbot.py
│   ├── yuanbao.py
│   ├── imessage.py         # BlueBubbles bridge
│   ├── simplex.py
│   ├── irc.py
│   ├── sms_twilio.py
│   ├── home_assistant.py
│   ├── yandex_messenger.py # CIS exclusive
│   ├── vk.py               # CIS exclusive
│   ├── mychat.py           # CIS exclusive (Astra Linux)
│   ├── webhook.py
│   ├── voice.py            # discord voice channel
│   └── cli.py
├── multi_agent/
│   ├── kanban.py           # durable board + heartbeat + reclaim
│   ├── delegate.py         # subagent spawn
│   ├── moa.py              # mixture of agents
│   └── dag.py              # DAG workflow runner
├── mcp/
│   ├── server.py           # ARGO as MCP server
│   ├── client.py           # ARGO consumes MCP tools
│   └── transport/
│       ├── stdio.py
│       ├── http.py
│       └── sse.py
├── plugin/
│   ├── api.py              # ArgPlugin ABC
│   ├── registry.py
│   ├── memory_provider.py  # plugin type 2
│   ├── context_engine.py   # plugin type 3
│   ├── channel_adapter.py  # plugin type 4
│   ├── skill_provider.py   # plugin type 5
│   └── builtin/
│       ├── security_audit.py
│       ├── disk_cleanup.py
│       ├── language_enforcer.py
│       ├── pii_redactor.py
│       └── compliance_uz.py
├── cron/
│   ├── scheduler.py        # APScheduler wrapper
│   ├── nl_parser.py        # natural language → cron expression
│   └── no_agent.py         # script-only watchdog mode
├── voice/
│   ├── mode.py             # push-to-talk
│   ├── discord_voice.py    # live conversations
│   ├── transcribe.py       # voice memos
│   └── tts_backends/
│       ├── elevenlabs.py
│       ├── openai.py
│       ├── xai_voices.py   # voice cloning
│       └── coqui.py
├── checkpoint/
│   ├── manager.py          # auto-snapshot + rollback
│   └── git_backend.py      # git-based snapshots
├── handoff/
│   └── transfer.py         # /handoff /claim
├── cache/
│   └── session.py          # 1-hour prompt cache
├── rl/
│   ├── trainer.py          # trajectory collector
│   ├── atropos.py          # Atropos export
│   ├── sft.py              # SFT export
│   ├── compression.py      # trajectory compression
│   └── batch.py            # batch processing
├── doctor/
│   └── health.py           # argo doctor
├── proxy/
│   └── server.py           # OpenAI-compatible proxy
├── language/
│   ├── detect.py           # fast langdetect
│   ├── locales/            # UI translations (25+)
│   ├── tokenizer/          # multi-language tokenizer hints
│   └── ca/                 # Central Asian language packs
│       ├── uz.py           # Uzbek (Latin + Cyrillic)
│       ├── kk.py           # Kazakh
│       ├── ky.py           # Kyrgyz
│       ├── tg.py           # Tajik
│       └── tk.py           # Turkmen
├── compliance/
│   ├── uz_152.py           # Uzbekistan Personal Data Law
│   ├── ru_152.py           # Russia 152-FZ
│   ├── gdpr.py
│   └── cn_pipl.py          # China PIPL
├── api/
│   ├── server.py           # FastAPI + integration
│   └── webhooks.py
├── ipc_client.py           # Brain → Core IPC
├── ipc_server.py           # entry point if standalone
└── tests/                  # >2,000 unit + integration tests
```

**Agent loop pseudocode:**

```python
async def process(self, msg: Message) -> AgentResp:
    # 1. Language detect + route
    if not msg.language:
        msg.language = await lang_engine.detect_fast(msg.content)

    # 2. User profile + dialectic model
    profile = await self.memory.profile(msg.user_id)
    if not profile:
        await self.memory.upsert_profile(msg.user_id, language=msg.language)
    user_model = await self.user_model.get(msg.user_id)  # Honcho-style

    # 3. Slash commands (early return)
    if cmd := await self.command_router.handle(msg):
        return cmd

    # 4. Build context (4-layer fusion)
    context_files = await self.context_loader.load(msg.user_id)  # MEMORY.md, USER.md, AGENTS.md, .argo.md
    refs = await self.refs.expand(msg.content)  # @file, @folder, @url, @diff
    history = await self.memory.history(msg.user_id, limit=settings.context_history)
    semantic = await self.memory.semantic_search(msg.user_id, msg.content)
    skills = await self.skills.get_relevant(msg.content)

    # 5. Personality
    soul = await self.personality.get(msg.user_id, msg.channel)

    # 6. Assemble system prompt
    system = self.prompt_builder.build(
        soul=soul,
        context_files=context_files,
        refs=refs,
        history_summary=user_model.summary,
        relevant_skills=skills,
        guidance=guidance_optimizer.get_additions(),
        language=msg.language,
        tools=self.tools.describe_for_model(model),
    )

    # 7. Prompt cache lookup
    cache_fp = fingerprint(system, history[-5:])
    cached = await self.cache.get(msg.user_id, model, cache_fp)

    # 8. Build llm_msgs (with cache_control on Anthropic)
    llm_msgs = build_llm_messages(system, history, msg, cached)

    # 9. Plan → Execute loop (max_iterations)
    for iter in range(settings.max_iterations):
        # Plugin pre-call hooks
        llm_msgs = await self.plugin_registry.transform_messages(llm_msgs)

        # Model selection (dynamic per query)
        model = self.model_selector.pick(msg.content, iter, history)

        # LLM call (with fallback chain)
        resp = await self.providers.acompletion(
            model=model, messages=llm_msgs, tools=self.tools.schemas(),
            max_tokens=settings.max_tokens, temperature=settings.temperature,
        )

        # Stream chunks → SSE
        if msg.stream:
            await self.stream_handler.emit(resp)

        # Tool calls?
        if resp.has_tool_calls:
            calls = resp.tool_calls
            # Plugin pre-tool veto
            calls = await self.plugin_registry.run_pre_tool(calls, msg.user_id)
            # Parallel execution with semaphore
            results = await self.tools.execute_parallel(calls, msg.user_id,
                                                       max_w=settings.max_parallel_tools)
            # Plugin post-tool transform
            results = await self.plugin_registry.run_post_tool(results, msg.user_id)
            llm_msgs.append(resp.message)
            for tc, r in zip(calls, results):
                llm_msgs.append({"role":"tool","tool_call_id":tc.id,"content":str(r)})
                # Track mutations (write_file, patch_file)
                if tc.name in MUTATION_TOOLS:
                    await self.mutation_verifier.verify(tc, r)
        else:
            final = resp.text
            break
    else:
        final = "❌ Max iterations exceeded."

    # 10. Persist + invalidate cache
    await self.memory.add(msg.user_id, "user", msg.content, msg.language, channel=msg.channel)
    await self.memory.add(msg.user_id, "assistant", final, msg.language, channel=msg.channel)
    await self.cache.invalidate(msg.user_id)

    # 11. Update dialectic user model (async)
    asyncio.create_task(self.user_model.observe(msg, final))

    # 12. Reflection trigger
    if iter > settings.reflect_threshold:
        await self.reflect_queue.put({"msg":msg,"final":final,"tools":tools_used})

    # 13. Trajectory export
    trajectory_collector.record(msg, final, tools_used, success=not final.startswith("❌"))

    # 14. Emit plugin events
    await self.plugin_registry.emit("on_response",
        user_id=msg.user_id, content=final, model=model)

    return AgentResp(content=final, language=msg.language, model=model,
                     tools_used=tools_used, iterations=iter+1,
                     duration_ms=int((time.time()-t0)*1000))
```

### 4.3 Memory subsystem (4 layers)

**L0 — In-process working memory (Rust DashMap + Python deque):**

- Fast real-time same-session visibility
- DashMap: per-user `VecDeque<Msg>` (max 200 messages per user)
- In parallel in the Python brain: `deque(maxlen=200)`
- Speed: 0.05 ms write, 0.1 ms read
- Lifetime: process lifetime

**L1 — Persistent (SQLite WAL):**

Schema (abridged):

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -32000;  -- 32 MB
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;

CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    importance REAL DEFAULT 1.0,
    freshness REAL DEFAULT 1.0,      -- decays over time
    channel TEXT DEFAULT 'unknown',
    parent_id TEXT,                   -- threaded conversations
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE INDEX idx_msg_user_time ON messages(user_id, created_at DESC);
CREATE INDEX idx_msg_session ON messages(session_id, created_at);

CREATE VIRTUAL TABLE messages_fts USING fts5(
    content, user_id UNINDEXED, language UNINDEXED, session_id UNINDEXED,
    content='messages', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 1'
);

-- Triggers for FTS sync (insert + delete + update)
CREATE TRIGGER msg_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid,content,user_id,language,session_id)
    VALUES(new.rowid,new.content,new.user_id,new.language,new.session_id);
END;
CREATE TRIGGER msg_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts,rowid,content,user_id,language,session_id)
    VALUES('delete',old.rowid,old.content,old.user_id,old.language,old.session_id);
END;
CREATE TRIGGER msg_au AFTER UPDATE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts,rowid,content,user_id,language,session_id)
    VALUES('delete',old.rowid,old.content,old.user_id,old.language,old.session_id);
    INSERT INTO messages_fts(rowid,content,user_id,language,session_id)
    VALUES(new.rowid,new.content,new.user_id,new.language,new.session_id);
END;

CREATE TABLE user_profiles (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    language TEXT DEFAULT 'en',
    timezone TEXT DEFAULT 'UTC',
    summary TEXT DEFAULT '',
    facts TEXT DEFAULT '{}',         -- JSON dict
    preferences TEXT DEFAULT '{}',   -- JSON dict
    user_model TEXT DEFAULT '{}',    -- Honcho dialectic JSON
    task_count INTEGER DEFAULT 0,
    token_usage_input INTEGER DEFAULT 0,
    token_usage_output INTEGER DEFAULT 0,
    trust_level TEXT DEFAULT 'unknown',  -- 'trusted','known','unknown','blocked'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    channel TEXT DEFAULT 'unknown',
    title TEXT,
    summary TEXT DEFAULT '',          -- LLM-generated session summary
    goal TEXT DEFAULT '',
    checkpoint TEXT DEFAULT '{}',
    parent_session_id TEXT,           -- for /handoff continuity
    started_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE skills (
    id TEXT PRIMARY KEY,
    user_id TEXT,                     -- NULL = global/builtin
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    trigger_kw TEXT DEFAULT '',
    category TEXT,
    quality REAL DEFAULT 0.5,
    use_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    last_used_at TEXT,
    is_builtin INTEGER DEFAULT 0,
    is_pinned INTEGER DEFAULT 0,       -- protected from curator
    is_archived INTEGER DEFAULT 0,
    tap_source TEXT,                   -- 'builtin','huggingface','custom','user'
    content_hash TEXT,
    origin_hash TEXT,                  -- for sync drift detection
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE reflections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    skill_id TEXT,
    trigger_msg_id TEXT,
    pattern_type TEXT,                 -- 'workflow','correction','preference'
    created_at TEXT NOT NULL,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE SET NULL
);

CREATE TABLE kanban_boards (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    goal TEXT DEFAULT '',
    workflow_type TEXT DEFAULT 'kanban', -- 'kanban','dag','pipeline'
    status TEXT DEFAULT 'active',
    metadata TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE kanban_tasks (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL REFERENCES kanban_boards(id) ON DELETE CASCADE,
    parent_task_id TEXT,
    title TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT DEFAULT 'todo',         -- todo, claimed, in_progress, done, blocked, failed
    agent_id TEXT,
    priority INTEGER DEFAULT 0,
    retries INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    heartbeat_at TEXT,                  -- last heartbeat
    claimed_at TEXT,
    started_at TEXT,
    completed_at TEXT,
    result TEXT,
    error TEXT,
    hallucination_score REAL DEFAULT 0,
    dependencies TEXT DEFAULT '[]',     -- JSON array of task IDs (DAG)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX idx_kt_board_status ON kanban_tasks(board_id, status);
CREATE INDEX idx_kt_heartbeat ON kanban_tasks(status, heartbeat_at) WHERE status IN ('claimed','in_progress');

CREATE TABLE cron_jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    schedule TEXT NOT NULL,             -- cron expr or natural language
    prompt TEXT NOT NULL,
    skill_ids TEXT DEFAULT '[]',
    delivery_platform TEXT,             -- where to send result
    delivery_target TEXT,               -- channel/user/etc
    enabled INTEGER DEFAULT 1,
    no_agent INTEGER DEFAULT 0,         -- script-only mode
    script TEXT,                        -- when no_agent=1
    last_run_at TEXT,
    next_run_at TEXT,
    last_status TEXT,
    last_output TEXT,
    run_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_cron_next ON cron_jobs(enabled, next_run_at);

CREATE TABLE checkpoints (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT,
    snapshot_path TEXT NOT NULL,       -- git ref or file path
    label TEXT,
    is_auto INTEGER DEFAULT 0,
    files_changed TEXT DEFAULT '[]',
    size_bytes INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    action TEXT NOT NULL,
    actor_type TEXT,                    -- 'user','agent','plugin','system'
    tool TEXT,
    args TEXT,                          -- redacted JSON
    result_preview TEXT,                -- max 200 chars
    ip_address TEXT,
    session_id TEXT,
    trust_level TEXT,
    severity TEXT DEFAULT 'info',       -- info, warn, error, security
    ts TEXT NOT NULL
);
CREATE INDEX idx_audit_user_ts ON audit_log(user_id, ts DESC);
CREATE INDEX idx_audit_sev_ts ON audit_log(severity, ts DESC);

CREATE TABLE trajectories (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    session_id TEXT,
    model TEXT,
    input TEXT NOT NULL,
    output TEXT NOT NULL,
    tools TEXT DEFAULT '[]',
    success INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.5,
    tokens_input INTEGER,
    tokens_output INTEGER,
    duration_ms INTEGER,
    exported_format TEXT,               -- NULL, 'sharegpt', 'atropos', 'sft'
    created_at TEXT NOT NULL
);

CREATE TABLE handoff_tickets (
    id TEXT PRIMARY KEY,
    from_user_id TEXT,
    to_target TEXT,                     -- can be user_id, role, or channel
    session_id TEXT,
    history_snapshot TEXT,              -- JSON snapshot of recent N messages
    goal TEXT,
    expires_at TEXT,
    claimed_at TEXT,
    claimed_by TEXT,
    created_at TEXT NOT NULL
);

-- Settings (per-user overrides)
CREATE TABLE user_settings (
    user_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (user_id, key)
);
```

**L2 — Vector (ChromaDB embedded or Qdrant):**

Default: ChromaDB embedded (single-node). Production: Qdrant (multi-node, HNSW, payload index).

```python
collection = qdrant.collection("argo_memory", vector_size=1536, distance="Cosine")
# Payload: {"user_id","role","language","session_id","ts","importance"}
# Filter on user_id + recency for fast retrieval
```

**L3 — Knowledge graph (optional):**

For users who enable it: Neo4j or Memgraph. Edges: user → fact, fact → entity, entity → entity. Built incrementally by a Honcho-style observer during conversation.

```cypher
(u:User {id:"u123"})-[:KNOWS]->(p:Person {name:"Alisher"})
(u)-[:WORKS_ON]->(proj:Project {name:"argo-agent"})
(proj)-[:USES]->(t:Technology {name:"Rust"})
```

**Compaction strategy:**

- L0: maxlen=200 (in-memory, oldest evicted)
- L1: compaction triggers when per-user `messages` ≥ `max_entries` (default: 1000):
  - Tokenize last 500 messages with LLM (summary skill)
  - Replace bottom 200 with single "summary" message (role=`system`, importance=2.0)
  - Net: keeps last ~800 messages + 1 summary
- L2: TTL 90 days unless `importance ≥ 1.5`
- L3: persistent unless explicitly deleted

### 4.4 Tool system

**Tool ABC:**

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict          # JSON schema
    requires_credentials: list[str] = []
    requires_toolsets: list[str] = []
    cost_estimate: ToolCost = ToolCost.FREE  # FREE, CHEAP, MODERATE, EXPENSIVE
    dangerous: bool = False   # requires user confirmation for mutations
    cacheable: bool = False
    cache_ttl: int = 300

    @abstractmethod
    async def run(self, user_id: str, **kw) -> ToolResult: ...

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
```

**ToolResult:**

```python
@dataclass
class ToolResult:
    content: str | list           # text or multimodal
    success: bool = True
    cost: int = 0                  # tokens consumed
    duration_ms: int = 0
    cacheable: bool = False
    media: list[Media] = ()        # images, audio, video attachments
    redacted: bool = False
    metadata: dict = field(default_factory=dict)
```

**Tool taxonomy (120+ built-in):**

| Toolset | Tools (approximate) |
|---|---|
| `web` (5) | web_search, web_fetch, http_get, http_post, web_extract |
| `search` (2) | x_search, semantic_web_search |
| `terminal` (3) | shell_exec, process (background), env_get |
| `file` (8) | read_file, write_file, patch_file, list_dir, find_files, grep_files, file_diff, file_lint |
| `memory` (4) | memory_search, memory_remember, memory_forget, session_search |
| `delegation` (3) | delegate_task, mixture_of_agents, dag_workflow |
| `kanban` (7) | kanban_create, kanban_claim, kanban_complete, kanban_block, kanban_comment, kanban_status, kanban_fan_out |
| `code_exec` (2) | execute_code (with tool access), execute_python |
| `clarify` (1) | clarify |
| `cron` (1) | cronjob (action: create/list/update/pause/resume/run/remove) |
| `browser` (12) | browser_navigate, browser_click, browser_type, browser_screenshot, browser_extract, browser_scroll, browser_wait, browser_fill_form, browser_back, browser_forward, browser_new_tab, browser_close |
| `computer_use` (1) | computer_use (cross-platform; macOS background mode) |
| `vision` (1) | vision_analyze |
| `image_gen` (1) | image_generate (FAL, DALL-E, SD, FLUX, Midjourney-compat) |
| `video` (2) | video_analyze, video_generate |
| `voice` (3) | text_to_speech, speech_to_text, voice_clone |
| `todo` (1) | todo (action: add/list/complete/delete) |
| `send_message` (1) | send_message (cross-platform) |
| `messaging` (per-platform, ~3 each) | discord_admin, telegram_admin, slack_admin (channel mgmt) |
| `devops/k8s` (6) | kubectl, kubectl_logs, kubectl_apply, k8s_port_forward, k8s_exec, helm_install |
| `devops/proxmox` (5) | proxmox_list, proxmox_create_vm, proxmox_clone, proxmox_snapshot, proxmox_migrate |
| `devops/vault` (4) | vault_get, vault_put, vault_list, vault_lease |
| `devops/ssh` (3) | ssh_exec, ssh_copy, ssh_tunnel |
| `devops/ansible` (2) | ansible_playbook, ansible_inventory |
| `devops/terraform` (3) | tf_plan, tf_apply, tf_destroy |
| `devops/docker` (5) | docker_build, docker_run, docker_ps, docker_logs, docker_compose |
| `devops/argocd` (3) | argocd_app_list, argocd_sync, argocd_diff |
| `data/sql` (3) | sql_query, sql_schema, sql_explain |
| `data/notion` (4) | notion_search, notion_create, notion_update, notion_query_db |
| `data/rss` (2) | rss_subscribe, rss_fetch |
| `git` (8) | git_status, git_diff, git_commit, git_push, git_pull, git_log, git_branch, git_pr |
| `email` (3) | email_send, email_search, email_archive |
| `home_assistant` (4) | ha_list, ha_call_service, ha_state, ha_history |
| `spotify` (7) | (plugin) |
| `safe` (placeholder) | tools available even in restricted mode |
| `rl` (10) | trajectory tools |

**Total:** ~120+ built-in tools, plus dynamic MCP tools, plus user/plugin custom tools.

**Execution pipeline:**

```
Tool call ─┐
           ├─► Plugin pre_tool veto ──┐
           │                          ├─► Tool.run() ──► Plugin transform_result ──► Plugin emit("on_tool_complete")
           ├─► Trust check            │
           ├─► Quota check            │
           ├─► Audit log              │
           └─► Confirmation prompt    │
              (if dangerous=True)     │
                                      └─► On failure: retry up to 3x with backoff
```

### 4.5 Channel adapters

**Base interface:**

```python
class Channel(ABC):
    name: str
    direction: ChannelDirection  # INBOUND, OUTBOUND, BIDIRECTIONAL
    auth: AuthMode               # TOKEN, OAUTH, WEBHOOK_SECRET

    @abstractmethod
    async def start(self): ...

    @abstractmethod
    async def stop(self): ...

    @abstractmethod
    async def send(self, target: str, message: ChannelMessage): ...

    @abstractmethod
    async def receive(self) -> AsyncIterator[ChannelMessage]: ...

    def health(self) -> ChannelHealth: ...
```

**30+ supported platforms** (Hermes 22 + ARGO additions):

Hermes parity (22): Telegram, Discord, Slack, WhatsApp, Signal, Email, Teams, Google Chat, Matrix, Mattermost, LINE, Viber, WeChat, WeCom, Feishu, DingTalk, QQBot, Yuanbao, iMessage (BlueBubbles), SimpleX, IRC, SMS (Twilio).

ARGO additions (8+):
- **Yandex.Messenger** (Russia/CIS)
- **VK Messages** (Russia/CIS)
- **MyChat** (Astra Linux Russia)
- **Mango Office** (Russia business)
- **Wire** (privacy)
- **Threema** (privacy)
- **Tox** (P2P)
- **Briar** (offline mesh)
- **Tencent Yuanbao** (extended)
- **Webhook generic** (any HTTP service)
- **CLI gateway** (Unix socket + named pipe)
- **Voice (Discord live)** — Hermes parity

**Common features all channels MUST support:**

- Voice memo transcription (sttinbound)
- Image/file/document attachment forwarding to agent
- Markdown ↔ platform-native formatting conversion
- Per-platform tool configuration overrides
- HMAC/signature verification (required, no `getattr` fallback)
- Stranger reject (configurable allowlist)
- Cross-platform `send_message` integration
- Per-channel rate limit
- Per-channel quota

### 4.6 Plugin system (5 types)

```python
# Type 1: General plugin
class ArgPlugin(ABC):
    name: str
    version: str
    description: str
    author: str
    enabled: bool = True

    async def on_load(self, registry): ...
    async def on_unload(self): ...
    async def pre_tool_call(self, tool, args, user_id) -> dict | None: ...
    async def transform_tool_result(self, tool, result, user_id) -> Any: ...
    async def transform_message(self, msg) -> Message: ...
    async def transform_terminal_output(self, out, user_id) -> str: ...
    async def on_message(self, user_id, content, channel): ...
    async def on_response(self, user_id, content, model): ...
    async def on_skill_saved(self, skill_id, content): ...
    async def on_handoff_created(self, ticket): ...
    async def handle_command(self, cmd, user_id, args) -> str | None: ...

# Type 2: Memory provider
class MemoryProvider(ABC):
    async def remember(self, user_id, fact, source): ...
    async def recall(self, user_id, query, k=5): ...
    async def forget(self, user_id, fact_id): ...
    async def export(self, user_id) -> dict: ...

# Type 3: Context engine (alternative context management)
class ContextEngine(ABC):
    async def build_context(self, user_id, query) -> str: ...

# Type 4: Channel adapter (custom messaging platform)
class ChannelAdapter(Channel): ...

# Type 5: Skill provider (alternative skill source)
class SkillProvider(ABC):
    name: str
    async def search(self, query) -> list[SkillMeta]: ...
    async def install(self, skill_id) -> str: ...
    async def update(self, skill_id) -> bool: ...
```

**v0.14.0 Hermes parity additions:**
- `ctx.llm(messages)` — plugins can call LLM through agent's active credentials
- `tool_override` flag — plugins can replace built-in tools

**Loading:**
- Local: `~/.argo/plugins/<name>.py` (auto-discovered)
- Marketplace: `argo plugins install <name>` (signed packages)
- Hot-reload: `argo plugins reload` (development mode)

### 4.7 Skill system

**Skill format (agentskills.io compatible):**

```markdown
---
name: deploy-k8s
slug: deploy-k8s
trigger: deploy, kubernetes, k8s, helm
category: devops
quality: 0.85
author: argo-team
license: MIT
requires_tools: [kubectl, helm_install, vault_get]
---

# Deploy to Kubernetes

When user asks to deploy a service to Kubernetes:

1. Verify cluster context with `kubectl config current-context`
2. Read deployment manifest (look for `k8s/`, `manifests/`, or `helm/`)
3. Check secrets in Vault (`vault_get`)
4. Apply with `kubectl apply -f` or `helm install`
5. Watch rollout: `kubectl rollout status`
6. Report final state + URL
```

**Curator pipeline (every 7 days, or `argo curator run`):**

```
1. Inventory: scan ~/.argo/skills/, count usage stats
2. Grade: LLM grades each skill (quality 0-1) based on:
   - Use frequency vs creation date
   - Success rate (from trajectory log)
   - Token efficiency (avg tokens to complete tasks using this skill)
   - Token overlap with other skills (potential dup)
3. Consolidate: merge highly-overlapping (>80% similar) skills
4. Archive: skills unused 60 days + low quality (<0.3) → archive
5. Prune: archived 90 days + still unused → delete
6. Report: write logs/curator/<timestamp>/run.json + REPORT.md
7. Notify user: optional Telegram/email summary
```

**Skill taps (multiple sources):**

- `~/.argo/skills/` — local user skills (highest priority)
- `argo-skills/` — bundled with ARGO repo (lowest priority, but always present)
- `huggingface.co/skills/<repo>` — community trusted tap
- `skills.argo-agent.io` — official hub (auto-trusted)
- Custom git repos via `argo skills tap add <repo>` (community-trusted)
- Plugin-provided (SkillProvider)

### 4.8 LLM provider abstraction (200+ models)

**Architecture:**

```
Agent → ProviderRegistry → Provider → Transport → HTTP
                              ↑           ↑
                              │           └─ Anthropic | ChatCompletions | ResponsesApi | Bedrock | Gemini | Ollama
                              │
                              └─ OAuth flow (if subscription)
```

**Provider registry (KNOWN_MODELS catalog) — 30+ first-class providers:**

Hermes parity:
- Anthropic, OpenAI (incl. Codex backend), Gemini, xAI Grok (SuperGrok OAuth + grok-4.3 1M context), DeepSeek, Mistral, Cohere, Together, Groq, OpenRouter (200+ via aggregator), Ollama, vLLM, LM Studio, NVIDIA NIM, NovitaAI, AWS Bedrock, Azure AI Foundry, GMI Cloud, MiniMax, Tencent Tokenhub, HuggingFace, Nous Portal, Xiaomi MiMo, z.ai/GLM, Kimi/Moonshot

ARGO additions:
- **Yandex GPT** (Russia data residency)
- **SberCloud GigaChat** (Russia)
- **Yandex Foundation Models**
- **GLM Air** (China)
- **Tencent Hunyuan**
- **Baidu ERNIE**
- **Local Triton Inference Server**

**OAuth flows for subscription accounts:**

- Claude Pro (web SSO → bearer cookie)
- ChatGPT Pro (Codex CLI proxy)
- SuperGrok (xAI OAuth 2.0)
- Moonshot Pro
- Kimi+

**Fallback chain:**

```yaml
# ~/.argo/config.yaml
models:
  default:
    primary: claude-sonnet-4-6
    fallback:
      - gpt-4o
      - gemini/gemini-2.5-pro
      - ollama/qwen3:14b   # always-available local
  fast:
    primary: claude-haiku-4-5
    fallback: [gpt-4o-mini, ollama/llama3.3]
  reasoning:
    primary: claude-opus-4-7  # current latest
    fallback: [o3, deepseek-reasoner]
```

**Pluggable transports:**

```python
class ProviderTransport(ABC):
    async def convert_messages(self, msgs: list[dict]) -> Any: ...
    async def convert_tools(self, tools: list[dict]) -> Any: ...
    async def assemble_kwargs(self, **kw) -> dict: ...
    async def normalize_response(self, raw) -> Response: ...
    async def stream(self, **kw) -> AsyncIterator[Chunk]: ...
```

Concrete: `AnthropicTransport`, `ChatCompletionsTransport`, `ResponsesApiTransport`, `BedrockTransport`, `GeminiTransport`, `OllamaTransport`.

### 4.9 OpenAI-compatible API + Streaming

**Endpoints:**

- `POST /v1/chat/completions` — OpenAI Chat Completions parity, streaming with SSE
- `POST /v1/responses` — OpenAI Responses API parity (state machine model)
- `POST /v1/embeddings` — embeddings (route to provider)
- `GET /v1/models` — list available models with metadata
- `POST /v1/files` — upload files for vision/document use
- `GET /v1/files/:id` — retrieve uploaded file
- `POST /v1/assistants` — Assistants API parity (optional)
- `POST /v1/threads` — Threads API parity (optional)

**Headers (consistent across all endpoints):**

- `Idempotency-Key: <uuid>` — request deduplication for 24h
- `X-ARGO-Session-Id: <id>` — persistent context across requests
- `X-ARGO-Session-Key: <hmac>` — memory provider keying
- `X-Request-Id: <id>` — trace correlation
- `Authorization: Bearer <token>` — JWT or API key

**Streaming protocol (SSE):**

```
data: {"id":"chatcmpl-abc","object":"chat.completion.chunk","model":"argo","choices":[{"index":0,"delta":{"content":"Hi"}}]}

data: {"id":"chatcmpl-abc","choices":[{"delta":{"content":" there"}}]}

data: {"id":"chatcmpl-abc","choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"kubectl","arguments":"{\"action\":\"get pods\"}"}}]}}]}

data: [DONE]
```

**Tool progress streaming (ARGO extension):**

```
event: tool_start
data: {"tool":"kubectl","args":{"action":"get pods"},"id":"call_xyz"}

event: tool_progress
data: {"tool":"kubectl","progress":"Connecting to cluster..."}

event: tool_end
data: {"tool":"kubectl","result_preview":"3 pods running","duration_ms":250}
```

### 4.10 MCP server + client + gateway

**As server (ARGO exposes its tools):**

- JSON-RPC 2.0 over stdio (newline-delimited, NOT Content-Length — fixed from v2.0)
- HTTP POST `/mcp`
- HTTP SSE `/mcp/sse` with OAuth forwarding
- Stale-pipe retries (Hermes v0.13 parity)
- Image results as `MEDIA` tags
- Keepalive on long-lived ops

**As client (ARGO consumes external MCP tools):**

```yaml
# ~/.argo/config.yaml
mcp:
  servers:
    - name: filesystem
      command: npx
      args: ["@modelcontextprotocol/server-filesystem", "/home/user/projects"]
    - name: github
      url: https://api.github.com/mcp
      auth:
        type: oauth
        flow: github
    - name: my-custom
      command: python
      args: ["-m", "my_mcp_server"]
      cwd: /opt/argo-plugins
```

Dynamic tools loaded into registry as `mcp_<server>_<tool>`.

**As gateway (proxy + aggregator):**

ARGO can expose its own MCP endpoint AND forward to upstream MCPs, providing unified namespace, caching, rate-limiting, and audit.

### 4.11 Multi-agent

**Kanban (durable, with full lifecycle):**

```
       ┌────────┐    claim     ┌─────────┐  heartbeat   ┌──────────────┐
       │  todo  │─────────────▶│ claimed │─────────────▶│ in_progress  │
       └────────┘              └─────────┘              └──────┬───────┘
                                    │                          │
                                    │ no heartbeat            │
                                    │ (zombie)                │ block (need human)
                                    ▼                          ▼
                              ┌──────────┐              ┌──────────┐
                              │ reclaim  │              │ blocked  │
                              └──────────┘              └──────────┘
                                    │                          │
                                    │ retry < max              │ resume
                                    ▼                          ▼
                              ┌──────────┐              ┌────────────┐
                              │   todo   │              │in_progress │
                              └──────────┘              └─────┬──────┘
                                                              │
                                                              │ complete
                                                              ▼
                                                       ┌───────────┐
                                                       │   done    │
                                                       └───────────┘

  Failure path: hallucination gate (LLM-judge verifies output) → if low score, failed → retry.
```

**delegate_task (isolated subagent):**

```python
result = await tools.delegate_task(
    prompts=[
        "Search the codebase for security issues",
        "Run security scan with semgrep",
        "Cross-reference findings with CVE database",
    ],
    toolsets=["file","terminal","web"],   # restricted toolset
    isolated_terminal=True,                # own /tmp + cwd
    timeout_s=600,
    return_format="structured",
)
```

Each subagent gets:
- Own conversation context (parent only sees summary)
- Own terminal session (sandboxed)
- Own toolset subset
- Token budget
- Wallclock timeout
- Final summary returned (no intermediate context pollution)

**mixture_of_agents (MoA):**

Same query routed to N models in parallel, then aggregator model synthesizes:

```python
result = await tools.mixture_of_agents(
    query="Refactor this function for readability",
    models=["claude-opus-4-7","gpt-5.5","deepseek-reasoner"],
    aggregator="claude-sonnet-4-6",
    file_context="auth/login.py",
)
```

**DAG workflow (ARGO addition):**

```yaml
# Stored as kanban_boards.workflow_type='dag'
workflow:
  name: ci-pipeline
  tasks:
    - id: lint
      prompt: "Run linters on the codebase"
    - id: test
      prompt: "Run all tests"
      depends_on: [lint]
    - id: build
      prompt: "Build production artifacts"
      depends_on: [test]
    - id: deploy_staging
      prompt: "Deploy to staging"
      depends_on: [build]
    - id: smoke_test
      prompt: "Run smoke tests against staging"
      depends_on: [deploy_staging]
    - id: deploy_prod
      prompt: "Deploy to production"
      depends_on: [smoke_test]
      requires_human_approval: true
```

### 4.12 Voice + Multimedia

**Voice mode (CLI):**

- Push-to-talk: F12 hotkey starts recording, releases on F12 again
- Wake word: optional "Ay ARGO" (RU: "Эй АРГО", UZ: "Hey ARGO") — Picovoice porcupine
- TTS playback via `voice_speak` tool, default: ElevenLabs, optional: xAI Custom Voices (cloning), OpenAI TTS, Coqui (local)

**Discord voice channel live:**

ARGO joins a Discord voice channel and:
1. Listens (Discord opus → Whisper STT)
2. Detects user voice (VAD — Silero)
3. Responds via TTS streamed back to channel

**Voice cloning support (Hermes v0.13+ parity):**

```python
# Upload sample (5-30s of clear speech)
voice_id = await tools.voice_clone(
    sample_path="my_voice.wav",
    name="argo_user_v1",
)

# Use cloned voice
await tools.text_to_speech(
    text="Salom, men ARGO'man.",
    voice=voice_id,
    backend="xai",
)
```

**Image paste from clipboard (Hermes parity):**

In CLI: Cmd+V / Ctrl+V pastes image into conversation. Image saved to `~/.argo/uploads/`, referenced in next message.

**Image generation (FAL default, multi-backend):**

```python
result = await tools.image_generate(
    prompt="Modern AI agent dashboard, dark theme, blue accents",
    backend="fal_flux_klein",   # default; alternatives: dalle, sd, midjourney_compat
    size="1024x1024",
    n=1,
)
# Returns URL
```

**Video generation (Hermes v0.14+ parity):**

```python
result = await tools.video_generate(
    prompt="A cat playing with a ball",
    backend="xai_grok_imagine",  # default
    duration_s=5,
    aspect_ratio="16:9",
    # Optional: image_url for image-to-video
)
```

### 4.13 Cron + Scheduling

**APScheduler-based, but with:**

- Natural language parser: `"every weekday at 9am"` → `CronTrigger(day_of_week='mon-fri', hour=9)`
- Skill attachment: jobs can require specific skills to load
- Delivery routing: result auto-sent to any channel
- `no_agent` mode: pure script execution (no LLM call)
- Pause/resume/edit/test

**Example:**

```bash
argo cron add \
  --name "daily-pr-summary" \
  --schedule "every weekday at 18:00" \
  --prompt "Summarize all PRs opened today across our repos. Include reviewer status." \
  --skills github,pr-summary \
  --deliver telegram:@dev_team
```

**`no_agent` mode (script-only watchdog):**

```bash
argo cron add \
  --name "disk-check" \
  --schedule "*/15 * * * *" \
  --no-agent \
  --script "df -h | awk '\$5 > 85 {print}'" \
  --deliver slack:alerts \
  --quiet-on-empty  # only deliver if non-empty stdout
```

### 4.14 Security & Sandbox

**Threat model:**

| Threat | Mitigation |
|---|---|
| Malicious user prompt → unintended tool call | Plugin pre_tool veto, dangerous-tool confirmation, audit log |
| Prompt injection via skill content | Cron `prompt-injection scanner` runs on every assembled skill |
| Tool result exfiltration of secrets | Output redaction (regex + token-based), patch-aware mode |
| Cross-tenant data leakage | Strict user_id scoping in all queries, no SELECT * without filter |
| Resource exhaustion (DoS) | Per-user quotas, rate limits, max iterations cap |
| Browser SSRF | Cloud-metadata IP block list, private IP block list |
| Discord guild cross-leak | Guild-scoped role allowlists (CVSS 8.1 fix from Hermes v0.13) |
| WhatsApp/Telegram stranger attacks | Default-reject for users not in allowlist |
| TOCTOU on auth.json | Atomic write + fsync + verify |
| MCP OAuth token theft | Encrypted at rest, in-memory only during use |
| Supply chain (dep) | `argo-supply-chain-check` runs on every install |
| Container escape | seccomp-bpf + user namespaces + read-only rootfs |

**Sandbox modes:**

| Mode | Description |
|---|---|
| `strict` | All tools require confirmation, no shell_exec, restricted toolsets |
| `dev` | Default — shell allowed, file write allowed, network allowed |
| `paranoid` | Like strict + outbound network audit + no clipboard |
| `airgapped` | No external network at all; local LLMs only |

**Compliance modules:**

- `compliance/uz_152.py` — Uzbekistan Personal Data Law (data residency in UZ, audit retention 5 years, redaction of citizen ID)
- `compliance/ru_152.py` — Russia 152-FZ (data residency in RU, audit logs, redaction of OGRN/INN)
- `compliance/gdpr.py` — GDPR (right to erasure, data portability, consent management)
- `compliance/cn_pipl.py` — China PIPL (data residency in CN, sensitive data flags)

Enabled via:
```yaml
compliance:
  modes: [uz_152]
  data_residency: uz
  audit_retention_days: 1825  # 5 years
```

### 4.15 Terminal backends (12+)

| Backend | Use case |
|---|---|
| `local` | development, local agent |
| `docker` | isolated, ephemeral; default for kanban subagents |
| `podman` | rootless Docker alternative |
| `ssh` | remote server, persistent |
| `k8s_pod` | spawn ephemeral pod, run command, return (kubectl exec) |
| `singularity` | HPC environments |
| `modal` | serverless GPU, cost-efficient |
| `daytona` | managed dev environments |
| `vercel_sandbox` | Vercel ephemeral |
| `lima` | macOS native VM |
| `firecracker` | microVMs, fastest isolation |
| `e2b` | E2B sandbox cloud |

**Switching:**

```bash
argo config set terminal.backend k8s_pod
argo config set terminal.k8s_namespace argo-tools
argo config set terminal.k8s_image python:3.12-slim
```

**Per-task backend override:**

```python
result = await tools.shell_exec(
    command="apt update && apt install -y nmap && nmap -sV 10.0.0.0/24",
    backend="docker",
    docker_image="kalilinux/kali-rolling",
    timeout=300,
)
```

---

## 5. Data models (brief schemas — full schema in Appendix B)

(The full SQL schema is given in section 4.3 above.)

**Migration policy:** Alembic-style versioned migrations, forward-only by default, with downgrade scripts. Each migration tagged with a feature flag.

**Backup:** automatic SQLite backup every 6 hours to `~/.argo/backups/` (rolling 7-day retention). Optional S3 sync.

**Multi-tenancy:** all queries filter by `user_id`. For shared / org-wide skills, special user_id `__global__`. For multi-tenant deployment, optional `tenant_id` column added via migration.

---

## 6. API specification (key points)

(Detailed in sections 4.1 and 4.9.)

The OpenAPI 3.1 specification is generated automatically: `argo openapi > spec.yaml`. Site: `argo-agent.io/api`.

---

## 7. Deployment

### 7.1 Docker Compose (single-node default)

`docker-compose.yml`:

```yaml
services:
  argo-core:
    image: ghcr.io/argo-agent/core:3.0.0
    restart: unless-stopped
    env_file: .env
    ports:
      - "${ARGO_PORT:-8000}:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - argo-ipc:/ipc
    networks: [argo]
    healthcheck:
      test: ["CMD","curl","-sf","http://localhost:8000/api/health"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 10s
    depends_on:
      vault: {condition: service_healthy}

  argo-brain:
    image: ghcr.io/argo-agent/brain:3.0.0
    restart: unless-stopped
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./skills:/app/skills
      - ./plugins:/app/plugins
      - argo-ipc:/ipc
    networks: [argo]
    depends_on: [argo-core]

  vault:
    image: hashicorp/vault:1.17
    restart: unless-stopped
    cap_add: [IPC_LOCK]
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: "${VAULT_TOKEN:-dev-token-change-me}"
    ports: ["8200:8200"]
    volumes: [vault-data:/vault/data]
    networks: [argo]
    healthcheck:
      test: ["CMD","vault","status","-address=http://localhost:8200"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 5s

  qdrant:
    image: qdrant/qdrant:v1.11
    restart: unless-stopped
    volumes: [qdrant-data:/qdrant/storage]
    ports: ["6333:6333"]
    networks: [argo]

  prometheus:
    image: prom/prometheus:latest
    profiles: [observability]
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports: ["9090:9090"]
    networks: [argo]

  grafana:
    image: grafana/grafana:latest
    profiles: [observability]
    environment:
      GF_SECURITY_ADMIN_PASSWORD: "${GRAFANA_PASSWORD:-argo}"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/dashboards:/etc/grafana/provisioning/dashboards
    ports: ["3000:3000"]
    networks: [argo]

volumes:
  vault-data:
  qdrant-data:
  grafana-data:
  argo-ipc:

networks:
  argo:
    driver: bridge
```

### 7.2 Kubernetes (Helm chart)

```
helm/argo-agent/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── core-deployment.yaml      # Rust gateway, 3 replicas, HPA on CPU+RPS
│   ├── core-service.yaml         # ClusterIP + LoadBalancer
│   ├── brain-deployment.yaml     # Python brain, 3 replicas, HPA on iteration rate
│   ├── brain-service.yaml
│   ├── statefulset-vault.yaml    # HA Vault
│   ├── statefulset-qdrant.yaml   # HA Qdrant
│   ├── statefulset-postgres.yaml # Memory L2 (instead of SQLite)
│   ├── secrets.yaml              # ESO integration
│   ├── ingress.yaml
│   ├── networkpolicy.yaml
│   ├── poddisruptionbudget.yaml
│   ├── servicemonitor.yaml       # Prometheus Operator
│   └── certificate.yaml          # cert-manager
└── README.md
```

Install:
```bash
helm install argo argo-agent/argo-agent \
  --set image.tag=3.0.0 \
  --set persistence.size=20Gi \
  --set ingress.host=argo.example.com \
  --set llm.anthropic.apiKey="${ANTHROPIC_KEY}"
```

### 7.3 Cloud one-click templates

- AWS CloudFormation
- GCP Deployment Manager  
- Yandex.Cloud Resource Manager
- Tencent Cloud Lighthouse (Hermes parity)
- DigitalOcean App Platform
- Hetzner Cloud (via terraform)

### 7.4 Native binaries (no Docker)

Single binary distribution:
```bash
curl -fsSL https://argo-agent.io/install.sh | bash
# Detects OS, downloads native binary, sets up systemd service (Linux) / launchd (macOS) / Windows Service
```

Binary contents:
- `argo-core` (~5 MB Rust stripped)
- `argo` CLI (~5 MB Rust)
- `argo-brain` (Python embedded — uses PyOxidizer to bundle ~30 MB)

---

## 8. Observability

**Metrics (Prometheus):**

```
# HELP argo_chat_requests_total Total chat requests
# TYPE argo_chat_requests_total counter
argo_chat_requests_total{user_id="u123",channel="telegram",status="ok"} 142

# HELP argo_chat_duration_seconds Chat duration histogram
# TYPE argo_chat_duration_seconds histogram
argo_chat_duration_seconds_bucket{le="0.5"} 89
argo_chat_duration_seconds_bucket{le="1"} 132

# HELP argo_tool_calls_total Tool call counter
# TYPE argo_tool_calls_total counter
argo_tool_calls_total{tool="kubectl",status="success"} 64

# HELP argo_llm_tokens_total Tokens consumed
# TYPE argo_llm_tokens_total counter
argo_llm_tokens_total{provider="anthropic",model="claude-sonnet-4-6",direction="input"} 1245678

# HELP argo_memory_size_bytes Memory subsystem size
# TYPE argo_memory_size_bytes gauge
argo_memory_size_bytes{layer="L1",type="messages"} 524288000

# HELP argo_active_sessions Sessions currently active
# TYPE argo_active_sessions gauge
argo_active_sessions{channel="telegram"} 12
```

**Traces (OpenTelemetry):**

Every request gets a trace with spans for:
- `gateway.request` (root)
- `ipc.brain_call`
- `brain.process`
  - `memory.history`
  - `memory.semantic_search`
  - `provider.llm_call`
  - `tool.kubectl` (etc.)
  - `plugin.pre_tool_hook`
  - `memory.write`

Default exporter: OTLP/gRPC to local collector. Optional: Jaeger, Tempo, DataDog, New Relic.

**Logs (structured JSON):**

```json
{
  "ts": "2026-05-20T14:32:15.123Z",
  "level": "info",
  "logger": "argo_brain.core.agent",
  "user_id": "u123",
  "session_id": "s456",
  "request_id": "r789",
  "event": "tool_call",
  "tool": "kubectl",
  "args_redacted": {"action":"get pods","namespace":"<REDACTED>"},
  "duration_ms": 245,
  "result_status": "success"
}
```

**Grafana dashboards (bundled):**

1. **Overview** — RPS, error rate, P50/P99 latency, active sessions
2. **LLM Usage** — tokens per model, cost estimate, failover events
3. **Tools** — top tools, success rate, duration distribution
4. **Memory** — DB size, FTS5 query time, vector search latency
5. **Channels** — per-platform message rate, queue depth
6. **Security** — audit events, blocked tool calls, redaction rate

---

## 9. Performance targets (further detail)

(Given at a high level in section 0; here, broken down by component.)

**Core gateway:**

| Operation | P50 | P99 | Special condition |
|---|---|---|---|
| /api/health | 0.1 ms | 1 ms | response only |
| /api/chat (excl. brain) | 5 ms | 20 ms | with sandbox |
| WebSocket message echo | 0.3 ms | 2 ms | single message |
| OpenAI /v1/chat/completions overhead | 10 ms | 30 ms | with streaming |
| MCP tools/list | 2 ms | 8 ms | with 50 tools |

**Brain agent loop (single iteration, no LLM):**

| Operation | P50 | P99 |
|---|---|---|
| Lang detect | 1 ms | 5 ms |
| Build context (L0+L1+L2 fusion) | 30 ms | 100 ms |
| Tool dispatch (parallel 8) | 5 ms | 20 ms (overhead only) |
| Memory write (L0+L1) | 2 ms | 10 ms |
| Plugin pre/post hooks | 0.5 ms | 5 ms |

**End-to-end (with Claude Sonnet, no tools):**

| Operation | P50 | P99 |
|---|---|---|
| Simple chat (200 token output) | 1.5 s | 4 s |
| With 1 tool call | 3 s | 8 s |
| With 5 parallel tool calls | 4 s | 10 s |
| Voice mode (push-to-talk) | 2.5 s (STT + LLM + TTS) | 6 s |

**Throughput (per node):**

| Workload | Target |
|---|---|
| Concurrent WS connections | ≥50,000 |
| RPS (gateway-only echo) | ≥10,000 |
| RPS (full chat with cache hit, no tools) | ≥1,000 |
| RPS (full chat with 1 tool call) | ≥200 |
| RPS (full chat with LLM call) | LLM-bound |

---

## 10. Security model (further detail)

(Given at a high level in section 4.14.)

**Auth:**

- API key (per-user, hashed at rest)
- JWT (HS256 default, RS256 optional)
- OAuth 2.0 (for IDE/web clients)
- mTLS (for service-to-service)

**RBAC:**

```yaml
roles:
  admin:
    permissions: ["*"]
  user:
    permissions: ["chat","memory:read","memory:write","skills:read","tools:safe"]
  read_only:
    permissions: ["chat","memory:read","skills:read"]
  service:
    permissions: ["api:webhook"]
```

Per-tool permissions:
```yaml
tools:
  kubectl:
    requires_role: [admin, devops]
    confirmation: true
  shell_exec:
    requires_role: [user]
    sandbox: docker
    confirmation: for_root_commands
```

**Secrets management:**

- Default: HashiCorp Vault
- Alternatives: 1Password Connect, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault
- Never store API keys in env vars by default — Vault references via `vault://secret/argo/anthropic#api_key`

**Audit log:**

Append-only, signed, exported to SIEM (Splunk, ELK, Sentinel) via Fluent Bit.

---

## 11. Quality (Testing + CI/CD)

**Test pyramid:**

| Level | Coverage target | Tooling |
|---|---|---|
| Unit | ≥85% | pytest, cargo test |
| Integration | ≥70% | pytest-asyncio, testcontainers |
| Contract | 100% endpoints | schemathesis (OpenAPI fuzz) |
| E2E | 20 critical paths | playwright (TUI), cypress (web) |
| Performance | weekly | k6, criterion.rs |
| Security | every PR | semgrep, bandit, cargo-audit, trivy |
| Chaos | weekly | LitmusChaos |

**CI pipeline (GitHub Actions / GitLab CI):**

```yaml
stages:
  - lint
  - test-unit
  - test-integration
  - test-e2e
  - build
  - security-scan
  - performance
  - publish

lint:
  - black --check
  - ruff
  - mypy --strict
  - cargo fmt --check
  - cargo clippy -- -D warnings
  - taplo lint (TOML)
  - yamllint
  - hadolint Dockerfile.*

test-unit:
  parallel: 4
  - pytest tests/unit/ --cov=argo_brain --cov-fail-under=85
  - cargo test --workspace

test-integration:
  - pytest tests/integration/ -m "not slow"
  - docker compose up -d
  - pytest tests/e2e/ --base-url http://localhost:8000

security-scan:
  - bandit -r argo_brain
  - safety check
  - cargo audit
  - trivy image ghcr.io/argo-agent/core:${TAG}
  - semgrep --config=auto

performance:
  - k6 run perf/chat_load.js
  - cargo bench (criterion)
  - Compare to baseline; fail if >10% regression

publish:
  - cargo publish (crates.io)
  - twine upload (pypi)
  - docker buildx push (ghcr.io)
  - helm package + push (OCI registry)
```

**Required pre-merge checks:**
- All tests green
- Coverage maintained
- No new security findings (P1+)
- Performance within 10% of baseline
- Two reviewer approvals
- Signed-off-by trailer

---

## 12. Documentation requirements

**Documentation site:** `argo-agent.io/docs` (Docusaurus 3)

Structure:
```
docs/
├── intro.md
├── installation/
│   ├── linux.md
│   ├── macos.md
│   ├── windows.md
│   ├── docker.md
│   ├── kubernetes.md
│   └── termux.md
├── quickstart.md
├── configuration.md
├── concepts/
│   ├── architecture.md
│   ├── memory.md
│   ├── skills.md
│   ├── tools.md
│   ├── channels.md
│   ├── plugins.md
│   └── multi-agent.md
├── guides/
│   ├── first-conversation.md
│   ├── connect-telegram.md
│   ├── deploy-k8s.md
│   ├── migrate-from-hermes.md
│   ├── migrate-from-openclaw.md
│   ├── voice-mode.md
│   └── multi-agent-kanban.md
├── reference/
│   ├── cli.md            # all 30+ commands
│   ├── api.md            # auto-gen from OpenAPI
│   ├── config.md         # every config key documented
│   ├── tools.md          # all 120+ tools
│   ├── skills.md         # bundled skills catalog
│   ├── channels.md       # all 30+ channels
│   ├── providers.md      # all 30+ LLM providers
│   └── plugins.md        # plugin API
├── plugins/
│   └── (auto-listed plugins)
├── skills/
│   └── (auto-listed skills)
├── languages/
│   ├── uzbek.md
│   ├── russian.md
│   ├── kazakh.md
│   └── ...
└── faq.md
```

**Required for every feature:**
- Concept page (what + why)
- Reference page (API + config)
- Guide page (how-to with example)
- Code samples in `examples/` directory

**Translations:** Uzbek, Russian, Chinese (Simplified), Turkish, English (canonical).

---

## 13. Release roadmap

**Sprint structure:** 2-week sprints, 12 sprints (6 months) to v3.0 GA.

### Sprint 0 — Foundation Reset (2 weeks)
**Goal:** fix v2.0 bugs, foundation code ready.
**Deliverables:**
- All v2.0 blocking bugs fixed (config, KanbanManager, SessionCache, IPC, CronScheduler)
- Tests 100% green (29/29 → 200+/200+)
- CI pipeline working
- Public repo on GitHub (alpha)
- README honestly rewritten

### Sprint 1 — Rust Gateway v1 (2 weeks)
- argo-core all endpoints (HTTP, WS, OpenAI, MCP HTTP, webhooks)
- L0+L1 memory (Rust)
- Audit log
- Per-IP rate limit
- Prometheus metrics

### Sprint 2 — Python Brain v1 (2 weeks)
- Agent loop refactor (new prompt_builder)
- Memory manager (L0+L1+L2 unified)
- Tool registry consolidation (all_tools.py + registry.py → one)
- Plugin system (5 types)
- Honcho-style user_model

### Sprint 3 — Skills & Curator (2 weeks)
- agentskills.io standard
- Skill bundles (YAML)
- Curator pipeline (grading, consolidate, archive, prune)
- HuggingFace tap integration
- 50 bundled skills (newly written)

### Sprint 4 — Tools Suite I (2 weeks)
- Web/file/terminal/memory/delegation toolsets (40 tools)
- Multi-backend terminal (local, docker, ssh, k8s_pod)
- execute_code with tool access (Hermes parity)
- file_mutation_verifier
- LSP write-time diagnostics

### Sprint 5 — Tools Suite II — DevOps (2 weeks)
- Vault, K8s, Proxmox, SSH, Ansible, Terraform, Docker, ArgoCD tools
- Modal, Daytona, Vercel, Lima, Firecracker terminal backends
- Compliance modules (uz_152, ru_152, gdpr, cn_pipl)

### Sprint 6 — Channels I (2 weeks)
- Telegram, Discord, Slack, WhatsApp, Signal — with full integration tests
- Microsoft Teams end-to-end (Graph + webhook + delivery)
- Email IMAP/SMTP
- Voice mode (push-to-talk + Discord voice channel)

### Sprint 7 — Channels II (2 weeks)
- LINE, Viber, Matrix, Mattermost, Google Chat, IRC
- iMessage (BlueBubbles), WeChat, WeCom, Feishu, DingTalk, QQBot, Yuanbao, SimpleX
- Yandex.Messenger, VK, MyChat (CIS exclusives)

### Sprint 8 — Multi-agent & MCP (2 weeks)
- Kanban full lifecycle (heartbeat, reclaim, zombie, hallucination gate)
- delegate_task with isolation
- mixture_of_agents
- DAG workflow
- MCP server (stdio fix, SSE, OAuth forwarding)
- MCP client (load external tools)

### Sprint 9 — TUI & Web Dashboard (2 weeks)
- React/Ink TUI (Hermes parity)
- Web dashboard (Next.js): conversation history, skill manager, tool config, audit viewer
- ACP integration (VS Code, Zed)
- Personality system (SOUL.md, /personality)
- Theme/skin customization

### Sprint 10 — Polish, Performance, Security (2 weeks)
- Performance tuning to hit all 11 metric targets
- External security audit
- Penetration test
- 8+ P0/P1 security closures
- Native Windows beta
- Termux support
- Cold start optimization

### Sprint 11 — Hub & Marketplace (2 weeks)
- argo-agent.io/hub (skills marketplace)
- argo-agent.io/plugins (plugin marketplace)
- Signed packages
- 100+ pre-published skills
- 20+ pre-published plugins

### Sprint 12 — GA Launch (2 weeks)
- Marketing site
- Documentation 100% complete
- Tutorial videos (10+ in UZ/RU/EN)
- PyPI + crates.io + Homebrew + apt repo
- One-click cloud templates (Yandex, Tencent, AWS, GCP, DigitalOcean)
- Launch on Product Hunt, Hacker News, r/LocalLLaMA
- Anthropic / NousResearch outreach for cross-promotion

---

## 14. Risk register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Hermes feature lead grows faster than we can catch up | High | High | Niche-first strategy (CA + DevOps), not feature-match-all |
| R2 | Rust core development slower than estimate | Medium | High | Start with proven libs (Axum, Tokio, DashMap), no novel research |
| R3 | LLM provider API changes break adapters | High | Medium | Contract tests + LiteLLM upstream |
| R4 | Hermes upstream changes their MCP/skill format | Medium | Medium | Pin to agentskills.io standard, version compatibility shim |
| R5 | Single dev burnout | High | Critical | Open-source from day 1, attract contributors early |
| R6 | Sovereign deployment legal complexity (UZ/RU/CN) | Medium | High | Compliance modules separated; users opt in |
| R7 | Tokenizer drift for Central Asian languages | Medium | Medium | Bundle SentencePiece models per language pack |
| R8 | Sandbox bypass discovered | Medium | Critical | External audit + bug bounty |
| R9 | OAuth flow changes for subscription providers | High | Medium | Maintained transport layer, fallback to API key |
| R10 | Performance targets unrealistic in practice | Medium | Medium | Continuous benchmark gates on PRs, alert on regression |

---

## 15. Open questions

1. **L3 KG (knowledge graph) — opt-in or default?** Currently marked as opt-in, but experimentation is needed.
2. **Rust brain port — when?** Planned for v3.5+, but keeping the Python brain may be sufficient.
3. **Cloud hosted service?** Should we offer an "ARGO Cloud" SaaS? It is a monetization path, but it conflicts with the "self-hosted first" philosophy.
4. **Telemetry — when, if ever, can it be enabled?** Never default ON, but collecting minimal anonymous metrics on an opt-in basis (`argo telemetry enable`) may be useful.
5. **Premium tier** — voice cloning, advanced video gen, premium models — will all of these remain in user configuration, or will there be a premium tier?
6. **Hermes interop** — ARGO imports Hermes skills, but should it also export skills to Hermes (the reverse direction)?
7. **Mobile-native app** — marked as a non-goal, but many users in the Central Asian market are mobile-first. Should this be reconsidered?

---

## Appendix A — Hermes ↔ ARGO full feature matrix

(Abridged in section 2 above; here, the full version with 155+ rows. A separate page in the document.)

| Category | Feature | Hermes v0.14 | ARGO v3.0 |
|---|---|---|---|
| **Memory** | 3-layer architecture | ✅ | ✅ |
| | 4-layer (with KG) | ❌ | ✅ |
| | FTS5 search | ✅ | ✅ |
| | Vector semantic | ✅ Chroma | ✅ Chroma/Qdrant |
| | Cross-session prompt cache | ✅ 1 hour | ✅ 1 hour |
| | MEMORY.md / USER.md | ✅ | ✅ |
| | Honcho dialectic | ✅ plugin | ✅ built-in |
| | Auto-compression | ✅ | ✅ (real, not no-op) |
| | session_search tool | ✅ | ✅ |
| | LLM summarization for recall | ✅ | ✅ |
| **Personality** | SOUL.md | ✅ | ✅ |
| | /personality presets | ✅ | ✅ |
| | Custom themes/skins | ✅ | ✅ |
| **Context** | .hermes.md / .argo.md | ✅ | ✅ |
| | AGENTS.md auto-discovery | ✅ | ✅ |
| | @ context references | ✅ | ✅ |
| | Project context loading | ✅ | ✅ |

(...and 130+ more rows like this. The full table is provided as Excel/Markdown in the ARGO_Hermes_Parity.xlsx file.)

---

## Appendix B — Brief summary of the analysis results

Results of the ARGO v2.0 (existing code) analysis:

**Broken components (must be fixed in Sprint 0):**
1. `config.py:171` — orphan fields outside class body (syntax error)
2. `core/agent.py:110` — `KanbanManager()` missing `runner` argument
3. `cache/session.py:46` — `asyncio.create_task` in `__init__`
4. `ipc_server.py:93` — `agent._sub_runner` doesn't exist
5. `main.py:79` — `CronScheduler(agent)` wrong signature
6. `docker-compose.yml:29` — invalid YAML (semicolons)
7. `scripts/install.sh:14` — references non-existent PyPI package
8. `tools/registry.py` vs `tools/all_tools.py` — duplicate registries
9. `SkillLoader.list_skills()` — method doesn't exist (`list_all` does)
10. `MemoryManager.add_ktask` — doesn't exist (test references it)

**Partial implementations (to be completed during Sprints 1-9):**
- Compression (importance < 0.7 — no-op as default importance is 1.0)
- Security sandbox (linux_limits stub)
- Shell BLOCKED (trivial whitespace bypass)
- Tokenizer (text.len/4 — wrong for Cyrillic/Arabic)
- LINE channel HMAC (graceful fallback skips verification)
- skills_400.py (26 of the claimed 400+)
- MCP stdio (Content-Length headers — wrong for spec)

**Working foundations (kept as the base):**
- Rust gateway/IPC/memory.rs — kept at quality level
- Agent loop architecture — good
- Channel skeletons — to be extended
- Plugin API — to be extended (5 types)
- Doctor — to be extended

---

## Appendix C — Migration plan from v2.0

For users running ARGO v2.0 alpha:

```bash
# 1. Backup data
argo backup create ~/argo-v2-backup.tar.gz

# 2. Stop services
docker compose down

# 3. Upgrade
git pull
git checkout v3.0.0
docker compose pull

# 4. Apply migrations
argo migrate up

# 5. Restart
docker compose up -d

# 6. Verify
argo doctor
```

**Breaking changes from v2.0:**
- `tools/registry.py` and `tools/all_tools.py` merged into `tools/registry.py`
- `argo-hub/` directory removed (empty in v2.0)
- `KanbanManager()` now requires `runner` argument
- `SessionCache.__init__` no longer auto-starts eviction loop; call `start()` manually
- Config field `parallel_tools` is `bool`; new `max_parallel_tools: int = 8` for concurrency limit
- `MCP` stdio transport: now newline-delimited JSON, not Content-Length

---

## End of document

**Approval:** This TZ is submitted and serves as the official document for getting started. Changes are made via PR + 2 reviewer approvals.

**Next step:** Start Sprint 0. The first contractual deliverable: all v2.0 bugs fixed + tests 100% green.

**Contact:** GitHub Issues, Discord #argo-dev channel.

---

*Document version: 1.0*
*Created: May 2026*
*License: MIT (together with the ARGO project)*
