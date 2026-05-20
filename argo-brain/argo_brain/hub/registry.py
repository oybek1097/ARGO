"""Hub registry — spec section 4.7 / Sprint 11 (Hub & Marketplace).

The registry is the storage backend behind ``skills.argo-agent.io``. It is a
plain directory so the same code runs the official hub, a corporate private
hub, or an offline mirror — no database, no daemon:

    <root>/index.json                      — searchable catalogue
    <root>/packages/<name>@<version>.argopkg

`index.json` holds one `RegistryEntry` per published package: its manifest
summary, content digest and detached signature. The actual package bytes live
beside it. Clients search the index, then fetch and verify the bytes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from argo_brain.hub.package import ArgoPackage, PackageError, utc_now
from argo_brain.hub.signing import Signature


class RegistryError(Exception):
    """Raised on publish/fetch errors against the registry."""


@dataclass
class RegistryEntry:
    """One catalogue row: a published package version."""

    name: str
    version: str
    kind: str
    author: str
    description: str
    digest: str
    signature: dict = field(default_factory=dict)
    category: str = "general"
    triggers: list[str] = field(default_factory=list)
    downloads: int = 0
    published_at: str = ""

    @property
    def ref(self) -> str:
        return f"{self.name}@{self.version}"

    @property
    def filename(self) -> str:
        return f"{self.ref}.argopkg"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RegistryEntry":
        fields = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in fields})


class HubRegistry:
    """A file-backed package registry."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root).expanduser()
        self.packages_dir = self.root / "packages"
        self.index_path = self.root / "index.json"

    # -- lifecycle ---------------------------------------------------------
    def init(self) -> None:
        """Create the registry layout if it does not exist yet."""
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self._write_index([])

    def _read_index(self) -> list[RegistryEntry]:
        if not self.index_path.is_file():
            return []
        raw = json.loads(self.index_path.read_text(encoding="utf-8"))
        return [RegistryEntry.from_dict(row) for row in raw.get("packages", [])]

    def _write_index(self, entries: list[RegistryEntry]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        doc = {
            "schema": 1,
            "updated_at": utc_now(),
            "packages": [e.to_dict() for e in entries],
        }
        # Atomic replace so a crash mid-write cannot corrupt the index.
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.index_path)

    # -- publishing --------------------------------------------------------
    def publish(self, package: ArgoPackage, signature: Signature) -> RegistryEntry:
        """Store ``package`` and append a signed entry to the index.

        Re-publishing an existing ``name@version`` is rejected; versions are
        immutable once published.
        """
        self.init()
        m = package.manifest
        entries = self._read_index()
        if any(e.name == m.name and e.version == m.version for e in entries):
            raise RegistryError(f"{m.ref} is already published (versions are immutable)")
        if not signature.value:
            raise RegistryError("a signature is required to publish")

        data = package.to_bytes()
        entry = RegistryEntry(
            name=m.name,
            version=m.version,
            kind=m.kind,
            author=m.author,
            description=m.description,
            digest=package.digest,
            signature=signature.to_dict(),
            category=m.category,
            triggers=list(m.triggers),
            published_at=utc_now(),
        )
        (self.packages_dir / entry.filename).write_bytes(data)
        entries.append(entry)
        self._write_index(entries)
        return entry

    # -- queries -----------------------------------------------------------
    def all(self) -> list[RegistryEntry]:
        return self._read_index()

    def search(self, query: str = "", *, kind: str | None = None) -> list[RegistryEntry]:
        """Catalogue search over name/description/triggers, newest-first.

        An empty query lists everything; ``kind`` filters skill vs plugin.
        """
        q = query.lower().strip()
        out: list[RegistryEntry] = []
        # index.json preserves publish order, so reversing yields newest-first
        # without relying on the (second-granular) published_at timestamp.
        for e in reversed(self._read_index()):
            if kind and e.kind != kind:
                continue
            haystack = " ".join([e.name, e.description, e.category, *e.triggers]).lower()
            if not q or q in haystack:
                out.append(e)
        return out

    def versions(self, name: str) -> list[RegistryEntry]:
        """All published versions of ``name``, newest published first."""
        return [e for e in reversed(self._read_index()) if e.name == name]

    def get(self, name: str, version: str | None = None) -> RegistryEntry:
        """Resolve one entry; ``version=None`` picks the latest published."""
        rows = self.versions(name)
        if not rows:
            raise RegistryError(f"no such package: {name}")
        if version is None:
            return rows[0]
        for e in rows:
            if e.version == version:
                return e
        raise RegistryError(f"no such version: {name}@{version}")

    def fetch(self, name: str, version: str | None = None) -> tuple[RegistryEntry, ArgoPackage]:
        """Load a package's bytes, recording one download against its entry."""
        entry = self.get(name, version)
        path = self.packages_dir / entry.filename
        if not path.is_file():
            raise RegistryError(f"package file missing for {entry.ref}")
        data = path.read_bytes()
        package = ArgoPackage.from_bytes(data)
        if package.digest != entry.digest:
            raise PackageError(
                f"digest mismatch for {entry.ref}: index and stored bytes disagree"
            )
        self._bump_downloads(entry.ref)
        return entry, package

    def _bump_downloads(self, ref: str) -> None:
        entries = self._read_index()
        for e in entries:
            if e.ref == ref:
                e.downloads += 1
        self._write_index(entries)
