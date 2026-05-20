# ARGO Agent v3.0 — Texnik Zadacha to'plami

**Sana:** May 2026 · **Versiya:** 1.0 · **Litsenziya:** MIT

Bu to'plamda ARGO Agent v3.0 ni 0 dan yaratish uchun barcha texnik hujjatlar mavjud. Hujjatlar Hermes Agent v0.14.0 "Foundation Release" tahliliga asoslangan va GitHub'da rasmiy loyiha hujjati sifatida nashr etish uchun tayyor.

## Hujjatlar tarkibi

| Fayl | Maqsad | Hajm | Auditoriya |
|---|---|---|---|
| **ARGO_TZ_Executive_Summary.md** | 1-sahifalik qisqacha xulosa | 1 sahifa | Yuqori menejment, investorlar |
| **ARGO_AGENT_v3_Texnik_Zadacha.md** | To'liq texnik spetsifikatsiya (asosiy hujjat) | ~100 sahifa, 10K so'z | Muhandislik jamoasi |
| **ARGO_TZ_Hermes_Parity_Matrix.md** | Hermes ↔ ARGO funksiya-funksiya jadvali | ~70 sahifa, 9K so'z, 470+ qator | Texnik lead, planner |
| **README.md** | Bu fayl — navigatsiya | — | — |

## Qaysi tartibda o'qish kerak

1. **Birinchi marta tanishish:** `ARGO_TZ_Executive_Summary.md` (5 daqiqa)
2. **Loyihani boshlashdan oldin:** `ARGO_AGENT_v3_Texnik_Zadacha.md` — 0-bo'lim (Annotation) + 13-bo'lim (Sprint Roadmap)
3. **Komponent ishlab chiqishdan oldin:** `ARGO_AGENT_v3_Texnik_Zadacha.md` — tegishli 4.X bo'limi
4. **Hermes bilan taqqoslash kerak:** `ARGO_TZ_Hermes_Parity_Matrix.md`
5. **Risk va ochiq savollar:** Asosiy hujjat 14-15 bo'limlari

## Asosiy ko'rsatkichlar (qisqa)

ARGO v3.0 maqsadlari Hermes v0.14.0 ga nisbatan:

| Performance | Improvement |
|---|---|
| Idle RAM | **20x kamroq** (400 MB → <20 MB) |
| Cold start | **10x tezroq** (1.5s → <150ms) |
| Tool dispatch | **10x tezroq** (10ms → <1ms) |
| WS connections | **10x ko'proq** (5k → 50k+) |
| Memory throughput | **20x ko'proq** (500/s → 10k/s) |

| Funksiyalar | Hermes | ARGO | ARGO exclusive |
|---|---|---|---|
| Built-in tools | 70 | 120+ | DevOps 25 ta |
| Messaging platforms | 22 | 30+ | CIS 8 ta |
| LLM providers | 26 | 32+ | RU/CN 6 ta |
| Tillar (native agent) | 7 | 7+ | Markaziy Osiyo 5 ta |
| Terminal backends | 7 | 12 | K8s/Lima/Firecracker |
| **JAMI funksiyalar** | **~358** | **~474** | **~110 yangi** |

## Loyiha tuzilishi (kelajakdagi repo)

```
argo-agent/
├── argo-core/              # Rust gateway (~15K satr)
│   ├── src/
│   ├── Cargo.toml
│   └── README.md
├── argo-brain/             # Python brain (~50K satr)
│   ├── argo_brain/
│   ├── pyproject.toml
│   └── README.md
├── argo-cli/               # Rust CLI binary (~5K satr)
├── argo-tui/               # React/Ink TUI (~10K satr)
├── argo-web/               # Next.js dashboard (~15K satr)
├── argo-mcp-tools/         # Bundled MCP servers
├── argo-skills/            # 150+ bundled markdown skills
├── argo-docs/              # Docusaurus site
├── helm/                   # Kubernetes Helm chart
├── docker-compose.yml      # Single-node deployment
├── monitoring/             # Prometheus + Grafana
├── scripts/                # Install, migrate, doctor
├── tests/                  # Integration + E2E
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE                 # MIT
└── README.md
```

## Sprint roadmap (qisqacha)

| Sprint | Hafta | Asosiy yetkazib berish |
|---|---|---|
| 0 | 1-2 | v2.0 bug fixlar, CI |
| 1 | 3-4 | Rust gateway |
| 2 | 5-6 | Python brain v1 |
| 3 | 7-8 | Skills + Curator |
| 4 | 9-10 | Tools I (40 ta) |
| 5 | 11-12 | Tools II DevOps (35 ta) |
| 6 | 13-14 | Channels I (6 ta core) |
| 7 | 15-16 | Channels II (24 ta extra) |
| 8 | 17-18 | Multi-agent + MCP |
| 9 | 19-20 | TUI + Web |
| 10 | 21-22 | Polish + security audit |
| 11 | 23-24 | Hub + marketplace |
| 12 | 25-26 | GA Launch |

## Litsenziya

Bu texnik zadacha **MIT litsenziyasi** ostida tarqatiladi. ARGO Agent loyihasining barcha kod va hujjatlari MIT ostida bo'ladi.

## Hissa qo'shish

PR'lar GitHub'da kutiladi. Ko'rib chiqish jarayoni:
1. Issue ochish va muhokama qilish
2. PR yuborish (2 reviewer approval kerak)
3. CI yashil bo'lishi shart
4. Signed-off-by trailer kerak

## Hermes Agent va ARGO

ARGO **Hermes Agent**ning **alternative emas, balki to'ldiruvchisi**. ARGO:
- ✅ Hermes skill'larini import qiladi (agentskills.io standart)
- ✅ Hermes MCP serverlariga ulanadi
- ✅ OpenAI proxy bir xil (kross-platforma)
- ✅ NousResearch va Hermes jamoasiga to'liq krediga ega

Bizning farqimiz — bu yerda nima yangi:
- 🆕 Rust core (performance + xavfsizlik)
- 🆕 Markaziy Osiyo tillari
- 🆕 DevOps stack
- 🆕 Sovereign compliance

---

*Hujjatlar ARGO Loyihasi tomonidan yaratildi · May 2026*
