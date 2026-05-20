---
name: Audit Dependencies for Vulnerabilities
slug: security-audit-dependencies
trigger: security, vulnerability, cve, dependency audit
category: security
quality: 0.84
author: argo-team
license: MIT
requires_tools: [shell]
---

# Audit Dependencies for Vulnerabilities

1. Run the ecosystem's audit tool to list known CVEs.
2. Triage by severity and whether the vulnerable path is actually used.
3. Upgrade to a patched version; if none exists, assess mitigations.
4. Re-run the audit to confirm resolution.
5. Schedule recurring audits so new CVEs are caught early.
