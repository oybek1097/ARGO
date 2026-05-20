# Ilova A — Hermes v0.14.0 ↔ ARGO v3.0 to'liq feature parity matritsasi

**Hujjat versiyasi:** 1.0 · **Sana:** May 2026
**Manbalar:** Hermes Agent rasmiy hujjatlari (hermes-agent.nousresearch.com), GitHub repository, v0.14.0 release notes, ARGO v2.0 kod tahlili.

**Belgilashlar:**
- ✅ — bor va to'liq ishlaydi
- 🟡 — qisman / kichik versiyada / qo'shimcha ishlash kerak
- ❌ — yo'q
- 🆕 — ARGO exclusive (Hermes'da yo'q)

---

## 1. Asosiy arxitektura va platforma

| # | Funksiya | Hermes v0.14 | ARGO v3.0 target | Eslatma |
|---|---|---|---|---|
| 1.1 | Self-improving learning loop | ✅ | ✅ | reflection + curator |
| 1.2 | Persistent cross-session memory | ✅ | ✅ | |
| 1.3 | Background daemon mode | ✅ | ✅ | systemd / docker |
| 1.4 | Local-first (no cloud required) | ✅ | ✅ | |
| 1.5 | MIT license | ✅ | ✅ | |
| 1.6 | Rust component | ❌ | ✅ | 🆕 gateway + IPC |
| 1.7 | Multi-runtime brain support | ❌ | 🟡 v3.5 | 🆕 Go/Rust ports planned |
| 1.8 | Unix socket IPC | ❌ | ✅ | 🆕 |
| 1.9 | Tencent Cloud one-click | ✅ | 🟡 | priority backlog |
| 1.10 | Yandex.Cloud one-click | ❌ | ✅ | 🆕 CIS region |
| 1.11 | DigitalOcean one-click | ❌ | ✅ | 🆕 |
| 1.12 | Native Windows beta | ✅ | ✅ | |
| 1.13 | Termux (Android) | ✅ | ✅ | |
| 1.14 | FreeBSD support | ❌ | ✅ | 🆕 |
| 1.15 | Compile-from-source easy | ✅ | ✅ | cargo/uv |
| 1.16 | Profiles (multi-instance) | ✅ | ✅ | `--profile dev/prod` |
| 1.17 | OpenClaw migration | ✅ | 🟡 v3.0+ | low priority |
| 1.18 | Hermes migration tool | ❌ | ✅ | `argo migrate hermes` |
| 1.19 | Hot-reload config | ❌ | ✅ | 🆕 |
| 1.20 | Cluster/multi-node mode | 🟡 | ✅ | 🆕 native HA |

## 2. Memory subsystem

| # | Funksiya | Hermes | ARGO | Eslatma |
|---|---|---|---|---|
| 2.1 | Working memory (in-process) | ✅ | ✅ | L0 |
| 2.2 | SQLite persistent | ✅ | ✅ | L1 with WAL |
| 2.3 | FTS5 full-text search | ✅ | ✅ | unicode61 + diacritics |
| 2.4 | Vector semantic search | ✅ ChromaDB | ✅ Chroma/Qdrant | L2 |
| 2.5 | Knowledge graph (KG) | ❌ | 🟡 opt-in | 🆕 L3 Neo4j/Memgraph |
| 2.6 | Cross-session prompt cache | ✅ 1hr | ✅ 1hr | |
| 2.7 | Real-time same-session visibility | ✅ | ✅ | L0+L1 ID dedup |
| 2.8 | MEMORY.md file | ✅ | ✅ | |
| 2.9 | USER.md file | ✅ | ✅ | |
| 2.10 | Honcho dialectic modeling | ✅ plugin | ✅ built-in | |
| 2.11 | Auto-compression | ✅ | ✅ | age + importance weighted |
| 2.12 | LLM-summary for old context | ✅ | ✅ | |
| 2.13 | session_search tool | ✅ | ✅ | |
| 2.14 | Multi-language tokenizer | 🟡 | ✅ | 🆕 SentencePiece per language |
| 2.15 | Postgres backend (multi-node) | ❌ | ✅ | 🆕 |
| 2.16 | Redis cache layer | ❌ | ✅ | 🆕 optional |
| 2.17 | Backup/restore tools | 🟡 | ✅ | `argo backup create/restore` |
| 2.18 | Memory provider plugin | ✅ | ✅ | |
| 2.19 | Per-user memory namespace | ✅ | ✅ | |
| 2.20 | Cross-tenant isolation | 🟡 | ✅ | 🆕 strict user_id filter |

## 3. Skills system

