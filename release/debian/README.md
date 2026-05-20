# Debian / apt packaging for ARGO Agent

This directory holds the Debian packaging sources for the `argo-agent`
package. Building it produces a single `.deb` that installs **both** ARGO
components and a systemd service:

- `argo-core` — the Rust HTTP gateway, compiled with `cargo` and installed
  to `/usr/bin/argo-core`.
- `argo-brain` — the stdlib-only Python 3.12 brain, installed under
  `/usr/lib/argo-agent` and launched through a thin `/usr/bin/argo` wrapper.
- `argo-agent.service` — a hardened systemd unit for the `argo-core`
  gateway (HTTP port 8000, bound to `127.0.0.1` by default).

> Status: ARGO is alpha approaching its v3.0.0 GA. These packaging files
> target that GA. Treat them as a release candidate — test the resulting
> `.deb` on a throwaway machine before relying on it.

## Contents

| File | Purpose |
|---|---|
| `control` | Source/binary package metadata, dependencies, description. |
| `changelog` | Debian changelog — one entry for the `3.0.0-1` GA. |
| `rules` | Build rules: a hand-rolled override of the `dh` sequence. |
| `postinst` | Post-install: creates the `argo` system user, enables the service. |
| `prerm` | Pre-removal: stops and disables the service. |
| `argo-agent.service` | systemd unit installed to `/lib/systemd/system`. |

## Prerequisites

Build on Debian 12 (bookworm) or newer, or a recent Ubuntu LTS:

```bash
sudo apt-get update
sudo apt-get install -y \
    build-essential debhelper devscripts dpkg-dev \
    cargo rustc python3
```

`python3` must be 3.12 or newer (`control` declares `python3 (>= 3.12)`).
On distributions whose `python3` is older, install a 3.12 toolchain first.

## Building the .deb

The packaging files in this directory are kept under `release/debian/` so
they do not clash with anything at the repository root. To build, copy them
into a top-level `debian/` directory of a clean source tree and run
`dpkg-buildpackage`:

```bash
# From a clean checkout of the ARGO repository:
cp -r release/debian debian
dpkg-buildpackage -us -uc -b
```

- `-us -uc` skip GPG-signing the `.changes`/`.dsc` (sign them for a real
  repository upload — see below).
- `-b` builds a binary-only package; the `.deb` lands in the parent
  directory (`../argo-agent_3.0.0-1_<arch>.deb`).

Install and verify locally:

```bash
sudo apt-get install ../argo-agent_3.0.0-1_*.deb
argo version
systemctl status argo-agent.service
curl http://127.0.0.1:8000/api/health
```

Remove it again with:

```bash
sudo apt-get remove argo-agent
```

## Lint

Before publishing, lint the package:

```bash
lintian ../argo-agent_3.0.0-1_*.changes
```

A few informational tags are expected (for example, the hand-rolled
`/usr/bin/argo` wrapper). Fix any `E:` (error) tags before uploading.

## apt repository plan

For the GA, ARGO will be distributed from a self-hosted apt repository
rather than uploaded to the Debian or Ubuntu archives:

1. **Sign** the build with the project release key:
   ```bash
   dpkg-buildpackage -b   # signs the .changes/.dsc with the default key
   ```
2. **Publish** the `.deb` into a repository managed with
   [`aptly`](https://www.aptly.info/) or `reprepro`. Planned layout:
   - Suite: `stable`
   - Component: `main`
   - Architectures: `amd64`, `arm64`
3. **Serve** the repository over HTTPS at `https://apt.argo-agent.dev`.
4. Users add it with:
   ```bash
   curl -fsSL https://apt.argo-agent.dev/argo.gpg \
       | sudo tee /usr/share/keyrings/argo.gpg >/dev/null
   echo "deb [signed-by=/usr/share/keyrings/argo.gpg] \
       https://apt.argo-agent.dev stable main" \
       | sudo tee /etc/apt/sources.list.d/argo.list
   sudo apt-get update
   sudo apt-get install argo-agent
   ```

The repository key, hosting and CI automation are tracked as GA launch
tasks; this document records the intended design.

## See also

- `release/homebrew/argo.rb` — Homebrew formula (macOS / Linuxbrew).
- `release/crates/RELEASING.md` — publishing `argo-core` to crates.io.
- `release/pypi/RELEASING.md` — publishing `argo-brain` to PyPI.
- `scripts/install.sh` — native, package-manager-free install script.
- `DEPLOYMENT.md` — Docker Compose and Kubernetes (Helm) deployment.
