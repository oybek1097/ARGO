---
name: Tune a Horizontal Pod Autoscaler
slug: scale-autoscaler
trigger: autoscaler, hpa, scaling, capacity
category: devops
quality: 0.75
author: argo-team
license: MIT
requires_tools: [kubectl]
---

# Tune a Horizontal Pod Autoscaler

1. Inspect the current HPA target metric and min/max replica bounds.
2. Review historical load to confirm the target utilisation is realistic.
3. Ensure pod resource requests are set — the HPA needs them to compute %.
4. Adjust min replicas to cover baseline traffic without cold starts.
5. Apply, then load test to confirm scale-up and scale-down both trigger.
