# ARGO Agent v3.0

> Ochiq manbali, ko'p tilli AI agent platformasi — **Rust gateway + Python brain**.
> Markaziy Osiyo tillari va DevOps uchun maxsus optimallashtirilgan.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Status](https://img.shields.io/badge/status-alpha-orange)
![Tests](https://img.shields.io/badge/tests-73%20passing-brightgreen)

ARGO — Hermes Agent ekotizimiga feature-parity'ni maqsad qilgan, undan tashqari
Markaziy Osiyo va sovereign deployment niche'lariga exclusive funksiyalar beruvchi
agent platformasi. To'liq texnik spetsifikatsiya: [`ARGO_AGENT_v3_Texnik_Zadacha.md`](ARGO_AGENT_v3_Texnik_Zadacha.md).

---

## Tez boshlash

```bash
# Bir buyruqli o'rnatish (toolchain tekshiradi, argo-core quradi, sozlaydi)
./scripts/setup.sh

# yoki qo'lda:
cd argo-brain
python3 -m argo_brain setup      # interaktiv sozlash sehrgari
python3 -m argo_brain doctor     # diagnostika
python3 -m argo_brain chat       # interaktiv suhbat (API kalitsiz)
python3 -m argo_brain serve      # HTTP gateway
python3 -m argo_brain telegram   # Telegram bot
```

`argo-brain` yadrosi **faqat Python stdlib** bilan ishlaydi — o'rnatishsiz darhol
sinab ko'rsa bo'ladi.

## Repozitoriya tuzilishi

```
ARGO/
├── argo-core/          # Rust gateway (Axum + Tokio) — HTTP, IPC, L0 memory, metrics
├── argo-brain/         # Python brain — agent loop, tools, memory, channels, plugins
├── scripts/setup.sh    # bir buyruqli o'rnatuvchi
├── ARGO_AGENT_v3_Texnik_Zadacha.md   # to'liq texnik zadacha (TZ)
├── ARGO_TZ_Executive_Summary.md      # 1-sahifalik xulosa
├── ARGO_TZ_Hermes_Parity_Matrix.md   # Hermes ↔ ARGO funksiya jadvali
└── LICENSE             # MIT
```

## Hozirgi holat (alpha)

ARGO TZ bo'yicha **12 sprintlik** loyiha. Quyidagilar bajarilgan:

| Komponent | Holat |
|---|---|
| `argo-core` — Rust gateway (`/api/health`, `/api/chat`, `/api/history`, `/metrics`) | ✅ ishlaydi (1.3 MB binary) |
| `argo-brain` — agent loop (Plan→Execute), 13 built-in tool | ✅ ishlaydi |
| Xotira — L0 (deque) + L1 (SQLite + FTS5) | ✅ |
| LLM provayderlar — Mock + Anthropic | ✅ |
| Skills, Plugin (5-hook), Kanban multi-agent, Cron | ✅ |
| Til aniqlash — uz/ru/kk/ky/tg/en | ✅ |
| Telegram kanali | ✅ |
| IPC (argo-core ↔ argo-brain) | ✅ |
| Setup sehrgari + doctor | ✅ |
| Qolgan 29+ kanal, TUI, web dashboard, MCP, 100+ tool | 🔜 keyingi sprintlar |

Yo'l xaritasi: TZ 13-bo'lim. O'zgarishlar tarixi: [`CHANGELOG.md`](CHANGELOG.md).

## Arxitektura

```
Foydalanuvchi ─► Kanal adapter ─► argo-core (Rust) ──IPC──► argo-brain (Python)
                                  HTTP/WS gateway          agent loop + tools
```

`argo-core` — kichik, xavfsiz tashqi yuz; `argo-brain` — boy AI mantiq.
Ikkisi Unix socketda satr-cheklangan JSON orqali bog'lanadi (TZ 3.4).

## Hissa qo'shish

[`CONTRIBUTING.md`](CONTRIBUTING.md) ga qarang.

## Litsenziya

MIT — [`LICENSE`](LICENSE).
