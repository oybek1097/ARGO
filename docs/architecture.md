# Architecture

ARGO is built from two cooperating components: a small Rust gateway and a
rich Python brain.

```
User ─► Channel adapter ─► argo-core (Rust) ──IPC──► argo-brain (Python)
                           HTTP/WS gateway          agent loop + tools
```

## The two components

### argo-core — the Rust gateway

`argo-core` is the small, hardened external face of ARGO, built on
**Axum + Tokio**. Responsibilities:

- The HTTP and WebSocket gateway: `/api/health`, `/api/version`, `/api/chat`,
  `/api/history/:uid`, `/metrics`, a `/ws/:uid` WebSocket endpoint and an
  OpenAI-compatible `/v1/chat/completions` endpoint.
- The **L0 working memory** — a per-user ring buffer held in a `DashMap`.
- Prometheus metrics.
- A Unix-socket IPC client that forwards work to the brain.

The release binary is roughly 1.3 MB. Building `argo-core` requires Rust and
is optional — the brain ships its own HTTP gateway that stands in for it.

### argo-brain — the Python brain

`argo-brain` holds the AI logic and runs on the Python standard library only.
Its main subsystems live under `argo_brain/`:

| Subsystem | Directory | Role |
|---|---|---|
| Agent loop | `core/` | The Plan → Execute loop (`AgentCore`). |
| Memory | `memory/` | L0 working, L1 persistent, L2 vector memory. |
| Tools | `tools/` | The tool ABC, registry and built-in toolsets. |
| Providers | `providers/` | LLM abstraction — Mock, Anthropic, OpenAI, Gemini, Ollama. |
| Channels | `channels/` | Messaging-platform adapters. |
| MCP | `mcp/` | Model Context Protocol client and server. |
| Skills | `skills/` | Markdown skill loader (agentskills.io style). |
| Plugins | `plugin/` | A 5-hook plugin API and registry. |
| Multi-agent | `multi_agent/` | A durable SQLite Kanban board and workflow runner. |
| Cron | `cron/` | A scheduler with a natural-language schedule parser. |
| Security | `security/` | PII redaction and an append-only audit log. |
| Compliance | `compliance/` | UZ-152, RU-152-FZ, GDPR, CN-PIPL policy modules. |
| RL | `rl/` | A trajectory collector with ShareGPT/SFT/JSONL export. |
| Checkpoint / handoff | `checkpoint/`, `handoff/` | File-snapshot checkpoints and SQLite handoff tickets. |
| API / IPC | `api/`, `ipc/` | The HTTP gateway and the Unix-socket IPC server. |
| TUI | `tui/` | The rich terminal UI. |

## Inter-process communication (IPC)

`argo-core` and `argo-brain` communicate over a **Unix domain socket**. The
protocol is **line-delimited JSON**: one JSON request object per line, one
JSON response object per line.

The socket path defaults to `~/.argo/argo.sock` and can be overridden with the
`ipc_socket` configuration setting or the `ARGO_IPC_SOCKET` environment
variable.

Start the brain's IPC server with:

```bash
python3 -m argo_brain ipc
```

The brain's `AgentResponse` is serialized for IPC with these fields:
`content`, `language`, `model`, `tools_used`, `iterations`, `duration_ms`
and `error`.

## The three-layer memory

ARGO's memory is layered:

- **L0 — working memory.** A per-user ring buffer (a `deque`) of recent turns.
  In a full deployment this lives in `argo-core`; the brain also keeps an L0
  buffer whose size is set by `working_memory_size` (default 200).
- **L1 — persistent memory.** A SQLite database with an FTS5 full-text index.
  Conversation history is stored here and is searchable.
- **L2 — vector memory.** A vector store using a standard-library hashing
  vectorizer and cosine-similarity search for semantic recall.

The `MemoryManager` in `argo_brain/memory/` orchestrates these layers — user
profiles, history retrieval and persistence.

## The agent loop

The `AgentCore.process()` method implements a **Plan → Execute** loop:

1. **Language detection.** The incoming message's language is detected
   (`uz`/`ru`/`kk`/`ky`/`tg`/`en`) unless the caller supplies one.
2. **User profile.** The user's profile is ensured in memory.
3. **Context assembly.** Recent history (up to `context_history` turns, default
   20) is loaded, and any skills relevant to the message are selected.
4. **System prompt.** A system prompt is built, instructing ARGO to reply in
   the detected language, with relevant skills injected.
5. **The loop.** For up to `max_iterations` iterations (default 8):
   - The LLM provider is called with the conversation and the tool schemas.
   - If the response contains tool calls, plugins may veto them via the
     pre-tool hook, the tools run in parallel (bounded by
     `max_parallel_tools`, default 8), each result passes through the
     post-tool hook, and results are fed back to the model.
   - If the response has no tool calls, it is the final answer.
6. **Persistence.** The user message and the assistant reply are written to
   memory.
7. **Response hook.** Plugins receive the final response via the `on_response`
   hook.

If the loop reaches `max_iterations` without a final answer, ARGO returns a
"maximum number of iterations exceeded" message.

> The reflection queue, trajectory export and prompt cache are noted in the
> code as planned for a later sprint.
</content>
