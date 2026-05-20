# Hacker News — "Show HN" post

## Title

> Show HN: ARGO – a self-hosted AI agent with native Central Asian language support

Keep the title plain. No superlatives, no emoji. Alternates:

- Show HN: ARGO – self-hosted AI agent, Rust gateway + Python brain (MIT)
- Show HN: ARGO – an AI agent that runs on the Python stdlib

## Body

ARGO is an open-source AI agent platform. It's two parts: a small Rust
gateway (`argo-core`, Axum + Tokio) that is the external HTTP face, and a
Python brain (`argo-brain`) that runs the agent loop and tools. They talk
over a Unix socket with line-delimited JSON.

I'll be straight about the state of it: ARGO is alpha, heading toward a
v3.0 GA. It works and it's useful, but it is not finished. There are
84 tests passing, 13 built-in tools, and a fair amount of the roadmap is
still roadmap. I'd rather say that here than have you find out by
surprise.

Two things make it different from the other agent frameworks:

1. Central Asian languages are first-class. Most agent frameworks assume
   English plus a US-hosted API. ARGO does language detection and
   response routing for Uzbek (Latin and Cyrillic), Russian, Kazakh,
   Kyrgyz, Tajik, and English. This is the niche we actually care about —
   there are ~250M people in the CIS/Central Asia region and nobody is
   serving it well for this kind of tooling.

2. It's genuinely easy to try and self-hosted by default. The Python
   brain runs on the standard library — no `pip install` needed to start
   a conversation. `python3 -m argo_brain chat` gives you an interactive
   session against a local mock model, so you can see how the agent loop
   behaves before wiring up a real LLM (Anthropic is supported today;
   more providers are on the roadmap). There's an airgapped mode for
   environments with no outbound network.

The agent loop is a plain Plan→Execute loop. Memory is two tiers right
now: an in-process deque (L0) and SQLite with FTS5 for recall (L1).
DevOps tooling is built in — shell, files, Git, Docker, kubectl — because
a lot of what we want agents to do is operate infrastructure. Channels:
Telegram, Slack, and a generic webhook today.

Why Rust + Python instead of one language: the gateway is the part that
faces the network and needs to be small and hardened, so that's Rust.
The brain is where the messy AI logic lives and iteration speed matters,
so that's Python. The split also means the brain has zero third-party
runtime dependencies.

It's MIT licensed. The repo has the full technical spec and the
12-sprint roadmap if you want to see where it's going. I'd genuinely
value feedback on the architecture, and corrections from native speakers
of any of the supported languages.

Repo: <link>
Quick start: <link>

## Anticipated FAQ (have these ready as comment replies)

**"Isn't this just a wrapper around an LLM API?"**
The LLM is one pluggable component. The project is the agent loop,
tooling, memory tiers, channel adapters, the Rust gateway, and the
language layer. You can run the `chat` command against a local mock
model with no API at all and watch the loop work. Provider choice is
yours.

**"Why two languages? Sounds like accidental complexity."**
It's a deliberate split, not an accident. The gateway needs to be small,
fast, and hardened at the network edge — Rust. The brain needs fast
iteration on fuzzy logic — Python. The IPC boundary between them is a
single Unix socket with line-delimited JSON; it's simple to reason
about. The Python side has no third-party runtime deps as a result.

**"How is the Central Asian language support actually better?"**
It's not a translation shim. Language detection covers uz/ru/kk/ky/tg/en
and the response is routed back in the detected language. Uzbek is
handled in both Latin and Cyrillic script. We're explicitly asking
native speakers to file corrections — that's part of why we're launching
now rather than later.

**"Performance numbers?"**
The spec lists performance targets for the Rust gateway (low idle RAM,
fast cold start, sub-millisecond IPC). Those are targets, and we present
them as targets — not measured marketing claims. We are not going to
post a "100,000x" number; the spec itself disowns that style. Real
benchmarks will land with GA.

**"Is it production-ready?"**
No. It's alpha. It is suitable for trying out, building on, and
contributing to. It is not yet something we'd tell you to put in front
of customers unattended. The roadmap to GA is in the repo.

**"How do I run it without sending data anywhere?"**
Self-host it; that's the default mode. The brain runs locally. There's
an airgapped mode for no-outbound-internet environments. If you point it
at a hosted LLM, that traffic goes to that provider — but the agent,
memory, and tooling all run on your hardware.

**"What's the license / can I use it commercially?"**
MIT. Yes.

**"Comparison to <other agent framework>?"**
Honestly, for pure English use cases on a US cloud, mature frameworks
will be ahead of us today — we're alpha. Where ARGO is meant to win is
the specific combination of self-hosted/sovereign deployment, Central
Asian languages, and built-in DevOps tooling. If that combination isn't
your use case, one of the bigger projects may serve you better, and
that's fine.
