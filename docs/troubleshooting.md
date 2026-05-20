# Troubleshooting

This page collects the problems users hit most often and how to fix them.
When something is wrong, **start with `doctor`** — it diagnoses most issues
automatically.

## First step: run `doctor`

```bash
cd ARGO/argo-brain
python3 -m argo_brain doctor
```

`doctor` checks the Python version, the configuration file, the data
directory, whether `ANTHROPIC_API_KEY` is set, the presence of the `argo-core`
binary, and that the brain package imports cleanly. It exits non-zero if it
finds a **fatal** problem. A missing API key (mock mode) and a missing
`argo-core` binary are reported but are **not** fatal.

A quick subsystem smoke test:

```bash
python3 -m argo_brain selftest
```

## Installation and startup

### `python3: command not found` or wrong version

ARGO needs **Python 3.11 or newer**. Check with `python3 --version`. On some
systems the right interpreter is `python3.12`; use that explicitly if so.

### `ModuleNotFoundError: No module named 'argo_brain'`

You must run the brain from the `argo-brain/` directory (the package's parent),
because the brain is run as a module:

```bash
cd ARGO/argo-brain
python3 -m argo_brain chat
```

The brain has **no third-party dependencies**, so a missing-dependency error
should never come from ARGO itself.

### `cargo: command not found` when running `setup.sh`

This is **not fatal**. Cargo is only needed to build the optional `argo-core`
Rust gateway. The Python brain runs on its own and ships its own HTTP gateway
(`serve`). Install Rust only if you specifically want `argo-core`.

## Configuration

### My setting changes are ignored

Settings are resolved with this precedence (later wins):

1. Built-in defaults
2. `~/.argo/config.json`
3. `ARGO_*` environment variables

An `ARGO_*` environment variable **overrides** the config file. If a setting
will not change, check that no `ARGO_<NAME>` variable is shadowing it
(`env | grep ARGO`).

### `config.json` edits had no effect

A **corrupt** `config.json` is silently ignored and the defaults are used.
Validate the file is well-formed JSON:

```bash
python3 -m json.tool ~/.argo/config.json
```

Also confirm you are editing the right file — if `ARGO_HOME` is set, the
config lives at `$ARGO_HOME/config.json`, not `~/.argo/config.json`.

### The agent gives generic, canned replies

You are almost certainly running the **`MockProvider`**. That is the default
(`model: "mock"`) and needs no API key. To use a real model, set `model` to a
real model name *and* provide the matching API key:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ARGO_MODEL=claude-sonnet-4-6
```

See [Configuration](configuration.md) for the full provider list.

### A non-mock model still behaves like the mock

The provider is chosen by the `model` setting **plus** which API key is
present. If `model` is non-mock but **no** provider's API key is set in the
environment, ARGO falls back to the mock. Run `doctor` — it reports whether an
API key is visible. Remember to `source ~/.argo/env` if the wizard saved your
key there.

## IPC socket issues

`argo-core` and `argo-brain` talk over a **Unix domain socket** (default
`~/.argo/argo.sock`).

### `argo-core` cannot connect to the brain

- The brain's IPC server must be running: `python3 -m argo_brain ipc`.
- Both processes must agree on the socket path. Check the `ipc_socket` setting
  / the `ARGO_IPC_SOCKET` environment variable is **identical** for both.
- In Docker/Kubernetes, both containers must mount the **same volume** at the
  socket directory. The shipped Compose file and Helm chart already do this.

### `Address already in use` on the socket

A stale socket file was left behind by a process that did not shut down
cleanly. Stop any running brain, remove the stale file and restart:

```bash
rm -f ~/.argo/argo.sock
python3 -m argo_brain ipc
```

### `Permission denied` on the socket

The user running `argo-core` must have read/write access to the socket file
and its directory. Make sure both services run as the same user, or that the
socket directory's permissions allow both.

## HTTP gateway

### `Address already in use` on port 8000

Another process holds the port. Either stop it, or start the gateway on a
different port:

```bash
python3 -m argo_brain serve --port 8080
```

### `/api/chat` returns nothing useful

Confirm the gateway is healthy first:

```bash
curl http://127.0.0.1:8000/api/health
```

Then check your request shape — `/api/chat` expects JSON with `user_id` and
`message`:

```bash
curl -s http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "alice", "message": "Hello"}'
```

## Channels

### `argo_brain telegram` exits immediately

The `TELEGRAM_BOT_TOKEN` environment variable is not set. Create a bot with
[@BotFather](https://t.me/BotFather), then:

```bash
export TELEGRAM_BOT_TOKEN=<your-token>
python3 -m argo_brain telegram
```

### The Slack webhook is not registered

The Slack webhook is added to `serve` **only when `SLACK_BOT_TOKEN` is set**.
Export it before starting the gateway. The gateway prints the registered
webhook platforms on startup — check that list. See [Channels](channels.md).

## Tools

### A DevOps tool fails with "command not found"

The DevOps tools (`git_*`, `docker_*`, `kubectl_get`, `vault_*`,
`terraform_*`, etc.) are **thin wrappers** around the real CLIs. They fail
*cleanly* when the underlying CLI is not installed — install the CLI on the
host to use the tool. This failure does not break the agent loop.

### The agent stops with "maximum number of iterations exceeded"

The agent loop hit `max_iterations` (default `8`) without producing a final
answer. Raise the limit if a genuinely long task needs it:

```bash
export ARGO_MAX_ITERATIONS=12
```

If a task *always* loops, it is usually a tool failing repeatedly — check the
tool output in the reply's metadata.

## Memory

### History is not being remembered

L1 history is stored in the SQLite database at `db_path` (default
`<data_dir>/argo.db`). Confirm the `data_dir` is writable and persistent. In a
container, ensure the data volume is mounted — otherwise history is lost on
restart.

## Still stuck?

- Re-run `python3 -m argo_brain doctor` and read its output carefully.
- Raise the log level: `export ARGO_LOG_LEVEL=DEBUG`.
- Check the [FAQ](faq.md) and the [CHANGELOG](../CHANGELOG.md) for whether the
  feature is implemented yet.
- Open an issue at <https://github.com/oybek1097/ARGO>.