| # | Funksiya | Hermes | ARGO | Eslatma |
|---|---|---|---|---|
| 3.1 | agentskills.io standart | ✅ | ✅ | |
| 3.2 | Bundled skills count | 118+ (v0.10) + 9 (v0.14) | 150+ target | sprint 3 |
| 3.3 | Skills Hub (marketplace) | ✅ | ✅ | argo-agent.io/hub |
| 3.4 | HuggingFace tap | ✅ | ✅ | huggingface.co/skills |
| 3.5 | Custom taps | ✅ | ✅ | `argo skills tap add` |
| 3.6 | Skill bundles (YAML aliases) | ✅ | ✅ | |
| 3.7 | skill_manage tool | ✅ | ✅ | |
| 3.8 | skill_view tool | ✅ | ✅ | |
| 3.9 | skills_list tool | ✅ | ✅ | |
| 3.10 | Autonomous Curator (7-day cycle) | ✅ | ✅ | |
| 3.11 | Curator grading | ✅ | ✅ | LLM-judge |
| 3.12 | Curator consolidate | ✅ | ✅ | merge dups |
| 3.13 | Curator archive | ✅ | ✅ | |
| 3.14 | Curator prune | ✅ | ✅ | |
| 3.15 | Curator subcommands (archive/prune/list-archived) | ✅ | ✅ | |
| 3.16 | Curator sync run (manual) | ✅ | ✅ | |
| 3.17 | Pinned skills (curator-protected) | ✅ | ✅ | |
| 3.18 | Skill quality scoring | ✅ | ✅ | |
| 3.19 | Skill manifest hashing | ✅ | ✅ | drift detection |
| 3.20 | hermes skills reset | ✅ | ✅ | `argo skills reset` |
| 3.21 | Third-party warning panel | ✅ | ✅ | |
| 3.22 | Security scan on install | ✅ | ✅ | |
| 3.23 | Trust signals (community/trusted) | ✅ | ✅ | |
| 3.24 | Per-skill toolset requirements | ✅ | ✅ | |
| 3.25 | Skill provider plugin | ❌ | ✅ | 🆕 |

## 4. Tools

| # | Tool | Hermes (~70) | ARGO (~120) |
|---|---|---|---|
| 4.1 | web_search | ✅ | ✅ |
| 4.2 | x_search (Twitter) | ✅ (v0.14) | ✅ |
| 4.3 | web_fetch | ✅ | ✅ |
| 4.4 | http_get / http_post | ✅ | ✅ |
| 4.5 | shell_exec | ✅ | ✅ (multi-backend) |
| 4.6 | process (background) | ✅ | ✅ |
| 4.7 | read_file | ✅ | ✅ |
| 4.8 | write_file | ✅ | ✅ + LSP lint |
| 4.9 | patch_file | ✅ | ✅ |
| 4.10 | list_dir / find_files | ✅ | ✅ |
| 4.11 | grep_files | ✅ | ✅ |
| 4.12 | file_diff | ✅ | ✅ |
| 4.13 | file_mutation_verifier | ✅ | ✅ |
| 4.14 | memory_search | ✅ | ✅ |
| 4.15 | memory_remember | ✅ | ✅ |
| 4.16 | session_search | ✅ | ✅ |
| 4.17 | delegate_task | ✅ | ✅ |
| 4.18 | mixture_of_agents | ✅ | ✅ |
| 4.19 | dag_workflow | ❌ | ✅ 🆕 |
| 4.20 | kanban_create + 6 ta | ✅ | ✅ |
| 4.21 | cronjob | ✅ | ✅ |
| 4.22 | execute_code (with tool access) | ✅ | ✅ |
| 4.23 | execute_python | ✅ | ✅ |
| 4.24 | clarify | ✅ | ✅ |
| 4.25 | todo | ✅ | ✅ |
| 4.26 | send_message (cross-platform) | ✅ | ✅ |
| 4.27 | vision_analyze | ✅ | ✅ pixel-preserving |
| 4.28 | image_generate | ✅ FAL Flux | ✅ multi-backend |
| 4.29 | video_analyze | ✅ | ✅ |
| 4.30 | video_generate | ✅ Grok/Veo/Pixverse | ✅ multi-backend |
| 4.31 | text_to_speech | ✅ | ✅ |
| 4.32 | speech_to_text | ✅ | ✅ |
| 4.33 | voice_clone | ✅ xAI Custom Voices | ✅ |
| 4.34 | computer_use | ✅ macOS BG | ✅ cross-platform |
| 4.35 | computer_use_linux MCP | ✅ | ✅ |
| 4.36 | browser tools (10+) | ✅ | ✅ |
| 4.37 | browser CDP backend | ✅ | ✅ |
| 4.38 | Browserbase cloud | ✅ | ✅ |
| 4.39 | Browser Use cloud | ✅ | ✅ |
| 4.40 | home_assistant tools (4) | ✅ | ✅ |
| 4.41 | spotify (plugin, 7) | ✅ | ✅ |
| 4.42 | feishu tools (5) | ✅ | ✅ |
| 4.43 | yuanbao tools (5) | ✅ | ✅ |
| 4.44 | discord_admin tools (2) | ✅ | ✅ |
| 4.45 | RL tools (10) | ✅ | ✅ |
| 4.46 | git tools (8) | ✅ | ✅ |
| 4.47 | notion | 🟡 skill | ✅ tool |
| 4.48 | rss tools | 🟡 skill | ✅ tool |
| 4.49 | email_send/search | ✅ | ✅ |
| 4.50 | sql_query / sql_schema / sql_explain | ❌ | ✅ 🆕 |
| 4.51 | **kubectl** + 5 K8s | ❌ | ✅ 🆕 ARGO exclusive |
| 4.52 | **proxmox** (5) | ❌ | ✅ 🆕 ARGO exclusive |
| 4.53 | **vault** (4) | ❌ | ✅ 🆕 ARGO exclusive |
| 4.54 | **ssh** (3) | ❌ | ✅ 🆕 ARGO exclusive |
| 4.55 | **ansible** (2) | ❌ | ✅ 🆕 ARGO exclusive |
| 4.56 | **terraform** (3) | ❌ | ✅ 🆕 ARGO exclusive |
| 4.57 | **docker** (5) | 🟡 backend only | ✅ 🆕 tool |
| 4.58 | **argocd** (3) | ❌ | ✅ 🆕 ARGO exclusive |
| 4.59 | webhook send | ✅ | ✅ |
| 4.60 | env_get | ✅ | ✅ |
| 4.61 | MCP dynamic tools | ✅ | ✅ |

