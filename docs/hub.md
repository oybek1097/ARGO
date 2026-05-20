# Hub & Marketplace

The ARGO **Hub** is the distribution channel for skills and plugins. It lets
you package a skill or plugin into a single signed file, publish it to a
registry, and install it on another machine — with every install verified
before anything touches disk.

The Hub is implemented under `argo_brain/hub/` and is built entirely on the
Python standard library (`tarfile`, `gzip`, `json`, `hashlib`, `hmac`).

## The `.argopkg` package format

**Module:** `argo_brain/hub/package.py`

A `.argopkg` is the distributable unit of the Hub: one skill or plugin bundled
with its metadata. It is a deliberately boring **gzipped tar archive** so it
can be inspected with standard tools:

```
manifest.json        — the package manifest (metadata)
files/<name>         — the payload (skill markdown, plugin sources, ...)
```

### The manifest

`manifest.json` describes the package:

| Field | Default | Meaning |
|---|---|---|
| `name` | — (required) | Package name. |
| `version` | — (required) | Package version (`name@version` is the reference string). |
| `kind` | `skill` | `skill` or `plugin`. |
| `author` | `unknown` | The author. |
| `license` | `MIT` | The license. |
| `description` | `""` | A short description. |
| `category` | `general` | A grouping label (skills). |
| `triggers` | `[]` | Skill trigger keywords (skills). |
| `requires` | `[]` | Tools / packages the payload needs. |
| `api_version` | `3.0` | Minimum ARGO API version targeted. |
| `format` | `1` | The package layout version. |

### Reproducible builds and content addressing

`ArgoPackage.to_bytes()` serialises the archive **deterministically**: members
are sorted, and timestamps and ownership are zeroed (including the gzip header
`mtime`). The same manifest and files therefore always produce identical
bytes.

The package **digest** is the SHA-256 of those bytes. The digest is the
content address used by the registry and re-checked on install — if a single
byte changes, the digest changes, and the install is rejected.

### Building a skill package

```python
from argo_brain.hub.package import build_skill_package

pkg = build_skill_package(
    name="deploy-k8s",
    version="1.0.0",
    markdown=open("deploy-k8s.md").read(),
    author="you",
    description="Deploy a service to Kubernetes",
    category="devops",
    triggers=["deploy", "kubernetes", "k8s"],
)
```

## Signing and trust

**Module:** `argo_brain/hub/signing.py`

Every package published to the Hub carries a **detached signature** so a
client can verify *who* published it and that the bytes were not tampered
with.

- Signatures use **HMAC-SHA256** under a per-publisher trust key. The Python
  standard library ships no dependency-free asymmetric primitive, so the Hub
  uses a **trusted-key model** — the same model `apt`/`pip` index mirrors use
  internally. The `Signature` envelope records the algorithm, so an asymmetric
  backend can be slotted in unchanged once a crypto dependency is permitted.
- The `TrustStore` maps publisher names to their trust keys. A client verifies
  a package **only** if it holds a key for the signing publisher; an unknown
  publisher is rejected, not silently trusted.
- A `TrustStore` can be loaded from a `{publisher: key}` JSON file with
  `TrustStore.from_file(path)`.

> **Roadmap.** Asymmetric (Ed25519/RSA) package signatures are planned for
> when a crypto dependency is allowed. The current HMAC scheme is a genuine
> authenticity + integrity check within the trusted-key model.

## The registry

**Module:** `argo_brain/hub/registry.py`

The `HubRegistry` is the storage backend. It is a **plain directory** — no
database, no daemon — so the same code runs the official hub, a corporate
private hub, or an offline mirror:

```
<root>/index.json                       — searchable catalogue
<root>/packages/<name>@<version>.argopkg — the package bytes
```

`index.json` holds one `RegistryEntry` per published version: the manifest
summary, the content digest, the detached signature and a download counter.

Key behaviour:

- **Versions are immutable.** Re-publishing an existing `name@version` is
  rejected.
- **Publishing requires a signature.** An entry with no signature value is
  refused.
- `search(query, kind=...)` does a catalogue search over name, description,
  category and triggers, newest-first.
- `fetch()` loads a package's bytes, re-checks the digest against the
  catalogue entry, and records a download.

## The Hub client

**Module:** `argo_brain/hub/client.py`

`HubClient` is the user-facing surface. It searches the catalogue, publishes
signed packages, and installs packages into the local skill / plugin
directories.

### Publishing

```python
from argo_brain.hub.client import HubClient
from argo_brain.hub.registry import HubRegistry

registry = HubRegistry("/path/to/registry")
client = HubClient(registry)

entry = client.publish(pkg, publisher="you", key="your-trust-key")
```

`publish()` signs the canonical package bytes as `publisher` and stores the
package plus a signed index entry.

### Installing

```python
from argo_brain.hub.signing import TrustStore

trust = TrustStore.from_file("~/.argo/trust.json")
client = HubClient(registry, trust=trust)

result = client.install("deploy-k8s")          # latest version
result = client.install("deploy-k8s", version="1.0.0")
```

`install()` enforces a strict trust flow before writing anything to disk:

1. **Fetch** the package bytes from the registry.
2. **Confirm** the SHA-256 digest matches the catalogue entry.
3. **Verify** the detached signature against the local `TrustStore`.
4. Only then **extract** the payload into the right directory — `skills` go to
   `~/.argo/skills/`, `plugins` go to `~/.argo/plugins/`.

With the default `require_signature=True`, a package signed by an untrusted
publisher, or one with a bad signature, raises `HubError` before any file is
touched. Passing `require_signature=False` downgrades a failure to an
*unverified* install and is intended only for local development hubs.

## See also

- [Skills](skills.md) — the skill format that Hub packages carry.
- [Tools](tools.md) — plugins extend ARGO's behaviour around tools.
- [Configuration](configuration.md) — the `~/.argo/skills/` and
  `~/.argo/plugins/` directories.
