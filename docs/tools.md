# Tools

Tools are the actions ARGO's agent can take beyond generating text — reading
files, running shell commands, querying Git, fetching web pages and so on.

## How tools work

Every tool is a subclass of the `Tool` abstract base class
(`argo_brain/tools/base.py`). A tool defines:

- `name` — the tool's identifier.
- `description` — what the tool does (shown to the model).
- `parameters` — a JSON schema for the tool's arguments.
- `dangerous` — a flag; when set, confirmation is requested for mutations.
- an async `run(user_id, **kwargs)` method that returns a `ToolResult`.

A `ToolResult` carries `content`, a `success` flag, a `duration_ms`
measurement and a `metadata` dictionary. Tool exceptions are caught so a
failing tool never breaks the agent loop — the failure is returned as an
unsuccessful `ToolResult`.

### The registry

The `ToolRegistry` registers tools, exposes their OpenAI-style function
schemas to the LLM, and executes calls. It can run multiple tool calls in
**parallel**, bounded by a semaphore (the `max_parallel_tools` setting,
default 8).

`build_default_registry()` constructs a registry populated with all the
built-in toolsets. Memory-dependent tools are added only when a memory
manager is supplied.

## Built-in toolsets

ARGO ships dozens of built-in tools, grouped into toolsets:

### basic

Core everyday tools: `current_time`, `calculate`, `read_file`, `list_dir`,
`memory_search`.

### web

HTTP and web access: `http_get`, `http_post`, `web_fetch`.

### terminal

Shell access: `shell_exec`.

### file

File operations: `write_file`, `find_files`, `grep_files`.

### text

Text processing: `diff_text`, `csv_parse`, `zip_create`, `zip_extract`,
`regex_extract`, `template_render`.

### system

System inspection: `disk_usage`, `env_get`, `dns_lookup`, `port_check`,
`system_info`, `http_status`.

### devops

Audited DevOps CLI wrappers — Git and containers: `git_status`, `git_log`,
`git_diff`, `git_branch`, `git_commit`, `docker_ps`, `docker_images`,
`kubectl_get`. Extended DevOps tools cover secrets and infrastructure:
`vault_get`, `vault_put`, `ssh_exec`, `ansible_playbook`, `terraform_plan`,
`terraform_apply`. These are thin wrappers around the underlying CLIs and
fail cleanly when a CLI is not installed.

### data

Data utilities: `sql_query`, `json_query`, `hash_text`, `uuid_generate`,
`datetime_now`.

### memory

Memory tools (registered only when memory is available): `memory_remember`,
plus `memory_search` from the basic toolset.

### workflow

Agent-control tools that help the agent plan and pace its work: `todo`,
`clarify`, `wait`, `plan`.

## MCP tools

In addition to the built-in tools, ARGO can connect to external **Model
Context Protocol (MCP)** servers and register their tools automatically. Such
tools appear in the registry with the name `mcp_<server>_<tool>`. Configure
MCP servers in `~/.argo/config.json` (see [Configuration](configuration.md))
and inspect them with `python3 -m argo_brain mcp`.

ARGO can also act as an MCP **server**, exposing its own tools to other MCP
clients.

## Extending ARGO with plugins

Beyond tools, ARGO has a 5-hook plugin API (pre-tool, post-tool, on-response
and related hooks). Plugins can veto tool calls, transform tool results and
react to responses. Plugin files live in `~/.argo/plugins/`.
</content>