## 5. Terminal backends

| # | Backend | Hermes (7) | ARGO (12) |
|---|---|---|---|
| 5.1 | local | ✅ | ✅ |
| 5.2 | docker | ✅ | ✅ |
| 5.3 | ssh | ✅ | ✅ |
| 5.4 | singularity | ✅ | ✅ |
| 5.5 | modal | ✅ | ✅ |
| 5.6 | daytona | ✅ | ✅ |
| 5.7 | vercel_sandbox | ✅ | ✅ |
| 5.8 | k8s_pod | ❌ | ✅ 🆕 |
| 5.9 | podman | ❌ | ✅ 🆕 |
| 5.10 | lima (macOS VM) | ❌ | ✅ 🆕 |
| 5.11 | firecracker (microVM) | ❌ | ✅ 🆕 |
| 5.12 | e2b | ❌ | ✅ 🆕 |

## 6. Messaging platforms

| # | Platform | Hermes (22) | ARGO (30+) |
|---|---|---|---|
| 6.1 | Telegram | ✅ | ✅ |
| 6.2 | Discord | ✅ | ✅ |
| 6.3 | Discord voice channel | ✅ | ✅ |
| 6.4 | Slack | ✅ | ✅ |
| 6.5 | WhatsApp | ✅ | ✅ |
| 6.6 | Signal | ✅ | ✅ |
| 6.7 | Email (IMAP/SMTP) | ✅ | ✅ |
| 6.8 | Microsoft Teams (end-to-end) | ✅ (v0.14) | ✅ |
| 6.9 | Google Chat | ✅ (v0.13) | ✅ |
| 6.10 | Matrix | ✅ | ✅ |
| 6.11 | Mattermost | ✅ | ✅ |
| 6.12 | LINE | ✅ (v0.14) | ✅ |
| 6.13 | Viber | ❌ | ✅ 🆕 |
| 6.14 | WeChat | ✅ | ✅ |
| 6.15 | WeCom | ✅ | ✅ |
| 6.16 | Weixin | ✅ | ✅ |
| 6.17 | Feishu/Lark | ✅ | ✅ |
| 6.18 | DingTalk | ✅ | ✅ |
| 6.19 | QQBot | ✅ | ✅ |
| 6.20 | Yuanbao | ✅ | ✅ |
| 6.21 | iMessage (BlueBubbles) | ✅ | ✅ |
| 6.22 | SimpleX Chat | ✅ (v0.14) | ✅ |
| 6.23 | IRC | ✅ | ✅ |
| 6.24 | SMS (Twilio) | ✅ | ✅ |
| 6.25 | Home Assistant | ✅ | ✅ |
| 6.26 | Webhook generic | ✅ | ✅ |
| 6.27 | **Yandex.Messenger** | ❌ | ✅ 🆕 CIS |
| 6.28 | **VK Messages** | ❌ | ✅ 🆕 CIS |
| 6.29 | **MyChat (Astra)** | ❌ | ✅ 🆕 RU gov |
| 6.30 | **Mango Office** | ❌ | ✅ 🆕 RU business |
| 6.31 | **Wire** | ❌ | ✅ 🆕 privacy |
| 6.32 | **Threema** | ❌ | ✅ 🆕 privacy |
| 6.33 | **Briar (offline mesh)** | ❌ | ✅ 🆕 |

## 7. LLM providers

