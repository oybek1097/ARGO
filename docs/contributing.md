# Contributing

ARGO is an open-source project — pull requests and issues are welcome. This
page is a short pointer; the authoritative guide is
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## Getting started

```bash
git clone https://github.com/oybek1097/ARGO.git
cd ARGO
./scripts/setup.sh
```

## Running the tests

### argo-brain (Python)

The Python brain's tests use the standard-library `unittest`, so they run
without `pytest`. From the `argo-brain/` directory:

```bash
cd argo-brain
python3 -m unittest discover -s tests       # full test suite (must stay green)
python3 -m argo_brain selftest              # subsystem smoke test
```

### argo-core (Rust)

From the `argo-core/` directory:

```bash
cd argo-core
cargo test
cargo build --release
cargo clippy -- -D warnings
cargo fmt --check
```

## Ground rules

- **Python 3.11+** is required.
- The brain runs on the **standard library only** — discuss before adding any
  new dependency.
- The whole project is written in **English** — code, comments, docstrings,
  Markdown docs and user-facing strings. ARGO is a multilingual *product*,
  but its codebase is English.
- Keep the test suites green.

## Code style

| Language | Lint | Format |
|---|---|---|
| Python | `ruff` | `ruff format` |
| Rust | `cargo clippy` | `cargo fmt` |

## Pull request process

1. Open an issue and discuss the change.
2. Create a branch, make your changes, and keep the tests green.
3. Submit a PR — CI must be green.
4. Include a `Signed-off-by:` trailer in your commit messages.

By contributing you agree that your code is distributed under the MIT
license. See the full [`CONTRIBUTING.md`](../CONTRIBUTING.md) for details.
</content>
