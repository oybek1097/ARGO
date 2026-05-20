---
name: Optimise a Slow Function
slug: optimize-slow-function
trigger: performance, slow, optimize, profile, bottleneck
category: coding
quality: 0.81
author: argo-team
license: MIT
requires_tools: [shell, file_read]
---

# Optimise a Slow Function

1. Measure first: profile to find the actual hot path — never guess.
2. Confirm the algorithmic complexity; an O(n^2) loop beats micro-tuning.
3. Reduce repeated work: cache, batch, or hoist invariants out of loops.
4. Re-measure after each change and keep only changes that help.
5. Add a benchmark so the regression cannot silently return.