| # | Provider | Hermes | ARGO |
|---|---|---|---|
| 7.1 | Anthropic Claude | ✅ | ✅ |
| 7.2 | OpenAI GPT | ✅ | ✅ |
| 7.3 | Google Gemini | ✅ | ✅ |
| 7.4 | xAI Grok | ✅ SuperGrok OAuth (v0.14) | ✅ |
| 7.5 | DeepSeek | ✅ | ✅ |
| 7.6 | Mistral | ✅ | ✅ |
| 7.7 | Cohere | 🟡 | ✅ |
| 7.8 | Together AI | ✅ | ✅ |
| 7.9 | Groq | ✅ | ✅ |
| 7.10 | OpenRouter (200+ models) | ✅ | ✅ |
| 7.11 | Ollama | ✅ | ✅ |
| 7.12 | vLLM | ✅ | ✅ |
| 7.13 | LM Studio | ✅ (v0.12) | ✅ |
| 7.14 | NVIDIA NIM | ✅ | ✅ |
| 7.15 | NovitaAI | ✅ | ✅ |
| 7.16 | AWS Bedrock | ✅ | ✅ |
| 7.17 | Azure AI Foundry | ✅ (v0.12) | ✅ |
| 7.18 | GMI Cloud | ✅ (v0.12) | ✅ |
| 7.19 | MiniMax | ✅ (v0.12) | ✅ |
| 7.20 | Tencent Tokenhub | ✅ (v0.12) | ✅ |
| 7.21 | Tencent Hunyuan | ❌ | ✅ 🆕 |
| 7.22 | HuggingFace | ✅ | ✅ |
| 7.23 | Nous Portal | ✅ | ✅ |
| 7.24 | Xiaomi MiMo | ✅ | ✅ |
| 7.25 | z.ai / GLM | ✅ | ✅ |
| 7.26 | Kimi / Moonshot | ✅ | ✅ |
| 7.27 | **Yandex GPT** | ❌ | ✅ 🆕 RU |
| 7.28 | **SberCloud GigaChat** | ❌ | ✅ 🆕 RU |
| 7.29 | **Yandex Foundation Models** | ❌ | ✅ 🆕 RU |
| 7.30 | **GLM Air** | ❌ | ✅ 🆕 CN |
| 7.31 | **Baidu ERNIE** | ❌ | ✅ 🆕 CN |
| 7.32 | **Triton Inference Server** | ❌ | ✅ 🆕 local infra |
| 7.33 | Claude Pro OAuth | ✅ | ✅ |
| 7.34 | ChatGPT Pro OAuth (Codex) | ✅ (v0.14) | ✅ |
| 7.35 | SuperGrok OAuth | ✅ (v0.14) | ✅ |
| 7.36 | Fallback chain | ✅ | ✅ |
| 7.37 | Live model switching (/model) | ✅ | ✅ |
| 7.38 | hermes doctor per-provider check | ✅ | ✅ argo doctor |
| 7.39 | Pluggable transports | ✅ | ✅ |
| 7.40 | OpenRouter routing | ✅ | ✅ via LiteLLM |

## 8. Multi-agent & delegation

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 8.1 | Kanban boards (durable) | ✅ | ✅ |
| 8.2 | Heartbeat + reclaim | ✅ | ✅ |
| 8.3 | Zombie detection | ✅ | ✅ |
| 8.4 | Hallucination gate | ✅ | ✅ LLM-judge |
| 8.5 | Per-task retries (budget) | ✅ | ✅ |
| 8.6 | Auto-block on incomplete exit | ✅ | ✅ |
| 8.7 | /goal Ralph loop | ✅ | ✅ |
| 8.8 | delegate_task (isolated) | ✅ | ✅ |
| 8.9 | Subagent isolated terminal | ✅ | ✅ |
| 8.10 | Subagent toolset restriction | ✅ | ✅ |
| 8.11 | mixture_of_agents (MoA) | ✅ | ✅ |
| 8.12 | DAG workflow | ❌ | ✅ 🆕 |
| 8.13 | /handoff session transfer | ✅ | ✅ |
| 8.14 | /claim handoff ticket | ✅ | ✅ |
| 8.15 | /steer in-flight redirect | ✅ ACP | ✅ |
| 8.16 | /queue follow-ups | ✅ ACP | ✅ |
| 8.17 | KANBAN_GUIDANCE auto-injection | ✅ | ✅ |
| 8.18 | Orchestrator profile | ✅ | ✅ |
| 8.19 | Subagent spawn observability | ✅ TUI overlay | ✅ |

## 9. MCP integration

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 9.1 | MCP server (expose tools) | ✅ | ✅ |
| 9.2 | MCP client (consume external) | ✅ | ✅ |
| 9.3 | Stdio transport (newline JSON) | ✅ | ✅ (v3 fix) |
| 9.4 | HTTP transport | ✅ | ✅ |
| 9.5 | SSE transport | ✅ | ✅ |
| 9.6 | OAuth forwarding | ✅ | ✅ |
| 9.7 | Stale-pipe retries | ✅ | ✅ |
| 9.8 | Image results MEDIA tags | ✅ | ✅ |
| 9.9 | Keepalive on long ops | ✅ | ✅ |
| 9.10 | Dynamic tool registration | ✅ | ✅ |
| 9.11 | mcp-<server> toolset namespace | ✅ | ✅ |
| 9.12 | MCP gateway/proxy | ❌ | ✅ 🆕 |
| 9.13 | OAuth flow standard | ✅ | ✅ |

