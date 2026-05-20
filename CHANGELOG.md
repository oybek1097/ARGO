# Changelog

ARGO Agent loyihasining barcha sezilarli o'zgarishlari shu faylda qayd etiladi.

Format [Keep a Changelog](https://keepachangelog.com/) ga, versiyalash
[Semantic Versioning](https://semver.org/) ga asoslangan.

## [Unreleased]

### Added — argo-brain (Python brain)
- Agent yadrosi: Plan → Execute loop (TZ 4.2)
- Xotira: L0 ishchi (deque) + L1 doimiy (SQLite + FTS5)
- Tool tizimi: `Tool` ABC, registr, 13 ta built-in tool
  (current_time, calculate, read/write/find/grep file, http_get/post,
  web_fetch, shell_exec, list_dir, memory_search/remember)
- LLM provayderlar: `MockProvider` (kalitsiz) + haqiqiy `AnthropicProvider`
- Skills: agentskills.io-mos markdown loader + trigger moslash
- Plugin tizimi: 5-hook API + registr (pre/post tool, on_response)
- Multi-agent: doimiy SQLite Kanban (claim/complete/retry/block lifecycle)
- Cron: scheduler + tabiiy til schedule parser
- Til aniqlash: uz/ru/kk/ky/tg/en heuristikasi
- Kanallar: `Channel` ABC + Telegram (long polling), generic webhook va
  Slack (Events API) adapterlari; `/webhook/<platform>` gateway marshruti
- HTTP gateway, IPC server (Unix socket)
- CLI: `setup`, `doctor`, `chat`, `serve`, `ipc`, `telegram`, `selftest`
- 84 ta unit test (stdlib `unittest`)

### Added — argo-core (Rust gateway)
- Axum + Tokio HTTP gateway: `/api/health`, `/api/version`, `/api/chat`,
  `/api/history/:uid`, `/metrics`
- L0 ishchi xotira (DashMap, foydalanuvchi boshiga ring buffer)
- argo-brain bilan Unix socket IPC mijozi
- Prometheus metrikalar
- Release binary: 1.3 MB

### Added — infratuzilma
- `scripts/setup.sh` — bir buyruqli o'rnatuvchi
- README, CHANGELOG, CONTRIBUTING, .gitignore

[Unreleased]: https://github.com/oybek1097/ARGO
