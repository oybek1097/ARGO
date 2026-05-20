# FAQ

Honest, factual answers about ARGO. Where a feature is not built yet, this
page says so plainly.

## What is ARGO?

ARGO Agent v3.0 is an open-source, multilingual AI agent platform. It runs a
conversational AI agent that can call tools, remember conversations, connect
to messaging platforms, coordinate multiple agents and integrate with external
services over the Model Context Protocol (MCP). It is split into a small Rust
gateway (`argo-core`) and a Python brain (`argo-brain`). See
[Introduction](introduction.md) and [Architecture](architecture.md).

## What is the project's status — is it production-ready?

ARGO is **alpha approaching GA**. It is a 12-sprint project per the
[technical specification](../ARGO_AGENT_v3_Technical_Specification.md). Most
core subsystems are implemented and covered by a stdlib `unittest` suite
(several hundred tests). However:

- Some features are **roadmap-only** and are marked as such throughout these
  docs (for example: PyPI publishing, asymmetric package signatures, the
  Kanban zombie-reclaim and LLM-judge gate, a pluggable embedding backend for
  L2 memory).
- APIs may still change before the GA release.

Treat ARGO as solid for evaluation, internal tooling and self-hosted
experiments. For mission-critical production use, pin a version and test
thoroughly. The authoritative, up-to-date status is in
[`../CHANGELOG.md`](../CHANGELOG.md).

## Do I need an API key to try it?

No. The default `MockProvider` (`model: "mock"`) runs the full agent loop
**offline with no API key**, deterministically simulating tool calls. It is
ideal for demos, tests and a first look. For real model responses, configure a
provider — see [Configuration](configuration.md).

## Which LLM providers are supported?

The brain ships a provider abstraction with: `MockProvider` (no key),
`AnthropicProvider`, `OpenAIProvider`, `GeminiProvider`, `OllamaProvider`, and
a generic `OpenAICompatibleProvider` that covers OpenAI-compatible endpoints
such as DeepSeek, Groq, Mistral, OpenRouter and Together. The provider is
chosen by the `model` setting plus which API key is present in the
environment. See [Configuration](configuration.md).

## Which languages does ARGO support?

ARGO has built-in heuristic **language detection** for Uzbek, Russian, Kazakh,
Kyrgyz, Tajik and English (`uz`/`ru`/`kk`/`ky`/`tg`/`en`). The agent is
instructed to reply in the user's detected language. This Central Asian
language focus is a deliberate niche for ARGO.

Note the distinction: ARGO is a multilingual **product**, but its **codebase**
— code, comments, docstrings and these docs — is written entirely in English.

## Can I self-host ARGO? Does it work offline / air-gapped?

Yes. ARGO is designed for sovereign, on-premises deployment:

- The Python brain runs on the **standard library only** — nothing to install,
  nothing to phone home.
- The `MockProvider` needs no network at all.
- For real LLM responses you can point a provider at an **on-premises**
  endpoint (an Ollama server, or any OpenAI-compatible server).
- It ships PII redaction, an append-only audit log, and region-specific
  compliance modules (UZ-152, RU-152-FZ, GDPR, CN-PIPL).

See [Deployment](deployment.md).

## Do I need to build the Rust `argo-core`?

No — building `argo-core` is **optional**. The Python brain ships its own HTTP
gateway (the `serve` command) that stands in for `argo-core`. Build the Rust
gateway when you want its small, hardened external face and Prometheus
metrics; otherwise run the brain alone. See [Architecture](architecture.md).

## How is ARGO licensed?

ARGO is distributed under the **MIT** license. See [`../LICENSE`](../LICENSE).
Contributions are accepted under the same license — see
[Contributing](contributing.md).

## How do I extend ARGO?

Three extension points:

- **Tools** — subclass the `Tool` ABC to give the agent a new action. See
  [Tools](tools.md).
- **Skills** — drop an agentskills.io-style Markdown file in `~/.argo/skills/`
  to teach ARGO a procedure. See [Skills](skills.md).
- **Plugins** — a 5-hook API (pre-tool, post-tool, on-response, ...) to veto
  tool calls, transform results and react to responses.

Skills and plugins can be packaged and shared as signed `.argopkg` packages
through the [Hub & Marketplace](hub.md).

## What is the difference between a tool, a skill and a plugin?

- A **tool** is *how* ARGO acts — an executable action like reading a file or
  running `git status`.
- A **skill** is *what to do* — Markdown instructions injected into the prompt
  when relevant.
- A **plugin** is *control logic* — Python hooks that intercept the agent loop
  (veto a tool call, rewrite a result).

## How does ARGO compare to the Hermes Agent ecosystem?

ARGO explicitly aims for **feature parity with Hermes** and then adds
functionality for two niches Hermes does not target:

- **Central Asian / multilingual** use — built-in detection and replies in
  uz/ru/kk/ky/tg/en.
- **Sovereign / on-premises** deployment — a stdlib-only brain, PII redaction,
  an audit log, and regional compliance modules (UZ-152, RU-152-FZ, GDPR,
  CN-PIPL).

A detailed, item-by-item comparison is maintained in the repository's
`ARGO_Hermes_Parity_Matrix.md`. Honest caveat: ARGO is younger than Hermes and
still alpha, so parity is a target the project is working toward, not a
finished claim — check the parity matrix and [`../CHANGELOG.md`](../CHANGELOG.md)
for the current state.

## Where is the configuration stored?

In `~/.argo/` (relocatable with the `ARGO_HOME` environment variable). The
main file is `~/.argo/config.json`; data, skills and plugins live in
sub-directories. See [Configuration](configuration.md).

## How do I report a bug or contribute?

Open an issue or pull request at <https://github.com/oybek1097/ARGO>. See
[Contributing](contributing.md) and [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## See also

- [Troubleshooting](troubleshooting.md) — fixes for common problems.
- [Architecture](architecture.md) — how ARGO is built.
- [`../CHANGELOG.md`](../CHANGELOG.md) — the authoritative current state.