## 10. Plugin system

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 10.1 | General plugin type | ✅ | ✅ |
| 10.2 | Memory provider plugin | ✅ | ✅ |
| 10.3 | Context engine plugin | ✅ | ✅ |
| 10.4 | Channel adapter plugin | ❌ | ✅ 🆕 |
| 10.5 | Skill provider plugin | ❌ | ✅ 🆕 |
| 10.6 | pre_tool_call hook | ✅ | ✅ |
| 10.7 | transform_tool_result hook | ✅ | ✅ |
| 10.8 | transform_terminal_output | ✅ | ✅ |
| 10.9 | on_message hook | ✅ | ✅ |
| 10.10 | on_response hook | ✅ | ✅ |
| 10.11 | on_skill_saved hook | ✅ | ✅ |
| 10.12 | Slash command registration | ✅ | ✅ |
| 10.13 | Dashboard tab plugin | ✅ | ✅ |
| 10.14 | Gateway platform plugin | ✅ | ✅ |
| 10.15 | Provider backend plugin | ✅ | ✅ |
| 10.16 | Image-gen backend plugin | ✅ | ✅ |
| 10.17 | Video-gen backend plugin | ✅ | ✅ |
| 10.18 | ctx.llm in plugin | ✅ (v0.14) | ✅ |
| 10.19 | tool_override flag | ✅ (v0.14) | ✅ |
| 10.20 | Auto-discovery from ~/.argo/plugins/ | ✅ | ✅ |
| 10.21 | Plugin marketplace | 🟡 | ✅ 🆕 signed |
| 10.22 | Hot-reload (dev mode) | ❌ | ✅ 🆕 |
| 10.23 | Built-in: security_audit | ✅ | ✅ |
| 10.24 | Built-in: disk_cleanup | ✅ | ✅ |
| 10.25 | Built-in: language_enforcer | ✅ | ✅ |
| 10.26 | Built-in: pii_redactor | ❌ | ✅ 🆕 |
| 10.27 | Built-in: compliance_uz/ru/eu | ❌ | ✅ 🆕 |

## 11. Voice / Multimedia

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 11.1 | Voice mode CLI (push-to-talk) | ✅ | ✅ |
| 11.2 | Voice mode in messaging | ✅ | ✅ |
| 11.3 | Discord live voice channel | ✅ | ✅ |
| 11.4 | Voice memo transcription | ✅ | ✅ |
| 11.5 | Wake word | ❌ | ✅ 🆕 Picovoice |
| 11.6 | Voice cloning (xAI) | ✅ | ✅ |
| 11.7 | TTS: ElevenLabs | ✅ | ✅ |
| 11.8 | TTS: OpenAI | ✅ | ✅ |
| 11.9 | TTS: Coqui (local) | ✅ | ✅ |
| 11.10 | TTS: Yandex SpeechKit | ❌ | ✅ 🆕 |
| 11.11 | STT: Whisper | ✅ | ✅ |
| 11.12 | STT: Deepgram | ✅ | ✅ |
| 11.13 | Image paste from clipboard | ✅ | ✅ |
| 11.14 | Multimodal vision | ✅ | ✅ |
| 11.15 | Image gen: FAL | ✅ | ✅ |
| 11.16 | Image gen: DALL-E | ✅ | ✅ |
| 11.17 | Image gen: Stable Diffusion local | ✅ | ✅ |
| 11.18 | Video analyze | ✅ | ✅ |
| 11.19 | Video gen: Grok Imagine | ✅ | ✅ |
| 11.20 | Video gen: Veo 3.1 | ✅ | ✅ |
| 11.21 | Video gen: Pixverse | ✅ | ✅ |
| 11.22 | Video gen: Kling | ✅ | ✅ |

## 12. CLI / TUI / Web

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 12.1 | Interactive CLI | ✅ | ✅ |
| 12.2 | React/Ink TUI | ✅ (v0.11+) | ✅ |
| 12.3 | Multiline editing | ✅ | ✅ |
| 12.4 | Slash command autocomplete | ✅ | ✅ |
| 12.5 | Conversation history nav | ✅ | ✅ |
| 12.6 | Interrupt-and-redirect | ✅ | ✅ |
| 12.7 | OSC-52 clipboard | ✅ | ✅ |
| 12.8 | Sticky composer | ✅ | ✅ |
| 12.9 | /clear with confirm | ✅ | ✅ |
| 12.10 | Light/dark theme | ✅ | ✅ |
| 12.11 | Custom themes/skins | ✅ | ✅ |
| 12.12 | Subagent spawn observability | ✅ | ✅ |
| 12.13 | /model picker with auth | ✅ | ✅ |
| 12.14 | Context compression counter | ✅ | ✅ |
| 12.15 | Status bar (stopwatch + branch) | ✅ | ✅ |
| 12.16 | Personality presets (/personality) | ✅ | ✅ |
| 12.17 | Web dashboard | 🟡 | ✅ Next.js |
| 12.18 | Skills manager UI | 🟡 | ✅ |
| 12.19 | Conversation viewer | ✅ | ✅ |
| 12.20 | Audit log viewer | ❌ | ✅ 🆕 |
| 12.21 | Token usage dashboard | 🟡 | ✅ |

