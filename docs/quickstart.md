# Quickstart

This page walks you through your first run of ARGO. It assumes you have
followed the [Installation](installation.md) steps and have Python 3.11+
available.

All commands below are run from the `argo-brain/` directory:

```bash
cd ARGO/argo-brain
```

## 1. Run the setup wizard

```bash
python3 -m argo_brain setup
```

The wizard asks you to:

- **Choose an LLM model.** Option `1` is `mock` — no API key needed. Options
  `2` and `3` are Anthropic models (`claude-sonnet-4-6`, `claude-opus-4-7`)
  and require an API key.
- **Provide an API key** (only if you picked a non-mock model). The key is
  saved to `~/.argo/env` with `0600` permissions.
- **Pick the HTTP gateway port** (default `8000`).

The wizard writes `~/.argo/config.json` and creates the `data/` and `skills/`
directories. If you saved an API key, load it into your shell before the next
steps:

```bash
source ~/.argo/env
```

## 2. Start chatting

The fastest way to try ARGO is the interactive chat:

```bash
python3 -m argo_brain chat
```

This opens a REPL. With the default `mock` provider it needs no API key and
deterministically simulates tool calls — handy for trying the agent loop
offline. Each reply shows the detected language, the model, the number of
agent-loop iterations, the duration and any tools used.

Type `/exit` (or `/quit`, `/q`) to leave.

## 3. Use the terminal UI

For a richer terminal experience:

```bash
python3 -m argo_brain tui
```

The `tui` command launches the interactive terminal UI backed by the same
agent.

## 4. Serve the HTTP gateway

To expose ARGO over HTTP:

```bash
python3 -m argo_brain serve --host 127.0.0.1 --port 8000
```

This starts the Python HTTP gateway. It exposes `/api/health`,
`/api/version`, `/api/chat`, `/api/history`, a web dashboard at `/` and an
inbound `/webhook/<platform>` route. The gateway prints the address and the
registered webhook platforms on startup.

Send a chat request:

```bash
curl -s http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "alice", "message": "Hello, ARGO!"}'
```

## 5. Run a Telegram bot

Create a bot with [@BotFather](https://t.me/BotFather) on Telegram, then:

```bash
export TELEGRAM_BOT_TOKEN=<your-token>
python3 -m argo_brain telegram
```

ARGO connects to Telegram with long polling and bridges incoming messages to
the agent. If `TELEGRAM_BOT_TOKEN` is not set, the command exits with
instructions.

## What next?

- [CLI reference](cli.md) — the full list of commands.
- [Configuration](configuration.md) — switch providers, tune the agent loop.
- [Channels](channels.md) — connect Slack, Email, IRC, Matrix and more.
- [Tools](tools.md) — see what the agent can do.
</content>
