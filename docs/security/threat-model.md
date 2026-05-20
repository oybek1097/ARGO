# ARGO Agent — Threat Model

This document describes the threat model for an ARGO Agent deployment. It
complements section 4.14 ("Security & Sandbox") and section 10 ("Security
model") of the
[technical specification](../../ARGO_AGENT_v3_Technical_Specification.md).

The model uses a STRIDE-style enumeration (Spoofing, Tampering, Repudiation,
Information disclosure, Denial of service, Elevation of privilege) applied
per trust boundary.

> Status: internal threat model, maintained alongside the codebase. It will
> be revised after the planned external audit.

## 1. System overview

ARGO has two processes plus pluggable channels and a tool sandbox:

```
            untrusted input
                  |
  +---------------v----------------+
  | Channels (Telegram, Discord,   |   Boundary A
  | Slack, Matrix, email, SMS,     |
  | webhooks, IRC, ...)            |
  +---------------+----------------+
                  | HTTP / WS
  +---------------v----------------+
  | argo-core (Rust gateway)       |   Boundary B
  | auth, rate limit, routing      |
  +---------------+----------------+
                  | internal IPC (UNIX socket / loopback)
  +---------------v----------------+
  | argo-brain (Python runtime)    |   Boundary C
  | agent loop, skills, memory     |
  +---------------+----------------+
                  | tool dispatch
  +---------------v----------------+
  | Tools / sandbox (containers,   |   Boundary D
  | microVMs, terminal backends)   |
  +--------------------------------+
```

## 2. Assets

| Asset | Why it matters |
|---|---|
| User conversation content & memory (L1/L2/L3) | Confidential; may contain PII and business data |
| Credentials & secrets (LLM API keys, OAuth tokens, channel tokens) | Compromise enables impersonation and cost abuse |
| Tool capability (shell, file, DevOps, network) | Tools can read/write the host and reach internal networks |
| Audit log | Integrity is required for incident response & compliance |
| Skill definitions & prompts | Tampering changes agent behaviour silently |
| Host & sandbox runtime | Container escape gives host control |
| Service availability | Outage affects every connected channel and user |
| Multi-tenant isolation (`user_id` / `tenant_id` scoping) | Cross-tenant leakage is a serious data-protection breach |

## 3. Trust boundaries

| ID | Boundary | Inside trust | Outside trust |
|----|----------|--------------|----------------|
| A | Channel ingress | Channel adapter code | Remote chat users, webhook callers |
| B | `argo-core` gateway | Authenticated, rate-limited, routed requests | Raw network input from channels / clients |
| C | core ↔ brain IPC | `argo-brain` runtime | Any process able to reach the IPC socket |
| D | tool / sandbox | The agent runtime requesting a tool | Tool side effects, sandbox-executed code |

## 4. Attacker profiles

| Profile | Capability | Goal |
|---|---|---|
| Unauthenticated remote attacker | Can reach exposed ports / webhooks | Auth bypass, DoS, SSRF |
| Malicious or compromised chat user | Holds a valid channel identity | Run privileged tools, exfiltrate data, prompt injection |
| Malicious content author | Controls a web page, file, email or skill the agent ingests | Indirect prompt injection, data exfiltration |
| Curious / hostile co-tenant | Valid account in a multi-tenant deployment | Read another tenant's data |
| Local low-privilege process | Code execution on the host as a non-root user | Reach the IPC socket, read secrets, escalate |
| Supply-chain attacker | Can publish a dependency or a Hub package | Code execution inside the runtime |
| Malicious insider | Operator-level access | Tamper with audit log, exfiltrate secrets |

## 5. Threats and mitigations by boundary

### Boundary A — Channel ingress

| STRIDE | Threat | Mitigation |
|---|---|---|
| S | Forged sender / unauthorized channel user | Per-channel allowlists, default-reject for unknown users (WhatsApp/Telegram), Discord guild-scoped role allowlists |
| S | Forged inbound webhook | HMAC signature verification, shared-secret path tokens, source-IP allowlist |
| T | Tampered message payload in transit | TLS for all channel transports; verified webhook signatures |
| I | Indirect prompt injection via page/email/file content | Prompt-injection scanner on assembled skills/content, output treated as data not instructions, dangerous-tool confirmation |
| D | Flood of messages / webhook calls | Per-user and per-channel rate limits, max-iteration cap, quotas |
| E | Stranger escalates to privileged actions | RBAC: chat users default to the `user` role; privileged tools require explicit roles |

### Boundary B — `argo-core` gateway

| STRIDE | Threat | Mitigation |
|---|---|---|
| S | Stolen / brute-forced API key or JWT | API keys hashed at rest, JWT expiry & signature checks, mTLS for service-to-service |
| T | Request smuggling / parameter tampering | Strict request schema validation, OpenAPI contract tests, schemathesis fuzzing in CI |
| R | Action without an attributable record | Append-only signed audit log keyed by `user_id` |
| I | Verbose errors leaking internals / stack traces | Generic error responses to clients, detail only in server logs |
| I | Secret leakage in logs | PII/secret redaction pipeline applied to logs and tool output |
| D | Connection / request floods | Connection caps, per-user rate limits, body-size limits, timeouts |
| E | Auth bypass on admin endpoints | Admin API bound to loopback by default, RBAC enforced server-side |

### Boundary C — core ↔ brain IPC

| STRIDE | Threat | Mitigation |
|---|---|---|
| S | Rogue local process impersonates `argo-core` | UNIX-domain socket with `0600` ownership/permissions; loopback-only if TCP; optional shared token |
| T | Tampering with in-flight tool requests/results | Length-prefixed framed messages with schema validation; loopback / UNIX socket only |
| R | Brain actions not linked to the originating request | Request correlation IDs propagated into the audit log |
| I | Eavesdropping on IPC traffic | UNIX socket (no network exposure) or loopback; never bound to `0.0.0.0` |
| D | Brain overwhelmed by queued requests | Bounded work queue, backpressure, per-request timeouts |
| E | Crafted IPC message triggers unintended tool call | Tool calls re-validated in the brain; `pre_tool` plugin veto; RBAC re-checked |

### Boundary D — tools and sandbox

| STRIDE | Threat | Mitigation |
|---|---|---|
| S | Tool argument injection (e.g. shell metacharacters) | Argument lists not shell strings, allowlists, no `shell=True`, escaping |
| T | Path traversal in file tools / archive extraction | Path canonicalization confined to a workspace root; archive members validated before extraction |
| R | Tool side effects without a trace | Every tool invocation recorded in the audit log |
| I | Tool output exfiltrates secrets / cross-tenant data | Output redaction, strict `user_id` scoping in all queries, no unfiltered `SELECT *` |
| I | SSRF from browser / HTTP tools to internal services | Block lists for cloud-metadata and private/loopback IP ranges; DNS-rebind resistant resolution |
| D | Resource exhaustion by runaway tool | Sandbox CPU/memory/time limits, per-user quotas, max-iteration cap |
| E | Container / sandbox escape | seccomp-bpf profile, user namespaces, read-only rootfs, dropped capabilities, no host network |

## 6. Residual risk

- **No external audit yet.** This model is maintainer-authored; a formal
  third-party penetration test remains a roadmap item.
- **LLM behaviour is probabilistic.** Prompt-injection defences reduce but
  do not eliminate the risk of an agent being manipulated; keep destructive
  tools behind confirmation and least-privilege RBAC.
- **Sandbox strength depends on the backend.** `local` execution provides
  the weakest isolation; container/microVM backends are strongly
  recommended for any deployment handling untrusted input.
- **Operator misconfiguration** is the most likely cause of a breach;
  follow the [hardening checklist](hardening-checklist.md).

## 7. Related documents

- [`SECURITY.md`](../../SECURITY.md) — reporting and disclosure policy.
- [`hardening-checklist.md`](hardening-checklist.md) — operator hardening.
- [`audit-sprint10.md`](audit-sprint10.md) — Sprint 10 internal review.
- Technical specification §4.14, §10, §11.
