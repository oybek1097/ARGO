---
name: Diagnose an Exception from a Stack Trace
slug: debug-stack-trace
trigger: stack trace, exception, error, crash, traceback
category: coding
quality: 0.83
author: argo-team
license: MIT
requires_tools: [file_read, shell]
---

# Diagnose an Exception from a Stack Trace

1. Read the trace bottom-up: the root cause is the deepest frame you own.
2. Identify the exact line and the variable/state that triggered it.
3. Reproduce with the minimal input that exercises that code path.
4. Form one hypothesis, add a targeted assertion or log, and confirm it.
5. Fix the root cause, not the symptom, and add a regression test.
