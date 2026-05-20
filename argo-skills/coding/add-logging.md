---
name: Add Structured Logging to a Module
slug: add-logging
trigger: logging, log statements, observability, structured logs
category: coding
quality: 0.74
author: argo-team
license: MIT
requires_tools: [file_read, file_write]
---

# Add Structured Logging to a Module

1. Choose levels: DEBUG for flow, INFO for milestones, WARN/ERROR for faults.
2. Log structured key-value context (IDs, counts), never bare strings.
3. Never log secrets, tokens, or full request bodies.
4. Log at boundaries: entry, external calls, and error handlers.
5. Confirm log volume is sane under load — no per-iteration spam.
