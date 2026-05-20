"""Hub client — spec section 4.7 / Sprint 11 (Hub & Marketplace).

`HubClient` is the user-facing surface of the marketplace. It searches the
registry catalogue, publishes signed packages, and installs packages into the
local skill / plugin directories — refusing on install any package whose bytes
or signature do not check out.

Install trust flow:
  1. fetch bytes from the registry,
  2. confirm the SHA-256 digest matches the catalogue entry,
  3. verify the detached signature against the local `TrustStore`,
  4. only then extract the payload files to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from argo_brain.hub.package import KIND_PLUGIN, KIND_SKILL, ArgoPackage
from argo_brain.hub.registry import HubRegistry, RegistryEntry
from argo_brain.hub.signing import Signature, SignatureError, TrustStore, sign


class HubError(Exception):
    """Raised when an install fails verification or a destination is unknown."""


@dataclass
class InstallResult:
    """Outcome of a successful `HubClient.install`."""

    entry: RegistryEntry
    paths: list[Path]
    signature_verified: bool


class HubClient:
    """High-level marketplace client over a `HubRegistry`."""

    def __init__(
        self,
        registry: HubRegistry,
        *,
        trust: TrustStore | None = None,
        skills_dir: Path | str = "~/.argo/skills",
        plugins_dir: Path | str = "~/.argo/plugins",
    ) -> None:
        self.registry = registry
        self.trust = trust or TrustStore()
        self.skills_dir = Path(skills_dir).expanduser()
        self.plugins_dir = Path(plugins_dir).expanduser()

    # -- discovery ---------------------------------------------------------
    def search(self, query: str = "", *, kind: str | None = None) -> list[RegistryEntry]:
        return self.registry.search(query, kind=kind)

    def info(self, name: str, version: str | None = None) -> RegistryEntry:
        return self.registry.get(name, version)

    # -- publishing --------------------------------------------------------
    def publish(self, package: ArgoPackage, *, publisher: str, key: str) -> RegistryEntry:
        """Sign ``package`` as ``publisher`` and publish it to the registry."""
        signature = sign(package.to_bytes(), publisher=publisher, key=key)
        return self.registry.publish(package, signature)

    # -- installing --------------------------------------------------------
    def install(
        self,
        name: str,
        *,
        version: str | None = None,
        require_signature: bool = True,
    ) -> InstallResult:
        """Fetch, verify and extract a package into the right local directory.

        With ``require_signature`` (the default) a package signed by an
        untrusted publisher, or with a bad signature, raises `HubError` before
        anything touches disk. Passing ``require_signature=False`` downgrades
        a verification failure to an unverified install — used only for local
        development hubs.
        """
        entry, package = self.registry.fetch(name, version)

        # registry.fetch has already confirmed digest == entry.digest; the
        # signature is verified over those same canonical bytes.
        payload = package.to_bytes()
        verified = self._verify_signature(entry, payload, require_signature)
        dest_dir = self._dest_dir(package)
        dest_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for rel, blob in package.files.items():
            target = dest_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            written.append(target)
        return InstallResult(entry=entry, paths=written, signature_verified=verified)

    def _verify_signature(
        self, entry: RegistryEntry, payload: bytes, require: bool
    ) -> bool:
        if not entry.signature:
            if require:
                raise HubError(f"{entry.ref} has no signature")
            return False
        signature = Signature.from_dict(entry.signature)
        try:
            ok = self.trust.verify(payload, signature)
        except SignatureError as exc:
            if require:
                raise HubError(f"signature check failed for {entry.ref}: {exc}") from exc
            return False
        if not ok and require:
            raise HubError(f"signature does not verify for {entry.ref}")
        return ok

    def _dest_dir(self, package: ArgoPackage) -> Path:
        kind = package.manifest.kind
        if kind == KIND_SKILL:
            return self.skills_dir
        if kind == KIND_PLUGIN:
            return self.plugins_dir
        raise HubError(f"cannot install unknown package kind: {kind!r}")
