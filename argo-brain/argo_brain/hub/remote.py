"""Remote hub client — spec section 4.7 / Sprint 11 (Hub & Marketplace).

`RemoteRegistry` speaks to a `HubServer` over HTTP while exposing the very
same method surface as the local `HubRegistry` (`search`, `get`, `versions`,
`fetch`, `publish`, `all`). Because the interface matches, a `HubClient` can
be pointed at a remote hub with no other change:

    client = HubClient(RemoteRegistry("https://skills.argo-agent.io"), ...)

Standard library only — HTTP via `urllib.request`.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from argo_brain.hub.package import ArgoPackage
from argo_brain.hub.registry import RegistryEntry, RegistryError
from argo_brain.hub.signing import Signature

_API = "/hub/v1"


class RemoteRegistry:
    """A read/write client for a remote `HubServer`."""

    def __init__(self, base_url: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    # -- HTTP plumbing -----------------------------------------------------
    def _get(self, path: str, **params) -> bytes:
        url = f"{self.base_url}{_API}{path}"
        query = {k: v for k, v in params.items() if v is not None}
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            raise RegistryError(self._http_message(exc)) from exc
        except urllib.error.URLError as exc:
            raise RegistryError(f"cannot reach hub at {self.base_url}: {exc}") from exc

    def _get_json(self, path: str, **params) -> dict:
        return json.loads(self._get(path, **params))

    @staticmethod
    def _http_message(exc: urllib.error.HTTPError) -> str:
        try:
            return json.loads(exc.read()).get("error", str(exc))
        except Exception:  # noqa: BLE001
            return f"hub returned HTTP {exc.code}"

    # -- registry interface ------------------------------------------------
    def all(self) -> list[RegistryEntry]:
        doc = self._get_json("/index")
        return [RegistryEntry.from_dict(r) for r in doc.get("packages", [])]

    def search(self, query: str = "", *, kind: str | None = None) -> list[RegistryEntry]:
        doc = self._get_json("/search", q=query, kind=kind)
        return [RegistryEntry.from_dict(r) for r in doc.get("packages", [])]

    def versions(self, name: str) -> list[RegistryEntry]:
        path = f"/versions/{urllib.parse.quote(name)}"
        doc = self._get_json(path)
        return [RegistryEntry.from_dict(r) for r in doc.get("versions", [])]

    def get(self, name: str, version: str | None = None) -> RegistryEntry:
        path = f"/package/{urllib.parse.quote(name)}"
        return RegistryEntry.from_dict(self._get_json(path, version=version))

    def fetch(self, name: str, version: str | None = None) -> tuple[RegistryEntry, ArgoPackage]:
        entry = self.get(name, version)
        path = f"/download/{urllib.parse.quote(name)}"
        blob = self._get(path, version=version)
        return entry, ArgoPackage.from_bytes(blob)

    def publish(self, package: ArgoPackage, signature: Signature) -> RegistryEntry:
        url = f"{self.base_url}{_API}/publish"
        request = urllib.request.Request(
            url,
            data=package.to_bytes(),
            method="POST",
            headers={
                "Content-Type": "application/octet-stream",
                "X-Argo-Publisher": signature.publisher,
                "X-Argo-Signature": signature.value,
                "X-Argo-Algorithm": signature.algorithm,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                return RegistryEntry.from_dict(json.loads(resp.read()))
        except urllib.error.HTTPError as exc:
            raise RegistryError(self._http_message(exc)) from exc
        except urllib.error.URLError as exc:
            raise RegistryError(f"cannot reach hub at {self.base_url}: {exc}") from exc

    def health(self) -> bool:
        """True if the remote hub answers its health probe."""
        try:
            return self._get_json("/health").get("status") == "ok"
        except RegistryError:
            return False
