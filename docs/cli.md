# CLI reference

The ARGO brain is driven through a single command-line interface:

```bash
python3 -m argo_brain <command> [options]
```

Run it from the `argo-brain/` directory. If no command is given, `chat` is
used as the default.

## Command summary

| Command | Purpose |
|---|---|
| [`setup`](#setup) | Interactive first-run setup wizard. |
| [`doctor`](#doctor) | Diagnose the installation. |
| [`chat`](#chat) | Interactive conversation in the terminal. |
| [`tui`](#tui) | Rich interactive terminal UI. |
| [`serve`](#serve) | Run the HTTP API gateway. |
| [`ipc`](#ipc) | Run the IPC server (Unix socket). |
| [`telegram`](#telegram) | Run the Telegram channel. |
| [`mcp`](#mcp) | List tools from configured MCP servers. |
| [`selftest`](#selftest) | Run the subsystem smoke test. |
| [`version`](#version) | Print version information. |

---

## setup

```bash
python3 -m argo_brain setup
```

The interactive first-run wizard. It asks you to choose an LLM model
(`mock`, `claude-sonnet-4-6` or `claude-opus-4-7`), optionally enter an
`ANTHROPIC_API_KEY`, and pick the HTTP gateway port. It then creates the
`~/.argo` directory layout and writes `~/.argo/config.json`. If you provide
an API key it is saved to `~/.argo/env` with `0600` permissions.

## doctor

```bash
python3 -m argo_brain doctor
```

Diagnoses the installation. Checks Python 3.11+, the configuration file, the
data directory, whether `ANTHROPIC_API_KEY` is set, the presence of the
`argo-core` binary, and that the brain package imports. A missing API key
(mock mode) and a missing `argo-core` binary are not fatal. Exits non-zero if
a fatal problem is found.

## chat

```bash
python3 -m argo_brain chat
```

Opens an interactive conversation REPL. Works with the default `mock`
provider without an API key. Each reply is annotated with the detected
language, the model, the iteration count, the duration and any tools used.
Exit with `/exit`, `/quit` or `/q`. Configured MCP servers are connected
automatically and their tools made available.

## tui

```bash
python3 -m argo_brain tui
```

Launches the rich interactive terminal UI, backed by the same agent as
`chat`.

## serve

```bash
python3 -m argo_brain serve [--host HOST] [--port PORT]
```

Runs the Python HTTP API gateway.

- `--host` — bind address (default `127.0.0.1`).
- `--port` — bind port (default `8000`).

Exposes `/api/health`, `/api/version`, `/api/chat`, `/api/history`, a web
dashboard at `/` and an inbound `/webhook/<platform>` route. The generic
webhook is always registered; the Slack webhook is added when
`SLACK_BOT_TOKEN` is set. Stop with `Ctrl+C`.

## ipc

```bash
python3 -m argo_brain ipc
```

Runs the IPC server on a Unix domain socket, using line-delimited JSON. This
is the endpoint the `argo-core` Rust gateway connects to. The socket path
defaults to `~/.argo/argo.sock` (configurable via `ipc_socket` /
`ARGO_IPC_SOCKET`). Stop with `Ctrl+C`.

## telegram

```bash
export TELEGRAM_BOT_TOKEN=<your-token>
python3 -m argo_brain telegram
```

Runs the Telegram channel (long polling) and bridges it to the agent.
Requires the `TELEGRAM_BOT_TOKEN` environment variable; without it the
command prints setup instructions and exits. Stop with `Ctrl+C`.

## mcp

```bash
python3 -m argo_brain mcp
```

Connects the MCP servers configured in `~/.argo/config.json` and lists the
tools they expose. If no servers are configured it prints the JSON snippet
needed to add one.

## selftest

```bash
python3 -m argo_brain selftest
```

Runs a smoke test across the main subsystems — basic chat, the calculate and
time tools, memory persistence, the tool suite, the Kanban lifecycle and the
cron natural-language parser. Exits non-zero if any check fails.

## version

```bash
python3 -m argo_brain version
```

Prints the `argo-brain` version.
