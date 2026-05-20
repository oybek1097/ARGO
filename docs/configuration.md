# Configuration

ARGO's Python brain reads its configuration from three sources, in increasing
order of priority:

1. **Built-in defaults.**
2. **The `~/.argo/config.json` file.**
3. **`ARGO_*` environment variables** (these win over everything else).

## The configuration file

The configuration file lives at `~/.argo/config.json` (or
`$ARGO_HOME/config.json` if `ARGO_HOME` is set). It is plain JSON. The
`argo_brain setup` wizard creates it for you; you can also edit it by hand.

A minimal file:

```json
{
  "model": "mock",
  "log_level": "INFO"
}
```

## Settings

The following settings are recognized. Each can be set in `config.json` or
overridden with the matching `ARGO_<NAME>` environment variable (uppercase).

| Setting | Default | Description |
|---|---|---|
| `data_dir` | `~/.argo/data` | Directory for SQLite databases and other data. |
| `db_path` | `<data_dir>/argo.db` | Path to the main SQLite database. |
| `ipc_socket` | `~/.argo/argo.sock` | Unix socket path for argo-core ↔ argo-brain IPC. |
| `model` | `mock` | LLM model — `mock`, `claude-sonnet-4-6`, `claude-opus-4-7`, etc. |
| `max_iterations` | `8` | Maximum iterations of the agent loop. |
| `context_history` | `20` | Number of history turns added to the prompt. |
| `max_parallel_tools` | `8` | Parallel tool-dispatch limit. |
| `working_memory_size` | `200` | L0 working-memory ring-buffer size per user. |
| `log_level` | `INFO` | Logging level. |

A corrupt `config.json` is ignored silently and the defaults are used.

## Environment variables

### `ARGO_*` settings overrides

Every setting above has a corresponding environment variable. For example:

```bash
export ARGO_MODEL=claude-sonnet-4-6
export ARGO_MAX_ITERATIONS=12
export ARGO_LOG_LEVEL=DEBUG
```

### `ARGO_HOME`

`ARGO_HOME` relocates the entire ARGO data directory (default `~/.argo`). It
is honoured by the installer, the setup wizard, the `doctor` command and the
brain itself.

```bash
export ARGO_HOME=/opt/argo
```

## Provider API keys

The LLM provider is chosen by the `model` setting plus which API key is
present in the environment:

- `model = "mock"` (or no API key) → the **MockProvider**, which needs no
  credentials and is used for demos and tests.
- A non-mock `model` picks the first provider whose API key is set, in this
  order:

| Provider | Environment variable |
|---|---|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Gemini | `GEMINI_API_KEY` |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

The setup wizard can save an Anthropic key to `~/.argo/env` (with `0600`
permissions). Load it into your shell with `source ~/.argo/env`.

## Channel credentials

Messaging channels read their credentials from the environment. For example:

```bash
export TELEGRAM_BOT_TOKEN=...   # required by `argo_brain telegram`
export SLACK_BOT_TOKEN=...      # enables the Slack webhook in `serve`
```

See [Channels](channels.md) for the full list.

## MCP servers

External MCP servers are configured in `~/.argo/config.json` under an `mcp`
key:

```json
{
  "model": "mock",
  "mcp": {
    "servers": [
      { "name": "my-server", "command": "path/to/mcp-server" }
    ]
  }
}
```

Their tools are then discovered and registered as `mcp_<server>_<tool>`.
See [Tools](tools.md) and the [CLI reference](cli.md#mcp).
