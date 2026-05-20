# ARGO Agent — Operator Hardening Checklist

This is an actionable checklist for hardening an ARGO Agent deployment
before exposing it to real users. It implements the controls described in
sections 4.14 and 10 of the
[technical specification](../../ARGO_AGENT_v3_Technical_Specification.md)
and the mitigations in the [threat model](threat-model.md).

Work top to bottom. Items marked **(P0)** should be considered mandatory
for any internet-facing deployment.

## Authentication & identity

- [ ] **(P0)** All API access requires a credential — API key, JWT or
      OAuth 2.0. No anonymous access to chat or tool endpoints.
- [ ] API keys are stored **hashed** at rest, never in plaintext.
- [ ] JWT signing key is at least 256 bits; rotate on a schedule and on
      suspected compromise. Prefer RS256 for multi-service setups.
- [ ] JWT expiry is short (minutes–hours); refresh tokens are revocable.
- [ ] mTLS is enabled for any service-to-service traffic.
- [ ] Default / sample credentials shipped for local development are
      removed or rotated before production.

## Network exposure

- [ ] **(P0)** The admin API is bound to loopback (`127.0.0.1`) or a
      private interface — never `0.0.0.0` on a public host.
- [ ] **(P0)** Only the gateway port intended for clients is reachable
      from untrusted networks; everything else is firewalled.
- [ ] The core ↔ brain IPC uses a UNIX-domain socket, or loopback TCP if a
      socket is not available — never a routable interface.
- [ ] A reverse proxy / WAF terminates public traffic and enforces request
      size and timeout limits.
- [ ] Outbound egress from the host is restricted to required destinations
      (LLM providers, channel APIs).

## Secrets & Vault

- [ ] **(P0)** No API keys or tokens in plaintext environment variables or
      committed config files. Use `vault://` references (or 1Password
      Connect / AWS / GCP / Azure secret managers).
- [ ] The secrets backend enforces least-privilege policies; ARGO's role
      can read only the paths it needs.
- [ ] Secret values are held in memory only while in use, not persisted.
- [ ] Secrets are rotated on a schedule and immediately after any
      personnel or trust change.
- [ ] `.env`, `auth.json` and key material are in `.gitignore` and have
      restrictive file permissions (`0600`).

## Sandbox & tool execution

- [ ] **(P0)** Shell and code execution use a container or microVM backend
      (`docker`, `podman`, `firecracker`, `k8s_pod`) — not `local` — for
      any deployment handling untrusted input.
- [ ] The appropriate sandbox mode is selected: `strict` or `paranoid`
      for shared/untrusted use, `airgapped` where no external network is
      permitted.
- [ ] Sandbox containers run with a read-only rootfs, dropped Linux
      capabilities, a seccomp profile and user namespaces.
- [ ] Sandbox containers have no host network and no Docker socket mount.
- [ ] CPU, memory and wall-clock limits are set on every sandbox.
- [ ] Dangerous tools (`shell_exec`, `kubectl`, file-write, network) are
      gated behind confirmation and restricted to the intended roles.
- [ ] File tools are confined to a workspace root; path traversal outside
      it is rejected.

## Audit logging

- [ ] **(P0)** The append-only audit log is enabled and writable by the
      ARGO process only.
- [ ] Audit records are shipped off-host to a SIEM (Splunk / ELK /
      Sentinel) so a host compromise cannot erase them.
- [ ] Audit log signing is enabled and the verification key is stored
      separately from the log.
- [ ] Retention meets the applicable compliance requirement (e.g. 5 years
      / 1825 days under UZ-152 or RU-152).
- [ ] Alerts fire on high-severity audit events (auth failures, denied
      tool calls, sandbox escapes).

## TLS & transport

- [ ] **(P0)** All external endpoints (HTTP, WebSocket, webhooks) are
      served over TLS 1.2+ (prefer 1.3).
- [ ] Certificates are issued by a trusted CA and auto-renewed.
- [ ] HSTS is enabled; plaintext HTTP redirects to HTTPS.
- [ ] Channel transports (bot APIs, email) use TLS; inbound webhooks
      verify HMAC signatures.

## Rate limiting & quotas

- [ ] **(P0)** Per-user and per-channel rate limits are configured.
- [ ] Per-user resource quotas (tokens, tool calls, cost) are enforced.
- [ ] The agent max-iteration cap is set to bound a single request.
- [ ] Request body size limits and connection caps are configured at the
      gateway.
- [ ] Webhook endpoints are individually rate-limited.

## Least-privilege RBAC

- [ ] **(P0)** Chat users receive the lowest sufficient role
      (`read_only` or `user`), never `admin` by default.
- [ ] The `admin` wildcard role is granted to as few principals as
      possible.
- [ ] Per-tool `requires_role` is set so privileged tools are unreachable
      by ordinary users.
- [ ] Service accounts hold only the `service` / webhook permission set.
- [ ] In multi-tenant deployments, every query is scoped by
      `user_id` / `tenant_id`; this is verified, not assumed.

## Container & host hardening

- [ ] ARGO processes run as a non-root user inside the container.
- [ ] Container images are minimal (slim/distroless) and pinned by digest.
- [ ] `trivy` (or equivalent) scans images for known CVEs before deploy.
- [ ] The host kernel and container runtime are patched and current.
- [ ] No unnecessary mounts (especially not the Docker socket or host
      `/`); volumes are read-only where possible.
- [ ] `cargo audit`, `bandit` and `semgrep` run in CI on every change
      (see [`scripts/security-audit.sh`](../../scripts/security-audit.sh)).

## Operational

- [ ] An incident response contact and process are documented.
- [ ] [`SECURITY.md`](../../SECURITY.md) reporting instructions are current.
- [ ] Backups (SQLite snapshots, optional S3 sync) are encrypted and
      tested by restore.
- [ ] Dependency updates are reviewed and supply-chain checks
      (`argo-supply-chain-check`) run on install.
- [ ] `scripts/security-audit.sh` is run before each release and its
      summary reviewed.

---

After completing this checklist, re-read the [threat model](threat-model.md)
to confirm no boundary is left unaddressed for your specific deployment.
