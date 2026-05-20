---
name: Rotate Compromised Secrets
slug: rotate-secrets
trigger: rotate secrets, leaked key, credential rotation
category: security
quality: 0.86
author: argo-team
license: MIT
requires_tools: [vault_get, shell]
---

# Rotate Compromised Secrets

1. Assume the secret is fully compromised; revoke it immediately.
2. Generate a new secret and update every consuming service.
3. Roll out the new secret with no overlap window once revoked.
4. Scan logs and git history for further exposure of the old secret.
5. Record the incident and check why the leak was possible.
