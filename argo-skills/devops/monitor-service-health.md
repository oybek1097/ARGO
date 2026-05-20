---
name: Check Service Health
slug: monitor-service-health
trigger: health, uptime, monitoring, status, metrics
category: devops
quality: 0.78
author: argo-team
license: MIT
requires_tools: [http_get, shell]
---

# Check Service Health

1. Hit the service `/health` or `/readyz` endpoint and record the status code.
2. Pull recent error-rate and p99 latency from the metrics backend.
3. Check resource pressure: CPU, memory, disk, and open file descriptors.
4. Inspect the last 100 log lines for repeated error signatures.
5. Summarise as healthy / degraded / down with the single most likely cause.
