"""ARGO Hub & Marketplace — spec section 4.7 / Sprint 11.

Skill and plugin distribution: a ``.argopkg`` package format, HMAC-signed
publishing, a file-backed registry that runs the official hub or a private
mirror unchanged, and a client that verifies every package before install.
"""

from argo_brain.hub.client import HubClient, HubError, InstallResult
from argo_brain.hub.remote import RemoteRegistry
from argo_brain.hub.server import HubServer
from argo_brain.hub.package import (
    KIND_PLUGIN,
    KIND_SKILL,
    ArgoPackage,
    Manifest,
    PackageError,
    build_skill_package,
)
from argo_brain.hub.registry import HubRegistry, RegistryEntry, RegistryError
from argo_brain.hub.signing import (
    Signature,
    SignatureError,
    TrustStore,
    sign,
    verify,
)

__all__ = [
    "ArgoPackage",
    "Manifest",
    "PackageError",
    "build_skill_package",
    "KIND_SKILL",
    "KIND_PLUGIN",
    "HubRegistry",
    "RegistryEntry",
    "RegistryError",
    "Signature",
    "SignatureError",
    "TrustStore",
    "sign",
    "verify",
    "HubClient",
    "HubError",
    "InstallResult",
    "HubServer",
    "RemoteRegistry",
]
