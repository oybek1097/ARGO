---
name: Review IAM Permissions
slug: review-iam-permissions
trigger: iam, permissions, least privilege, access control
category: security
quality: 0.82
author: argo-team
license: MIT
requires_tools: [shell]
---

# Review IAM Permissions

1. Enumerate principals and the policies attached to each.
2. Flag wildcards in actions or resources — narrow them.
3. Apply least privilege: grant only what the role actually uses.
4. Remove unused roles, keys, and stale human accounts.
5. Enable access logging and review it periodically.
