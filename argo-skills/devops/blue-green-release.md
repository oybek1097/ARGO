---
name: Run a Blue-Green Release
slug: blue-green-release
trigger: blue green, zero downtime, cutover, release strategy
category: devops
quality: 0.82
author: argo-team
license: MIT
requires_tools: [kubectl, http_get]
---

# Run a Blue-Green Release

1. Deploy the new version as the idle colour alongside the live one.
2. Run smoke and health checks against the idle environment directly.
3. Shift a small slice of traffic and watch error rate for 5-10 minutes.
4. Cut the load balancer fully over to the new colour.
5. Keep the old colour warm for one rollback window before scaling it down.
