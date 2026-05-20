---
name: Handle an Unexpected Error Gracefully
slug: handle-error-gracefully
trigger: error handling, unexpected, fallback, graceful
category: general
quality: 0.72
author: argo-team
license: MIT
requires_tools: []
---

# Handle an Unexpected Error Gracefully

1. Catch errors at the right boundary — not too broad, not too narrow.
2. Log enough context to diagnose without exposing secrets.
3. Fail loudly internally but degrade gracefully for the user.
4. Provide a clear, actionable message instead of a stack trace.
5. Ensure the system is left in a consistent state.
