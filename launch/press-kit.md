# ARGO Agent v3.0 — Press Kit

For journalists, bloggers, and community curators. Everything here may be
quoted or reproduced. ARGO is MIT licensed.

---

## Descriptions (use the one that fits the format)

### One-line (≤ 100 chars)

> ARGO is an open-source, self-hosted AI agent platform built for Central
> Asian languages and DevOps.

### Short (≈ 50 words)

> ARGO Agent is an open-source AI agent platform you run yourself. A small
> Rust gateway handles the network edge; a Python brain runs the agent
> loop, tools, and memory. It speaks Uzbek, Russian, Kazakh, Kyrgyz and
> Tajik natively, ships DevOps tooling, and is MIT licensed.

### Long (≈ 130 words)

> ARGO Agent v3.0 is an open-source, self-hosted AI agent platform with a
> two-part architecture: `argo-core`, a small hardened Rust gateway
> (Axum + Tokio) that is the only network-facing component, and
> `argo-brain`, a Python brain that runs the Plan→Execute agent loop,
> built-in tools, and tiered memory. The two communicate over a Unix
> socket.
>
> ARGO is built for two underserved niches. First, Central Asian
> languages: it does native language detection and response routing for
> Uzbek (Latin and Cyrillic), Russian, Kazakh, Kyrgyz and Tajik. Second,
> sovereign and DevOps deployment: it is self-hosted by default, has an
> airgapped mode, and ships tools for shell, files, Git, Docker and
> Kubernetes. The Python brain runs on the standard library alone, so
> there is nothing to install to try it. ARGO is MIT licensed and is
> currently in alpha, approaching its v3.0 general-availability release.

---

## Key facts

| | |
|---|---|
| Project name | ARGO Agent |
| Version | v3.0 (alpha, approaching GA) |
| Category | AI agent platform / developer tool |
| License | MIT |
| Architecture | Rust gateway (`argo-core`) + Python brain (`argo-brain`) |
| Languages (native agent) | Uzbek (Latin + Cyrillic), Russian, Kazakh, Kyrgyz, Tajik, English |
| Deployment | Self-hosted; Docker Compose; airgapped mode supported |
| Dependencies | Python brain runs on the standard library only |
| Built-in tools today | 13 (shell, files, Git, Docker, kubectl, memory, web, and more) |
| Channels today | Telegram, Slack, generic webhook |
| Memory | L0 in-process deque + L1 SQLite/FTS5 |
| LLM providers today | Anthropic + a local mock; more on the roadmap |
| Tests | 84 passing |
| Roadmap | 12-sprint plan; full technical spec in the repository |

> A note on numbers: the technical specification lists performance
> *targets* for the Rust gateway (low idle memory, fast cold start,
> sub-millisecond IPC). These are design targets, not measured marketing
> claims, and should be described as targets. Verified benchmarks will be
> published with the GA release.

---

## Target users

1. CIS DevOps engineers (Russia, Uzbekistan, Kazakhstan, Kyrgyzstan).
2. Central Asian startups that need an assistant in the local language.
3. Governments and banks needing sovereign, self-hosted deployment.
4. Independent developers who want a small, auditable agent stack.
5. Privacy-first users who need offline / airgapped operation.

---

## Project quote

> "Most AI agent tooling assumes English and a US-hosted API. For a
> developer in Tashkent or Almaty, neither assumption fits. We built ARGO
> the other way around — self-hosted first, Central Asian languages as a
> first-class concern, and small enough to actually audit. It's alpha
> today, and we're launching now precisely because we want the region's
> developers shaping it before GA."
> — The ARGO Project team

---

## Logo and visual assets

The following assets are available on request (described here; supply the
actual files alongside this kit):

- **Primary logo** — the ARGO wordmark, full color, on transparent
  background. PNG (at 256, 512, 1024 px) and SVG.
- **Logo, monochrome** — black-on-transparent and white-on-transparent
  variants, PNG + SVG, for single-color contexts.
- **App icon / mark** — the square "A" mark without the wordmark, for
  favicons and avatars, 512 px PNG + SVG.
- **Hero banner** — 1600×900 banner: logo, tagline, dark theme; for
  article headers.
- **Architecture diagram** — User → Channel adapter → argo-core (Rust)
  → IPC → argo-brain (Python), PNG + SVG.
- **Screenshot set** — (a) the `chat` CLI in a multilingual session,
  (b) ARGO answering in a Telegram chat, (c) `docker compose up` with
  both services healthy. PNG, dark theme.
- **Color and type notes** — dark base background, single accent color,
  monospace for all terminal/code imagery.

All assets are released for editorial use under the project's MIT terms.

---

## Links

- GitHub repository: <link>
- Quick start / documentation: <link>
- Technical specification: `ARGO_AGENT_v3_Technical_Specification.md` (in repo)
- Executive summary: `ARGO_Executive_Summary.md` (in repo)
- Changelog: `CHANGELOG.md` (in repo)
- Tutorial videos (EN/RU/UZ): <playlist link>

## Contact

- Press / general: <press email>
- Maintainers: via GitHub issues and discussions on the repository
- Project lead contact: akbarshohanvarbekov@gmail.com

*Press kit version 1.0 — May 2026.*