## 13. IDE / ACP integration

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 13.1 | VS Code integration | ✅ ACP | ✅ |
| 13.2 | Zed integration | ✅ ACP | ✅ |
| 13.3 | JetBrains integration | ✅ ACP | ✅ |
| 13.4 | Chat panel in IDE | ✅ | ✅ |
| 13.5 | Tool activity in IDE | ✅ | ✅ |
| 13.6 | File diff in IDE | ✅ | ✅ |
| 13.7 | Terminal commands in IDE | ✅ | ✅ |
| 13.8 | Atomic session persistence | ✅ | ✅ |
| 13.9 | Reasoning-metadata preservation | ✅ | ✅ |
| 13.10 | Claude Code delegation skill | ✅ | ✅ |
| 13.11 | Codex CLI delegation skill | ✅ | ✅ |
| 13.12 | OpenCode CLI delegation skill | ✅ | ✅ |

## 14. API & integrations

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 14.1 | REST /api/chat | ✅ | ✅ |
| 14.2 | WebSocket | ✅ | ✅ |
| 14.3 | OpenAI /v1/chat/completions | ✅ | ✅ |
| 14.4 | OpenAI /v1/responses | ✅ | ✅ |
| 14.5 | OpenAI /v1/embeddings | ✅ | ✅ |
| 14.6 | OpenAI /v1/models | ✅ | ✅ |
| 14.7 | OpenAI /v1/files | 🟡 | ✅ 🆕 |
| 14.8 | OpenAI /v1/threads (Assistants) | ❌ | ✅ 🆕 optional |
| 14.9 | /api/jobs (cron REST) | ✅ | ✅ |
| 14.10 | Idempotency-Key header | ✅ (v0.5) | ✅ |
| 14.11 | X-Session-Id header | ✅ (v0.7) | ✅ |
| 14.12 | X-Session-Key header | ✅ | ✅ |
| 14.13 | Real-time tool progress streaming | ✅ | ✅ |
| 14.14 | CORS protection | ✅ | ✅ |
| 14.15 | Input limits + field whitelists | ✅ | ✅ |
| 14.16 | SQLite-backed response persistence | ✅ | ✅ |
| 14.17 | Subscription proxy (OAuth→OpenAI) | ✅ (v0.14) | ✅ |
| 14.18 | API key auth | ✅ | ✅ |
| 14.19 | JWT auth | 🟡 | ✅ |
| 14.20 | OAuth 2.0 for web | 🟡 | ✅ |
| 14.21 | mTLS service-to-service | ❌ | ✅ 🆕 |

## 15. Cron / Scheduling

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 15.1 | Cron expression scheduling | ✅ | ✅ |
| 15.2 | Natural language scheduling | ✅ | ✅ |
| 15.3 | Pause/resume/edit | ✅ | ✅ |
| 15.4 | Skill-attached jobs | ✅ | ✅ |
| 15.5 | Delivery to any platform | ✅ | ✅ |
| 15.6 | no_agent watchdog mode | ✅ (v0.13) | ✅ |
| 15.7 | Empty stdout silent | ✅ | ✅ |
| 15.8 | hermes/argo cron CRUD | ✅ | ✅ |
| 15.9 | Cron prompt-injection scan | ✅ | ✅ |
| 15.10 | Per-job retention/cleanup | ✅ | ✅ |
| 15.11 | Distributed cron (HA) | ❌ | ✅ 🆕 |

