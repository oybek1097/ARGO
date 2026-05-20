"""ARGO package format — spec section 4.7 / Sprint 11 (Hub & Marketplace).

A ``.argopkg`` is the distributable unit of the ARGO hub: a single skill or
plugin bundled with its metadata. The format is a deliberately boring
``tar.gz`` archive so it can be inspected with standard tools:

    manifest.json        — the package manifest (see `Manifest`)
    files/<name>         — the payload (skill markdown, plugin sources, ...)

Dependency-free: built entirely on the standard library (`tarfile`, `json`,
`hashlib`). The package *digest* is the SHA-256 of the archive bytes and acts
as the content address used by the registry and verified on install.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
import time
from dataclasses import asdict, dataclass, field

# Bump when the on-disk layout changes in a backwards-incompatible way.
PACKAGE_FORMAT = 1

# Package kinds the hub understands.
KIND_SKILL = "skill"
KIND_PLUGIN = "plugin"
_KINDS = (KIND_SKILL, KIND_PLUGIN)


class PackageError(Exception):
    """Raised when a package is malformed or fails validation."""


@dataclass
class Manifest:
    """Metadata describing one hub package."""

    name: str
    version: str
    kind: str = KIND_SKILL
    author: str = "unknown"
    license: str = "MIT"
    description: str = ""
    # Skill-oriented hints, ignored for plugins.
    category: str = "general"
    triggers: list[str] = field(default_factory=list)
    # Tools / packages the payload needs to run.
    requires: list[str] = field(default_factory=list)
    # Minimum ARGO API version the package targets.
    api_version: str = "3.0"
    format: int = PACKAGE_FORMAT

    def __post_init__(self) -> None:
        if not self.name:
            raise PackageError("manifest.name is required")
        if not self.version:
            raise PackageError("manifest.version is required")
        if self.kind not in _KINDS:
            raise PackageError(f"unknown package kind: {self.kind!r}")

    @property
    def ref(self) -> str:
        """The ``name@version`` reference string used across the hub."""
        return f"{self.name}@{self.version}"

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Manifest":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        unknown = set(data) - known
        if unknown:
            raise PackageError(f"unknown manifest fields: {sorted(unknown)}")
        return cls(**data)


@dataclass
class ArgoPackage:
    """An in-memory ``.argopkg``: a manifest plus its payload files."""

    manifest: Manifest
    files: dict[str, bytes] = field(default_factory=dict)

    @property
    def digest(self) -> str:
        """SHA-256 content address of the serialised archive."""
        return hashlib.sha256(self.to_bytes()).hexdigest()

    def to_bytes(self) -> bytes:
        """Serialise to deterministic ``tar.gz`` bytes.

        Member order, timestamps and ownership are fixed so that the same
        manifest + files always produce the same digest. The gzip wrapper is
        written with ``mtime=0`` explicitly: ``tarfile``'s own ``w:gz`` mode
        stamps the *current* wall-clock time into the gzip header, which would
        make the digest change second-to-second and break content addressing.
        """
        tar_buf = io.BytesIO()
        # mtime=0 + sorted members → reproducible archive → stable digest.
        with tarfile.open(fileobj=tar_buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
            self._add(tar, "manifest.json", self.manifest.to_json().encode("utf-8"))
            for name in sorted(self.files):
                self._add(tar, f"files/{name}", self.files[name])
        gz_buf = io.BytesIO()
        # mtime=0 → the gzip header carries no timestamp → reproducible bytes.
        with gzip.GzipFile(fileobj=gz_buf, mode="wb", mtime=0) as gz:
            gz.write(tar_buf.getvalue())
        return gz_buf.getvalue()

    @staticmethod
    def _add(tar: tarfile.TarFile, name: str, data: bytes) -> None:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.mode = 0o644
        tar.addfile(info, io.BytesIO(data))

    @classmethod
    def from_bytes(cls, data: bytes) -> "ArgoPackage":
        """Parse ``.argopkg`` bytes, rejecting unsafe or malformed archives."""
        manifest: Manifest | None = None
        files: dict[str, bytes] = {}
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        raise PackageError(f"non-file member: {member.name}")
                    path = member.name
                    if path.startswith("/") or ".." in path.split("/"):
                        raise PackageError(f"unsafe member path: {path}")
                    payload = tar.extractfile(member)
                    blob = payload.read() if payload else b""
                    if path == "manifest.json":
                        try:
                            parsed = json.loads(blob)
                        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                            raise PackageError(
                                f"corrupt manifest.json: {exc}"
                            ) from exc
                        manifest = Manifest.from_dict(parsed)
                    elif path.startswith("files/"):
                        files[path[len("files/"):]] = blob
                    else:
                        raise PackageError(f"unexpected member: {path}")
        except tarfile.TarError as exc:
            raise PackageError(f"corrupt archive: {exc}") from exc
        if manifest is None:
            raise PackageError("package has no manifest.json")
        if manifest.format > PACKAGE_FORMAT:
            raise PackageError(
                f"package format {manifest.format} is newer than supported "
                f"{PACKAGE_FORMAT}"
            )
        return cls(manifest=manifest, files=files)


def build_skill_package(
    *,
    name: str,
    version: str,
    markdown: str,
    author: str = "unknown",
    description: str = "",
    category: str = "general",
    triggers: list[str] | None = None,
    requires: list[str] | None = None,
) -> ArgoPackage:
    """Convenience builder for a single-file markdown skill package."""
    manifest = Manifest(
        name=name,
        version=version,
        kind=KIND_SKILL,
        author=author,
        description=description,
        category=category,
        triggers=triggers or [],
        requires=requires or [],
    )
    return ArgoPackage(manifest=manifest, files={f"{name}.md": markdown.encode("utf-8")})


def utc_now() -> str:
    """ISO-8601 UTC timestamp used for registry entries."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
