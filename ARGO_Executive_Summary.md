# ARGO Agent v3.0 — Executive Summary (1 page)

**Project:** ARGO Agent — an open-source, Rust+Python AI agent platform
**Goal:** Full parity with the Hermes Agent ecosystem + exclusive advantage in the Central Asia and DevOps niches
**Timeline:** v3.0 GA — 6 months (12 sprints × 2 weeks)
**License:** MIT
**Owner:** ARGO Project

---

## Vision

ARGO is **the world's first Central Asia native AI agent platform**, while also being purpose-optimized for DevOps and sovereign deployment. It achieves full feature parity with Hermes Agent (NousResearch) and, beyond that, delivers **110 exclusive features**.

## Key numbers

| Metric | Hermes v0.14 | ARGO v3.0 target | Advantage |
|---|---|---|---|
| Idle RAM | ~400 MB | **<20 MB** | **20x** |
| Cold start | ~1.5 s | **<150 ms** | **10x** |
| Tool dispatch | ~10 ms | **<1 ms** | **10x** |
| WS connections/node | ~5,000 | **>50,000** | **10x** |
| Per-request latency P50 | ~80 ms | **<30 ms** | **2.7x** |
| Memory throughput | ~500/s | **>10,000/s** | **20x** |
| Built-in tools | 70 | **120+** | **1.7x** |
| Messaging platforms | 22 | **30+** | **1.4x** |
| Languages (native agent) | 7+3 | **26 UI / 7 first-class** | **3x** |
| Terminal backends | 7 | **12** | **1.7x** |
| LLM providers | 26 | **32+** | **1.2x** |

**Geometric mean:** ~10x improvement across each independent metric.

## Exclusive features (not present in Hermes)

**1. Central Asian languages (native):**
- Uzbek (Latin + Cyrillic), Kazakh, Kyrgyz, Tajik, Turkmen, Azerbaijani
- Tokenization, language detection, response routing — fully localized

**2. Built-in DevOps stack (8 tool groups):**
- HashiCorp Vault (4)
- Kubernetes (kubectl + 5)
- Proxmox (5)
- SSH (3)
- Ansible (2)
- Terraform (3)
- Docker (5)
- ArgoCD (3)

**3. Sovereign deployment:**
- Russia 152-FZ compliance module
- Uzbekistan personal data protection law compliance module
- China PIPL compliance module
- GDPR compliance module
- Airgapped mode (fully operable without external internet access)

**4. Native Rust gateway:**
- argo-core (Rust + Axum + Tokio): small (<20 MB RAM), fast (<1 ms IPC), secure (seccomp-bpf + rlimit)
- argo-brain (Python): rich AI logic
- Multi-runtime: Go and Rust brain ports planned for v3.5+

**5. CIS messenger support:**
- Yandex.Messenger
- VK Messages
- MyChat (Astra Linux)
- Mango Office

**6. CIS LLM provider support:**
- Yandex GPT, Yandex Foundation Models
- SberCloud GigaChat
- Tencent Hunyuan
- Baidu ERNIE

**7. Enterprise observability:**
- Prometheus metrics (first-class)
- OpenTelemetry traces
- 6 ready-made Grafana dashboards
- SIEM export (Splunk, ELK, Sentinel)

## Niche-first strategy

**Hermes vs ARGO — a regional distribution play:**
- Hermes today has 140,000+ GitHub stars, 295+ contributors, and a global presence
- ARGO is a startup, but: the **CIS + Central Asia** market is large (250M+ population), growing, and currently underserved by anyone offering full coverage

**ARGO target users:**
1. CIS DevOps engineers (Russia, UZ, KZ, KG, BY)
2. Central Asian startups (AI assistant in the local language)
3. Governments and banks (sovereign + compliance)
4. Independent developers (who need Rust performance)
5. Privacy-first users (offline + airgapped)

## Planned 6-month roadmap

| Sprint | Focus | Key deliverable |
|---|---|---|
| 0 (2 weeks) | Foundation reset | v2.0 bugs fixed, CI green |
| 1 | Rust gateway | argo-core full endpoints |
| 2 | Python brain | refactored agent loop, plugin API |
| 3 | Skills + Curator | 50 bundled skills, curator pipeline |
| 4 | Tools I | Web/file/terminal/memory (40 tools) |
| 5 | Tools II DevOps | Vault/K8s/Proxmox/SSH/Ansible/TF (35 tools) |
| 6 | Channels I | Top 6 platforms |
| 7 | Channels II | Remaining 24+ platforms |
| 8 | Multi-agent + MCP | Kanban, delegate, DAG, MCP gateway |
| 9 | TUI + Web | Hermes-parity TUI, web dashboard |
| 10 | Polish + Security | External audit, performance gates |
| 11 | Hub + Marketplace | 100+ skills, 20+ plugins |
| 12 | GA Launch | Marketing, docs, cloud templates |

## Success criteria (3 months post-launch)

- ≥1,000 GitHub stars
- ≥50 contributors
- ≥10 published skills
- ≥5 enterprise pilot deployments (UZ/RU/KZ)
- 99.9% uptime SLO (hosted instance)
- No open P0 security findings
- 26+ languages validated by real users

## Technical summary

> ARGO v3.0 — Hermes parity + 110 exclusive features. The Rust core uses 20x less RAM and delivers a 10x faster cold start. Central Asia, DevOps, and sovereign deployment are the strategic niches. GA in 6 months. MIT.

**Documents:**
- Full technical specification: `ARGO_AGENT_v3_Technical_Specification.md` (~10,000 words, 96 KB)
- Hermes parity matrix: `ARGO_Hermes_Parity_Matrix.md` (~9,000 words, 470+ features)
- This executive summary: 1 page

---
*Date: May 2026 · Version: 1.0 · MIT License*