## 16. Security

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 16.1 | Secret redaction | ✅ default OFF v0.12+ | ✅ |
| 16.2 | OS sandbox (seccomp-bpf) | 🟡 via containers | ✅ 🆕 native Rust |
| 16.3 | rlimit applied | 🟡 | ✅ 🆕 |
| 16.4 | Dangerous command blocking | ✅ | ✅ improved |
| 16.5 | Audit log | 🟡 hermes debug | ✅ structured |
| 16.6 | Webhook HMAC verification | ✅ | ✅ (required) |
| 16.7 | Discord guild-scoped allowlists | ✅ (v0.13) | ✅ |
| 16.8 | WhatsApp stranger reject default | ✅ | ✅ |
| 16.9 | TOCTOU closure | ✅ | ✅ |
| 16.10 | Browser SSRF floor | ✅ | ✅ |
| 16.11 | Cron prompt-injection scan | ✅ | ✅ |
| 16.12 | hermes debug share redaction | ✅ | ✅ |
| 16.13 | Hashicorp Vault | ❌ | ✅ 🆕 |
| 16.14 | RBAC | ❌ | ✅ 🆕 |
| 16.15 | mTLS | ❌ | ✅ 🆕 |
| 16.16 | Per-user quotas | 🟡 | ✅ 🆕 |
| 16.17 | DDoS rate limit | 🟡 | ✅ 🆕 |
| 16.18 | Supply-chain scan | ✅ (v0.14) | ✅ |
| 16.19 | Container hardening | ✅ | ✅ |
| 16.20 | Skills security scan | ✅ | ✅ |
| 16.21 | Trust signals (community/trusted) | ✅ | ✅ |
| 16.22 | External security audit | ✅ | ✅ pre-GA |
| 16.23 | Bug bounty program | 🟡 | ✅ |
| 16.24 | **Compliance: GDPR** | 🟡 | ✅ 🆕 module |
| 16.25 | **Compliance: O'zR 152** | ❌ | ✅ 🆕 |
| 16.26 | **Compliance: Russia 152-FZ** | ❌ | ✅ 🆕 |
| 16.27 | **Compliance: China PIPL** | ❌ | ✅ 🆕 |

## 17. RL / Training

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 17.1 | Trajectory export (ShareGPT) | ✅ | ✅ |
| 17.2 | Atropos export | ✅ | ✅ |
| 17.3 | SFT export | ✅ | ✅ |
| 17.4 | Batch processing | ✅ | ✅ |
| 17.5 | Trajectory compression | ✅ | ✅ |
| 17.6 | RL tools (10) | ✅ | ✅ |

## 18. Observability

| # | Funksiya | Hermes | ARGO |
|---|---|---|---|
| 18.1 | Prometheus metrics | 🟡 | ✅ 🆕 first-class |
| 18.2 | OpenTelemetry traces | ❌ | ✅ 🆕 |
| 18.3 | Structured JSON logs | ✅ | ✅ |
| 18.4 | Grafana dashboards bundled | ❌ | ✅ 🆕 6 ta |
| 18.5 | Jaeger/Tempo integration | ❌ | ✅ 🆕 |
| 18.6 | Per-request trace IDs | 🟡 | ✅ |
| 18.7 | SIEM export (Splunk/ELK) | ❌ | ✅ 🆕 |

## 19. Internationalization (i18n)

| # | Til | Hermes (UI) | ARGO (UI+agent) |
|---|---|---|---|
| 19.1 | English | ✅ | ✅ |
| 19.2 | Chinese (Simplified) | ✅ | ✅ |
| 19.3 | Japanese | ✅ | ✅ |
| 19.4 | German | ✅ | ✅ |
| 19.5 | Spanish | ✅ | ✅ |
| 19.6 | French | ✅ | ✅ |
| 19.7 | Ukrainian | ✅ | ✅ |
| 19.8 | Turkish | ✅ | ✅ |
| 19.9 | Russian | 🟡 | ✅ first-class |
| 19.10 | **Uzbek (Latin)** | ❌ | ✅ 🆕 first-class |
| 19.11 | **Uzbek (Cyrillic)** | ❌ | ✅ 🆕 first-class |
| 19.12 | **Kazakh** | ❌ | ✅ 🆕 first-class |
| 19.13 | **Kyrgyz** | ❌ | ✅ 🆕 first-class |
| 19.14 | **Tajik** | ❌ | ✅ 🆕 first-class |
| 19.15 | **Turkmen** | ❌ | ✅ 🆕 first-class |
| 19.16 | Arabic | ❌ | ✅ 🆕 |
| 19.17 | Persian | ❌ | ✅ 🆕 |
| 19.18 | Hindi | ❌ | ✅ 🆕 |
| 19.19 | Portuguese | ❌ | ✅ 🆕 |
| 19.20 | Italian | ❌ | ✅ 🆕 |
| 19.21 | Polish | ❌ | ✅ 🆕 |
| 19.22 | Dutch | ❌ | ✅ 🆕 |
| 19.23 | Korean | ❌ | ✅ 🆕 |
| 19.24 | Vietnamese | ❌ | ✅ 🆕 |
| 19.25 | Thai | ❌ | ✅ 🆕 |
| 19.26 | Azerbaijani | ❌ | ✅ 🆕 |

## 20. OS / Platform support

| # | OS / Platform | Hermes | ARGO |
|---|---|---|---|
| 20.1 | Linux x86_64 | ✅ | ✅ |
| 20.2 | Linux ARM64 | ✅ | ✅ |
| 20.3 | macOS Intel | ✅ | ✅ |
| 20.4 | macOS Apple Silicon | ✅ | ✅ |
| 20.5 | Windows native | ✅ beta (v0.14) | ✅ |
| 20.6 | WSL2 | ✅ | ✅ |
| 20.7 | Android Termux | ✅ | ✅ |
| 20.8 | FreeBSD | ❌ | ✅ 🆕 |
| 20.9 | Docker | ✅ | ✅ |
| 20.10 | Kubernetes Helm | 🟡 | ✅ 🆕 official |

