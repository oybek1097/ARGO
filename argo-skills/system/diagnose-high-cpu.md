---
name: Diagnose High CPU Usage
slug: diagnose-high-cpu
trigger: high cpu, cpu usage, slow server, performance issue
category: system
quality: 0.81
author: argo-team
license: MIT
requires_tools: [shell]
---

# Diagnose High CPU Usage

1. Identify the top processes with `top` or `ps aux --sort=-%cpu`.
2. For the offender, check whether it is user or system (kernel) time.
3. Inspect threads and, if needed, capture a profile or stack sample.
4. Correlate with recent deploys, cron jobs, or traffic spikes.
5. Apply the fix (throttle, fix the loop, scale out) and re-measure.
