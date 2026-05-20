---
name: Stabilise a Flaky Test
slug: fix-flaky-test
trigger: flaky test, intermittent failure, non-deterministic test
category: coding
quality: 0.78
author: argo-team
license: MIT
requires_tools: [shell, file_read, file_write]
---

# Stabilise a Flaky Test

1. Run the test in a loop to confirm and measure the failure rate.
2. Identify the source: time, ordering, shared state, or network.
3. Replace real time with a fake clock; isolate shared fixtures.
4. Remove sleeps in favour of explicit waits on a condition.
5. Re-run 50x; only consider it fixed at a 0% failure rate.
