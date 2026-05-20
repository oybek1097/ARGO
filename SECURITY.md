# Security Policy

ARGO Agent is an open-source AI agent platform (Rust gateway + Python brain).
Because an ARGO deployment executes tools, runs shell commands in sandboxes,
holds credentials and processes untrusted input from chat channels, security
is treated as a first-class concern. This document explains which versions
receive security fixes, how to report a vulnerability, and what to expect
afterwards.

> Project status: **alpha approaching GA**. ARGO has undergone an internal
> security review (see [`docs/security/audit-sprint10.md`](docs/security/audit-sprint10.md)).
> A formal third-party audit and penetration test is on the roadmap but has
> **not yet been performed**. Deploy accordingly.

## Supported versions

Security fixes are provided for the latest minor release on the `3.x` line.
Pre-release `0.x` tags are development snapshots and receive fixes only on
the current `main` branch.

| Version    | Supported          |
|------------|--------------------|
| `3.x` (latest minor) | Yes — security fixes |
| `3.x` (older minors) | Best-effort, upgrade recommended |
| `0.x` pre-release    | `main` branch only |
| `< 3.0`              | No |

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Report privately, via either channel:

- **Email:** `akbarshohanvarbekov@gmail.com` — use the subject prefix
  `[ARGO SECURITY]`. PGP-encrypted mail is welcome; request the key in a
  first contact message if needed.
- **GitHub Security Advisory:** use the *"Report a vulnerability"* button
  under the repository **Security** tab (private advisory).

Please include, where possible:

- A description of the issue and its security impact.
- The affected component (`argo-core`, `argo-brain`, a channel, a tool, a
  deployment artifact) and version / commit hash.
- Reproduction steps or a proof-of-concept.
- Your assessment of severity and any suggested remediation.

We support **responsible / coordinated disclosure**. Please give us a
reasonable window to ship a fix before any public disclosure.

## Disclosure timeline

We aim to meet the following targets from the time a report is received:

| Stage | Target |
|---|---|
| Acknowledge receipt | within **3 business days** |
| Initial triage & severity assessment | within **7 business days** |
| Fix or mitigation for Critical / High (P0/P1) | within **30 days** |
| Fix or mitigation for Medium / Low (P2/P3) | within **90 days** |
| Public disclosure & advisory | coordinated with reporter, normally after a fixed release is available |

If a fix is expected to take longer than the targets above, we will keep
the reporter informed of progress. With reporter consent, credit is given
in the release notes and the security advisory.

## Scope

**In scope**

- The `argo-core` Rust gateway and its HTTP / WebSocket APIs.
- The `argo-brain` Python runtime: agent loop, tools, skills, memory.
- Built-in channels (Telegram, Discord, Slack, Matrix, email, webhooks, etc.).
- The tool sandbox, terminal backends and the audit log.
- Authentication, RBAC, secrets handling and redaction.
- Official deployment artifacts (`Dockerfile`, `docker-compose.yml`, Helm chart).

**Out of scope**

- Vulnerabilities in third-party dependencies that have no exploitable path
  in ARGO (report those upstream; we still want to know).
- Issues that require an already-compromised host or pre-existing root/admin
  access.
- Social engineering of maintainers or users.
- Findings against a misconfigured deployment that contradicts the
  [hardening checklist](docs/security/hardening-checklist.md) (e.g. the
  admin API exposed to the public internet without auth).
- Self-inflicted denial of service (e.g. running an unbounded prompt loop
  with quotas disabled).
- Best-practice or "informational" reports with no demonstrable impact.

## Security model summary

ARGO's security model is documented in the technical specification:

- **Section 4.14 — Security & Sandbox:** threat table, sandbox modes
  (`strict` / `dev` / `paranoid` / `airgapped`), compliance modules.
- **Section 10 — Security model:** authentication (API key, JWT, OAuth 2.0,
  mTLS), RBAC roles and per-tool permissions, secrets management (Vault and
  alternatives), append-only signed audit log.
- **Section 11 — Quality:** the security scanning gate (`bandit`, `semgrep`,
  `cargo-audit`, `trivy`) that runs on every pull request.

Key controls in brief:

- **Trust boundaries** between channel → `argo-core` → `argo-brain` →
  tools/sandbox; see [`docs/security/threat-model.md`](docs/security/threat-model.md).
- **Tool execution** is mediated by plugin `pre_tool` veto hooks,
  dangerous-tool confirmation and per-tool RBAC.
- **Sandboxing** of shell and code execution via container / microVM
  backends with seccomp, user namespaces and a read-only rootfs.
- **Secrets** are referenced from a secrets manager (Vault by default), not
  stored in plaintext environment variables.
- **PII redaction** is applied to tool output and logs
  (`argo_brain/security/redaction.py`).
- **Auditing** is append-only and SQLite-backed
  (`argo_brain/security/audit.py`), exportable to a SIEM.

Operators should also follow the
[hardening checklist](docs/security/hardening-checklist.md) and run the
self-audit script at [`scripts/security-audit.sh`](scripts/security-audit.sh).
