---
name: Write Unit Tests for a Function
slug: write-unit-tests
trigger: unit test, write tests, coverage, pytest, jest
category: coding
quality: 0.85
author: argo-team
license: MIT
requires_tools: [file_read, file_write, shell]
---

# Write Unit Tests for a Function

1. Read the target function and list its inputs, outputs, and side effects.
2. Enumerate cases: happy path, boundary values, empty input, and errors.
3. Write one focused test per case with a descriptive name.
4. Mock external dependencies (network, clock, filesystem) for determinism.
5. Run the suite and confirm every new test fails for the right reason if
   the implementation is broken on purpose.
6. Report the resulting line/branch coverage delta.
