---
name: Review a Pull Request
slug: code-review-checklist
trigger: code review, pull request, pr, review code
category: coding
quality: 0.84
author: argo-team
license: MIT
requires_tools: [file_read]
---

# Review a Pull Request

1. Read the PR description; confirm scope matches the diff.
2. Check correctness: edge cases, error handling, and concurrency.
3. Check readability: naming, dead code, and oversized functions.
4. Verify tests cover the new behaviour and existing tests still pass.
5. Look for security and performance regressions in changed paths.
6. Leave actionable comments grouped by blocking vs nice-to-have.
