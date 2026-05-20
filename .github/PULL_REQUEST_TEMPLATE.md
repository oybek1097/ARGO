# Pull Request

## Summary

<!-- What does this change do, and why? Keep it concise. -->

## Related issues

<!-- e.g. "Closes #123", "Part of #456". Leave blank if none. -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that changes existing behaviour)
- [ ] Documentation only
- [ ] Build / CI / tooling

## Component(s) touched

- [ ] `argo-brain` (Python)
- [ ] `argo-core` (Rust)
- [ ] Docs
- [ ] CI / packaging

## Pre-merge checklist

These items mirror the required pre-merge checks in the Technical
Specification section 11.

- [ ] **All tests green.** `python3 -m unittest discover -s tests` passes
      from `argo-brain/`, and `cargo test --workspace` passes for `argo-core`.
- [ ] **Lint clean.** `ruff check .` passes for `argo-brain`; `cargo fmt
      --check` and `cargo clippy -- -D warnings` pass for `argo-core`.
- [ ] **Coverage maintained.** New code paths are covered by tests; overall
      coverage is not reduced.
- [ ] **No new security findings (P1+).** The `security-scan` workflow
      reports no new high-severity bandit / `cargo audit` findings.
- [ ] **Performance within 10% of baseline.** If this change could affect a
      hot path, performance targets from spec section 9 still hold (see
      `docs/performance/benchmarking.md`).
- [ ] **Documentation updated.** Public behaviour changes are reflected in
      `docs/` and in docstrings.
- [ ] **Comments and docstrings are in English.**

## Reviewers

- [ ] At least two reviewer approvals before merge.

## Sign-off

By submitting this pull request I certify the Developer Certificate of
Origin (DCO). Every commit includes a `Signed-off-by` trailer:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use `git commit -s` to add it automatically.

## Notes for reviewers

<!-- Anything reviewers should pay particular attention to: trade-offs,
     follow-up work, areas of uncertainty. -->
