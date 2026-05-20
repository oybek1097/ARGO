---
name: Investigate a Memory Leak
slug: investigate-memory-leak
trigger: memory leak, oom, out of memory, ram usage
category: system
quality: 0.79
author: argo-team
license: MIT
requires_tools: [shell]
---

# Investigate a Memory Leak

1. Confirm the trend: memory rising over time without release.
2. Identify the leaking process and watch RSS growth.
3. Capture heap snapshots at intervals and diff the allocations.
4. Trace the growing object type back to the retaining code.
5. Fix the retention; add a memory ceiling and an alert as a safety net.
