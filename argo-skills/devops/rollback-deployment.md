---
name: Roll Back a Bad Deployment
slug: rollback-deployment
trigger: rollback, revert deploy, incident, bad release
category: devops
quality: 0.86
author: argo-team
license: MIT
requires_tools: [kubectl, shell]
---

# Roll Back a Bad Deployment

1. Confirm the bad release: error rate, latency, or a failed health check.
2. Identify the last known-good revision (`kubectl rollout history`).
3. Roll back with `kubectl rollout undo --to-revision=<n>` or redeploy the
   previous image tag.
4. Watch the rollout until healthy, then re-check the failing metric.
5. Freeze further deploys and open an incident note with the timeline.
6. File a follow-up to root-cause the bad release before re-attempting.
