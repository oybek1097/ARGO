---
name: Refactor Code Without Behaviour Change
slug: refactor-safely
trigger: refactor, clean up, restructure, simplify code
category: coding
quality: 0.82
author: argo-team
license: MIT
requires_tools: [file_read, file_write, shell]
---

# Refactor Code Without Behaviour Change

1. Ensure a passing test suite exists; if not, write characterisation tests.
2. Make one small structural change at a time (extract, rename, inline).
3. Run the tests after every step — never batch unverified changes.
4. Keep behaviour identical; defer functional changes to a separate commit.
5. Review the final diff for accidental scope creep before committing.