## 21. Installation & distribution

| # | Method | Hermes | ARGO |
|---|---|---|---|
| 21.1 | curl install.sh one-liner | ✅ | ✅ |
| 21.2 | PowerShell one-liner | ✅ | ✅ |
| 21.3 | pip install (PyPI) | ✅ | ✅ |
| 21.4 | cargo install (crates.io) | ❌ | ✅ 🆕 |
| 21.5 | Homebrew formula | 🟡 | ✅ |
| 21.6 | apt repo (Debian/Ubuntu) | ❌ | ✅ 🆕 |
| 21.7 | yum/dnf repo (RHEL/Fedora) | ❌ | ✅ 🆕 |
| 21.8 | Arch AUR | ❌ | ✅ 🆕 |
| 21.9 | Docker Hub + GHCR | ✅ | ✅ |
| 21.10 | Helm chart | 🟡 | ✅ |
| 21.11 | Lazy install of heavy deps | ✅ (v0.14) | ✅ |
| 21.12 | Tiered installer fallback | ✅ (v0.14) | ✅ |
| 21.13 | Bundled MinGit (Windows) | ✅ | ✅ |
| 21.14 | Bundled ripgrep/ffmpeg/uv | ✅ | ✅ |
| 21.15 | Auto-update | ✅ | ✅ `argo update` |

## 22. Documentation & ecosystem

| # | Asset | Hermes | ARGO |
|---|---|---|---|
| 22.1 | Documentation site | ✅ Docusaurus | ✅ |
| 22.2 | API reference | ✅ | ✅ |
| 22.3 | Migration guides | ✅ OpenClaw→Hermes | ✅ + Hermes→ARGO |
| 22.4 | Tutorials | ✅ | ✅ |
| 22.5 | Video tutorials | 🟡 | ✅ 🆕 UZ/RU/EN |
| 22.6 | GitHub stars | 140,000+ | start 0 → target 5,000 |
| 22.7 | Contributors | 295+ | start 1 → target 50+ |
| 22.8 | Awesome list | ✅ awesome-hermes-agent | ✅ awesome-argo-agent |
| 22.9 | Active issue tracker | ✅ | ✅ |
| 22.10 | Discord community | ✅ | ✅ |
| 22.11 | Newsletter (Hermes Atlas) | ✅ | ✅ |

## 23. Performance

| # | Metric | Hermes v0.14 | ARGO v3.0 target |
|---|---|---|---|
| 23.1 | Idle RAM | ~400 MB | <20 MB (20x) |
| 23.2 | Cold start | 1.5s | <150ms (10x) |
| 23.3 | Tool dispatch latency | ~10ms | <1ms (10x) |
| 23.4 | WS concurrent connections | ~5,000 | >50,000 (10x) |
| 23.5 | Per-request P50 latency (excl LLM) | ~80ms | <30ms (2.7x) |
| 23.6 | Memory ingestion throughput | ~500/s | >10,000/s (20x) |
| 23.7 | Binary size | N/A | <5 MB (Rust) |
| 23.8 | Full install size | ~800 MB | <200 MB (4x) |
| 23.9 | Container image (core) | ~150 MB | <100 MB |
| 23.10 | Disk fresh install data | 50 MB | <50 MB |

---

## Yakuniy hisob

| Kategoriya | Hermes-da bor | ARGO target | ARGO 🆕 exclusive |
|---|---|---|---|
| Architecture | 18 | 20 | 6 |
| Memory | 18 | 20 | 4 |
| Skills | 22 | 25 | 1 |
| Tools | ~70 | ~120 | ~25 (DevOps) |
| Terminal backends | 7 | 12 | 5 |
| Channels | 22 | 30+ | 8 (CIS + privacy) |
| LLM providers | 26 | 32+ | 6 (RU/CN) |
| Multi-agent | 17 | 19 | 1 (DAG) |
| MCP | 11 | 13 | 1 (gateway) |
| Plugin | 24 | 27 | 5 |
| Voice/multimedia | 18 | 22 | 4 |
| CLI/TUI/Web | 17 | 21 | 4 |
| IDE/ACP | 12 | 12 | 0 |
| API | 17 | 21 | 4 |
| Cron | 10 | 11 | 1 |
| Security | 20 | 27 | 7 |
| RL/training | 6 | 6 | 0 |
| Observability | 3 | 7 | 4 |
| i18n | 8 (mostly UI) | 26 | 15 (CA + extra) |
| OS support | 7 | 10 | 3 |
| Installation | 7 | 15 | 6 |
| **JAMI** | **~358** | **~474** | **~110** |

**Konklyuziya:** ARGO v3.0 to'liq paritet + ~110 ta exclusive funksiya. Hermes paritetining 100% (358/358) erishish + 30% qo'shimcha (110 yangi) — bu spec'ning umumiy hajmi.

*Hujjat versiyasi: 1.0 · Sana: May 2026*
