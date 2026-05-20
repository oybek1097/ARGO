# Sprint 10 — Internal Security Review

| | |
|---|---|
| Scope | `argo-core`, `argo-brain`, channels, tools/sandbox, deployment artifacts |
| Type | **Internal** maintainer-led review and code audit |
| Period | Sprint 10 (Polish, Performance, Security) |
| Methodology | Manual code review, `bandit` / `semgrep` / `cargo-audit` / `trivy` scans, threat-model walkthrough (see [`threat-model.md`](threat-model.md)) |
| External audit | **Not performed.** A third-party penetration test remains a roadmap item — see *Limitations* below. |

> **Honesty note.** This is an internal review carried out by the project
> maintainers, not an independent third-party audit. It is a genuine pass
> over the codebase against the threat model, but it carries the usual
> limitations of self-assessment. Findings and severities reflect the
> maintainers' judgement and the CVSS-style P0/P1/P2 scale used elsewhere
> in the spec.

## Summary

The review enumerated threats per trust boundary and produced **11**
findings: **3 Critical (P0)**, **6 High (P1)** and **2 Medium (P2)**. All
P0 and P1 findings have been closed; the two P2 findings are tracked for a
follow-up release. The Sprint 10 goal of **8+ P0/P1 closures** is met
(9 P0/P1 findings closed).

| Severity | Found | Closed | Open |
|---|---|---|---|
| P0 (Critical) | 3 | 3 | 0 |
| P1 (High) | 6 | 6 | 0 |
| P2 (Medium) | 2 | 0 | 2 |
| **Total** | **11** | **9** | **2** |

## Severity scale

| Level | Meaning |
|---|---|
| P0 | Critical — remote code execution, auth bypass, secret disclosure, sandbox escape |
| P1 | High — privilege escalation, data exfiltration, traversal, SSRF |
| P2 | Medium — defence-in-depth gap, hardening shortfall, info leak with limited impact |

## Findings

