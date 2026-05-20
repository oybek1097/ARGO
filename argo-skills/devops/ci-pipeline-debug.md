---
name: Debug a Failing CI Pipeline
slug: ci-pipeline-debug
trigger: ci, pipeline, build failed, github actions, gitlab ci
category: devops
quality: 0.8
author: argo-team
license: MIT
requires_tools: [shell, http_get]
---

# Debug a Failing CI Pipeline

1. Fetch the failing job log and scroll to the first error, not the last.
2. Classify the failure: dependency, test, lint, infra/timeout, or flaky.
3. Reproduce locally with the exact command from the CI step.
4. For dependency drift, compare the lockfile against the CI cache key.
5. For flaky tests, re-run in isolation 5x to confirm non-determinism.
6. Propose a minimal fix and, if infra-related, suggest a cache or retry tweak.
