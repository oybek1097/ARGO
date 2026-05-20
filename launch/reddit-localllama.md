# r/LocalLLaMA — launch post

## Title

> ARGO: an open-source, self-hosted AI agent — runs offline, MIT, and the brain has zero pip dependencies

Alternates:
- I built a self-hosted AI agent with an airgapped mode and a Rust gateway (MIT)
- Self-hosted agent platform: bring your own local model, no telemetry, MIT

## Flair

`Other` / `Resources` (whichever the subreddit currently uses for project shares)

## Body

Posting here because this subreddit cares about exactly the things ARGO
was built around: running things yourself, keeping your data local, and
not depending on someone else's cloud.

**What it is.** ARGO is an open-source AI agent platform. Two parts: a
small Rust gateway (`argo-core`) that handles the HTTP/network side, and
a Python brain (`argo-brain`) that runs the agent loop, tools, and
memory. MIT licensed.

**Up front: it's alpha.** It's heading toward a v3.0 GA. 84 tests pass,
13 built-in tools, the core loop works. Plenty is still roadmap. I'd
rather you know that than be annoyed later.

**Why it might interest this sub specifically:**

- **Self-hosted by default.** No account, no sign-up, no telemetry
  calling home. You run the whole thing on your own box.
- **Airgapped mode.** It can run with no outbound internet access at
  all. If your setup is a sealed network, that's a supported mode, not a
  hack.
- **Bring your own model.** The LLM is a pluggable provider. There's a
  built-in mock provider so you can exercise the agent loop with zero
  network, and a real provider interface to wire up whatever you serve
  locally. (More provider adapters — including local-runtime-friendly
  ones — are on the roadmap; today the shipped real provider is
  Anthropic, plus the mock.)
- **The Python brain runs on the standard library only.** No
  `pip install` to get going. `python3 -m argo_brain chat` and you have
  an interactive agent session. That also means a tiny dependency
  surface to audit if you care about supply chain.
- **Rust gateway is the only network-facing part** and it's small by
  design — the idea is a hardened, minimal external face with the messy
  AI logic kept behind it.
- **Memory is local.** L0 is an in-process deque; L1 is SQLite with
  FTS5 for recall. Your conversation history is a file on your disk,
  not a row in someone's database.

**The other angle:** ARGO has native support for Central Asian languages
— Uzbek (Latin + Cyrillic), Russian, Kazakh, Kyrgyz, Tajik, plus
English. Language detection and reply routing are built in. Not the main
reason to post here, but if you're running local models for non-English
users it may matter to you.

**Honest scope.** What works today: the Rust gateway, the Plan→Execute
agent loop, 13 tools (shell/files/Git/Docker/kubectl among them), L0/L1
memory, Telegram + Slack + webhook channels, a setup wizard and a
`doctor` diagnostic. What's still roadmap: many more channels, a web
dashboard, a much larger tool/skill library, more provider adapters.
It's a 12-sprint project and the full plan is in the repo.

**Try it (no install):**

```bash
git clone <repo>
cd ARGO/argo-brain
python3 -m argo_brain chat
```

That runs against the local mock model — no API key, no network.

Repo + full spec: <link>

Feedback I'd actually like from this sub: how the provider interface
should look so it's painless to point at a local runtime, and whether
the airgapped mode misses anything. And native-speaker corrections for
any of the languages. Tear it apart.
