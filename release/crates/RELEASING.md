# Releasing `argo-core` to crates.io

This runbook covers publishing the `argo-core` crate — the ARGO Agent Rust
gateway — to [crates.io](https://crates.io/). It targets the **v3.0.0 GA**
release of ARGO Agent v3.0.

> Status: ARGO is alpha approaching its GA. A crates.io version **cannot be
> overwritten** once published, and a name, once taken, cannot be reused.
> Rehearse the whole runbook with `--dry-run` before the real `cargo publish`.

## Scope

Only `argo-core` (the Rust component) is published to crates.io. The Python
brain, `argo-brain`, is released separately to PyPI — see
`release/pypi/RELEASING.md`.

`argo-core` is primarily an application (it ships an `argo-core` binary),
but publishing it to crates.io still gives users a `cargo install argo-core`
path and a canonical, versioned source archive.

## Prerequisites

- A current stable Rust toolchain:
  ```bash
  rustup update stable
  cargo --version
  ```
- A crates.io account (sign in with GitHub) with a verified email address.
- A crates.io API token, created at <https://crates.io/settings/tokens>,
  scoped to `publish-new` and `publish-update`. Store it with:
  ```bash
  cargo login        # paste the token when prompted
  ```
- Repository checked out clean (`git status` shows no changes) on `main`.
- The crate builds and the binary runs:
  ```bash
  cd argo-core
  cargo build --release --locked
  ./target/release/argo-core --version
  ```

## 1. Add the publishing metadata to `Cargo.toml`

The in-repo `argo-core/Cargo.toml` carries only the minimum fields. Before
the first publish, replace its `[package]` section with the block below.
crates.io **requires** a `description` and a `license` (both already
present) and strongly recommends `repository`, `homepage`,
`documentation`, `readme`, `keywords` and `categories`.

```toml
[package]
name = "argo-core"
version = "3.0.0"
edition = "2021"
rust-version = "1.82"
license = "MIT"
description = "ARGO Agent v3.0 — Rust HTTP gateway (Axum + Tokio) for the ARGO multilingual AI agent platform"
authors = ["ARGO Agent Project <maintainers@argo-agent.dev>"]
repository = "https://github.com/argo-agent/argo"
homepage = "https://github.com/argo-agent/argo"
documentation = "https://docs.rs/argo-core"
readme = "README.md"
keywords = ["ai", "agent", "gateway", "axum", "llm"]
categories = ["web-programming::http-server", "command-line-utilities"]
# Keep the published archive small: ship only what the crate needs to build.
include = ["src/**/*.rs", "Cargo.toml", "README.md", "../LICENSE"]
```

Notes:

- **`version`** — bump from the development `0.1.0` to `3.0.0` for the GA so
  the crate version tracks the product version.
- **`keywords`** — crates.io allows at most 5 keywords, each lowercase and
  at most 20 characters.
- **`categories`** — must be drawn from the official
  [crates.io category slugs](https://crates.io/category_slugs); the two
  above are valid slugs.
- **`readme`** — `argo-core` has no crate-local `README.md` yet. Add a short
  `argo-core/README.md` (purpose, build, run, link back to the main repo)
  before publishing, or drop the `readme` line. crates.io renders it on the
  crate page.
- **`include`** — optional but recommended; it keeps the uploaded archive
  minimal and predictable. The `../LICENSE` entry pulls in the repository
  MIT license file. If `include` proves awkward across the workspace
  layout, use a `.cargo_vcs_info`-aware `exclude` list instead, or simply
  omit both and let Cargo pick up the VCS-tracked files.

After editing, confirm the manifest still builds:

```bash
cd argo-core
cargo build --release --locked
```

## 2. Verify the package contents

`cargo package` assembles the exact archive that would be uploaded, without
sending anything:

```bash
cd argo-core
cargo package --list      # show every file that will be included
cargo package             # build the .crate archive under target/package/
```

Review the file list — make sure no secrets, local config or stray build
artifacts are included, and that `LICENSE` and `README.md` are present.

## 3. Dry run

`cargo publish --dry-run` runs the full publish pipeline (packaging,
building the packaged crate in isolation) but stops short of upload:

```bash
cd argo-core
cargo publish --dry-run --locked
```

This must complete with no errors and no warnings about missing metadata.

## 4. Publish

Once the dry run is clean and the version is final:

```bash
cd argo-core
cargo publish --locked
```

`cargo publish` is **irreversible** for that version. If a published
release is broken you cannot replace it — you must `cargo yank` it and
publish a fixed patch version (`3.0.1`):

```bash
cargo yank --version 3.0.0     # hide a broken release from new resolutions
cargo yank --version 3.0.0 --undo   # un-yank if yanked by mistake
```

Yanking does not delete the version; it only stops new dependents from
selecting it.

## 5. Tag and create the GitHub release

```bash
git tag -a v3.0.0 -m "ARGO Agent v3.0.0 GA"
git push origin main
git push origin v3.0.0

gh release create v3.0.0 \
    --title "ARGO Agent v3.0.0 GA" \
    --notes-file release-notes.md
```

## Post-release checklist

- [ ] `cargo install argo-core` from a clean environment installs `3.0.0`
      and produces a working `argo-core` binary.
- [ ] The crates.io page renders the README and shows the correct
      repository / homepage / documentation links.
- [ ] <https://docs.rs/argo-core> builds successfully (docs.rs picks the
      crate up automatically a few minutes after publish).
- [ ] The GitHub release `v3.0.0` is published.
- [ ] Bump the in-repo `argo-core/Cargo.toml` `version` to the next
      development cycle (e.g. `3.1.0-dev`).

## See also

- `release/pypi/RELEASING.md` — publishing `argo-brain` to PyPI.
- `release/debian/README.md` — building the Debian `.deb`.
- `release/homebrew/argo.rb` — the Homebrew formula.
