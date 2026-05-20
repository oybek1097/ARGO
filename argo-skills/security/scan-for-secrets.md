---
name: Scan a Repository for Leaked Secrets
slug: scan-for-secrets
trigger: secret scanning, leaked credentials, git secrets
category: security
quality: 0.8
author: argo-team
license: MIT
requires_tools: [shell, file_read]
---

# Scan a Repository for Leaked Secrets

1. Scan the working tree and the full git history for secret patterns.
2. Triage hits — distinguish real secrets from test fixtures.
3. Rotate every confirmed real secret immediately.
4. Purge from history only after rotation; rotation comes first.
5. Add a pre-commit hook and CI scan to prevent recurrence.