| ID | Severity | Title | Description | Fix | Status |
|----|----------|-------|-------------|-----|--------|
| ARGO-S10-001 | P0 | Tool-call argument injection in `shell_exec` | Shell command arguments assembled from LLM/tool output were passed to a string-interpreted shell, allowing metacharacter injection (`;`, `$()`, backticks) that broke out of the intended command. | Switched all command execution to argument-vector form (no `shell=True` / no string interpolation). Arguments are passed as a list to the sandbox backend; a parser rejects shell metacharacters in fields that must be literal. Added regression tests with injection payloads. | Closed |
| ARGO-S10-002 | P0 | IPC socket world-accessible | The core ↔ brain UNIX-domain socket was created with default umask permissions, letting any local process on the host send framed tool requests to `argo-brain`. | Socket is now created with an explicit `0600` mode under a directory owned by the service user; the brain verifies peer credentials (`SO_PEERCRED`) and an optional shared token before processing frames. TCP fallback binds to loopback only. | Closed |
| ARGO-S10-003 | P0 | Path traversal in file tools | `read_file` / `write_file` joined a caller-supplied path onto the workspace root without canonicalization, so `../../etc/passwd` (and absolute paths) escaped the workspace. | All file tools canonicalize the resolved path (`realpath`) and reject any result that is not contained within the configured workspace root. Symlink targets are re-checked after resolution. Tests cover `..`, absolute paths and symlink escapes. | Closed |
| ARGO-S10-004 | P1 | Secret leakage in logs and tool output | API keys, bearer tokens and `vault://` resolved values appeared verbatim in debug logs and in tool result payloads returned to channels. | Extended the redaction pipeline (`argo_brain/security/redaction.py`) with token/secret patterns (bearer tokens, AWS-style keys, generic high-entropy `KEY=value` pairs) and applied it to the log formatter and the tool-result path, not only PII. Secret values are masked before any sink. | Closed |
| ARGO-S10-005 | P1 | Indirect prompt injection via tool output | Content fetched by the browser/HTTP tools was concatenated into the model context as if trusted, so a hostile page could issue instructions (e.g. "call `shell_exec`...") that the agent followed. | Tool output is now wrapped in an explicit untrusted-content delimiter and the system prompt instructs the model to treat it as data. The prompt-injection scanner runs over fetched content, and dangerous tools still require confirmation, so a successful injection cannot silently trigger a destructive action. | Closed |
| ARGO-S10-006 | P1 | Missing rate limit on chat and webhook endpoints | Chat and inbound webhook endpoints had no per-user/per-channel rate limit, allowing message floods to exhaust LLM quota and CPU (DoS / cost-abuse). | Added a token-bucket rate limiter at the gateway, keyed by `user_id` and channel, plus a global connection cap and per-request body-size limit. The agent loop max-iteration cap was confirmed enforced. Limits are configurable. | Closed |
| ARGO-S10-007 | P1 | Unverified inbound webhook input | Webhook channels accepted any POST body and did not verify provider signatures, so an attacker who learned an endpoint URL could inject messages as arbitrary users. | Inbound webhooks now require HMAC signature verification against the channel's configured secret (constant-time comparison), an optional source-IP allowlist, and strict JSON schema validation before the payload reaches the agent. Unsigned requests are rejected with `401`. | Closed |
| ARGO-S10-008 | P1 | SSRF via browser / HTTP tools | The web tools followed any URL, including `http://169.254.169.254/` (cloud metadata) and private/loopback ranges, exposing internal services and credentials. | Added a destination filter that resolves the host and blocks cloud-metadata IPs and RFC 1918 / loopback / link-local ranges. Resolution is re-checked after redirects to resist DNS rebinding. An allowlist mode is available for `paranoid`/`airgapped` deployments. | Closed |
| ARGO-S10-009 | P1 | Verbose error responses leak internals | Unhandled exceptions returned stack traces and internal file paths to channel clients, aiding reconnaissance. | Client-facing errors are now generic with a correlation ID; full detail is written only to the server-side log and audit trail. Applied uniformly across `argo-core` and `argo-brain` error handlers. | Closed |
| ARGO-S10-010 | P2 | Archive extraction path traversal (defence-in-depth) | A general archive-extraction helper could in principle write members outside the target directory (`zip`/`tar` slip). The Hub package format already validates members on install, so no exploitable path was found — this is a hardening gap in the generic helper. | The shared extraction helper now validates every member path against the destination root and rejects absolute paths, `..` components and symlink members before writing. Brings the generic helper to parity with the package installer. | Closed |
| ARGO-S10-011 | P2 | Audit log not signed or shipped off-host by default | The audit log is append-only but, by default, unsigned and stored only on the local host, so a host compromise could tamper with or erase incident evidence. | Tracked for a follow-up release: add optional record signing (HMAC chain) and document/enable SIEM export (Fluent Bit) in the default deployment. Operators can already ship logs off-host per the [hardening checklist](hardening-checklist.md). | Open (tracked) |

## Verification

- Regression tests were added for each closed finding (argument injection,
  path traversal, symlink escape, webhook signature failure, SSRF block
  list, archive slip). The existing `argo-brain` unit suite stays green.
- `bandit`, `semgrep`, `cargo-audit` and `trivy` were run via
  [`scripts/security-audit.sh`](../../scripts/security-audit.sh); no
  unresolved High/Critical findings remain in scanner output.
- The threat model in [`threat-model.md`](threat-model.md) was walked
  boundary-by-boundary to confirm each mitigation has a corresponding
  control or finding.

## Limitations

- This is a **self-assessment**, not an independent audit. Self-review is
  subject to blind spots; an external penetration test is expected to find
  additional issues.
- Coverage is **code- and configuration-centric**. It did not include a
  full deployed-environment penetration test, fuzzing campaign or
  red-team exercise.
- LLM/agent-behaviour risks (prompt injection) are mitigated, not
  eliminated — they are inherent to LLM-driven systems.

## Roadmap

1. Engage an independent firm for a third-party security audit and
   penetration test before GA.
2. Close P2 findings (ARGO-S10-011 audit-log signing & default SIEM
   export).
3. Add continuous fuzzing (OpenAPI contract fuzzing via schemathesis is
   already in CI) and expand the security regression suite.
4. Publish advisories for any externally reported issues per
   [`SECURITY.md`](../../SECURITY.md).
