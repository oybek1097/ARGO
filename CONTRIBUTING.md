# Contributing to ARGO Agent

ARGO is an open-source project. Pull requests and issues are welcome.

## Getting started

```bash
git clone https://github.com/oybek1097/ARGO.git
cd ARGO
./scripts/setup.sh
```

## argo-brain (Python)

```bash
cd argo-brain
python3 -m unittest discover -s tests   # tests (84, must stay green)
python3 -m argo_brain selftest          # smoke test
```

- Python 3.11+ is required.
- The core runs on the **stdlib only** — discuss before adding any new
  dependency.
- **The whole project is written in English** — code, comments, docstrings,
  Markdown docs and user-facing strings. ARGO is a multilingual *product*,
  but its codebase is English.

## argo-core (Rust)

```bash
cd argo-core
cargo test
cargo build --release
cargo clippy -- -D warnings
cargo fmt --check
```

## Pull request process (spec section 11)

1. Open an issue and discuss.
2. Create a branch, make changes, keep the tests green.
3. Submit a PR — CI must be green.
4. Include a `Signed-off-by:` trailer in commit messages.

## Code style

| Language | Lint | Format |
|---|---|---|
| Python | `ruff` | `ruff format` |
| Rust | `cargo clippy` | `cargo fmt` |

## License

By contributing you agree that your code is distributed under the MIT
license.
