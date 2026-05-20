# Product Hunt — ARGO Agent v3.0

## Name

ARGO Agent

## Tagline (max 60 chars)

> Self-hosted AI agent for Central Asian languages & DevOps

Alternates (pick one, all under 60 chars):
- Open-source AI agent — sovereign, multilingual, Rust core
- Your own AI agent: self-hosted, Uzbek/Russian-native, MIT

## Topics / tags

`Artificial Intelligence`, `Open Source`, `Developer Tools`,
`Productivity`, `Self-Hosted`, `Bots`

## Description (260 chars)

ARGO is an open-source AI agent platform you run yourself — a small Rust
gateway plus a Python brain. It speaks Central Asian languages natively
(Uzbek, Russian, Kazakh, Kyrgyz, Tajik), ships DevOps tools, and is easy
to try: the brain runs on the Python stdlib alone.

## First comment (from the maker)

Hi Product Hunt 👋

I'm one of the people behind ARGO Agent. I want to be upfront: **ARGO is
alpha, approaching its v3.0 GA.** It is real and usable today, but it is
not a finished, polished product yet — and I'd rather you knew that going
in than be disappointed later.

Why we built it:

Most AI agent frameworks assume you'll use a US-hosted API and English.
For a developer in Tashkent, Almaty, or Bishkek, neither assumption
holds well. ARGO is built the other way around:

- **Self-hosted first.** You run it on your own machine or server. No
  account, no telemetry phoning home. There is an airgapped mode for
  environments with no outbound internet.
- **Central Asian languages are native, not an afterthought.** Language
  detection and response routing cover Uzbek (Latin + Cyrillic),
  Russian, Kazakh, Kyrgyz, Tajik, and English.
- **DevOps is built in.** Tools for shell, files, Git, Docker, and
  Kubernetes — useful if your agent's job is to actually operate things.
- **It is genuinely easy to try.** The Python brain runs on the
  **standard library only**. No `pip install` to get a conversation
  going. There's a `chat` command that works with a local mock model,
  so you can poke at it before deciding to wire up a real LLM.

Architecture: a hardened Rust gateway (`argo-core`, Axum + Tokio) is the
small external face; a Python brain (`argo-brain`) holds the agent loop
and tools. They talk over a Unix socket.

Where it honestly stands today: the Rust gateway, the Plan→Execute agent
loop, 13 built-in tools, L0/L1 memory (deque + SQLite/FTS5), Telegram +
Slack + webhook channels, a setup wizard, and 84 passing tests. More
channels, a web dashboard, and a larger tool library are on the roadmap
(it's a 12-sprint project; the full plan is in the repo).

It's MIT licensed. We'd love bug reports, language corrections from
native speakers, and contributors. Try it, break it, tell us.

GitHub: <link to repo>
Docs / quick start: <link>
Thanks for taking a look 🙏

## Gallery shot list

Product Hunt allows up to ~8 images/GIFs. Suggested set:

1. **Hero card** — ARGO logo + tagline "Self-hosted AI agent for Central
   Asian languages & DevOps" on a clean dark background.
2. **Quick start (terminal screenshot)** — the README quick start block:
   `./scripts/setup.sh` then `python3 -m argo_brain chat`, with the
   caption "No API key needed to try it."
3. **Multilingual conversation (GIF)** — a `chat` session where the user
   types in Uzbek and Russian and ARGO replies in the same language;
   caption "Detects and replies in your language."
4. **Architecture diagram** — User → Channel adapter → argo-core (Rust)
   → IPC → argo-brain (Python); caption "Small hardened Rust gateway,
   rich Python brain."
5. **DevOps tools screenshot** — the agent running a shell/Git/Docker
   tool step; caption "Agents that can actually operate things."
6. **Telegram bot screenshot** — ARGO answering inside a Telegram chat;
   caption "Connect a Telegram bot in minutes."
7. **Docker Compose screenshot** — `docker compose up` with argo-brain +
   argo-core healthy; caption "Self-host with two containers."
8. **Status / honesty card** — a small table: "Working today" vs "On the
   roadmap"; caption "Alpha approaching GA — we tell you what's done."

Asset notes:
- Keep one consistent dark theme across all cards.
- Real terminal screenshots, not mockups, wherever possible.
- GIFs under ~3 MB so they load fast.
