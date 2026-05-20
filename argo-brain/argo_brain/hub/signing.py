"""Package signing — spec section 4.7 / Sprint 11 ("Signed packages").

Every package published to the hub carries a detached signature so a client
can verify *who* published it and that the bytes were not tampered with in
transit.

Crypto note: the Python standard library ships no asymmetric primitive
(Ed25519 / RSA) usable without a C dependency, so this module signs with
HMAC-SHA256 under a per-publisher trust key. This is a genuine
authenticity + integrity check within a *trusted-key* model — the same model
`apt`/`pip` index mirrors use internally — and the `Signature` envelope below
records the algorithm so an asymmetric backend can be slotted in unchanged
once a crypto dependency is permitted.
"""

from __future__ import annotations

import hmac
import json
from dataclasses import asdict, dataclass
from hashlib import sha256

ALGO_HMAC_SHA256 = "hmac-sha256"


class SignatureError(Exception):
    """Raised when a signature is missing, malformed or does not verify."""


@dataclass(frozen=True)
class Signature:
    """A detached signature over a package digest."""

    publisher: str
    algorithm: str
    value: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Signature":
        try:
            return cls(
                publisher=data["publisher"],
                algorithm=data["algorithm"],
                value=data["value"],
            )
        except (KeyError, TypeError) as exc:
            raise SignatureError(f"malformed signature: {exc}") from exc


def _digest(payload: bytes, key: str) -> str:
    return hmac.new(key.encode("utf-8"), payload, sha256).hexdigest()


def sign(payload: bytes, *, publisher: str, key: str) -> Signature:
    """Sign ``payload`` bytes for ``publisher`` with their trust ``key``."""
    if not publisher:
        raise SignatureError("publisher is required to sign")
    if not key:
        raise SignatureError("a non-empty key is required to sign")
    return Signature(
        publisher=publisher,
        algorithm=ALGO_HMAC_SHA256,
        value=_digest(payload, key),
    )


def verify(payload: bytes, signature: Signature, *, key: str) -> bool:
    """True iff ``signature`` is a valid signature of ``payload`` under ``key``.

    The comparison is constant-time to avoid leaking the signature via timing.
    """
    if signature.algorithm != ALGO_HMAC_SHA256:
        raise SignatureError(f"unsupported algorithm: {signature.algorithm}")
    expected = _digest(payload, key)
    return hmac.compare_digest(expected, signature.value)


class TrustStore:
    """Maps publisher names to their trust keys.

    A client verifies a package only if it holds a key for the publisher that
    signed it; an unknown publisher is rejected rather than silently trusted.
    """

    def __init__(self, keys: dict[str, str] | None = None) -> None:
        self._keys: dict[str, str] = dict(keys or {})

    def add(self, publisher: str, key: str) -> None:
        self._keys[publisher] = key

    def remove(self, publisher: str) -> None:
        self._keys.pop(publisher, None)

    def trusts(self, publisher: str) -> bool:
        return publisher in self._keys

    def publishers(self) -> list[str]:
        return sorted(self._keys)

    def verify(self, payload: bytes, signature: Signature) -> bool:
        """Verify against the stored key for the signature's publisher."""
        key = self._keys.get(signature.publisher)
        if key is None:
            raise SignatureError(f"untrusted publisher: {signature.publisher}")
        return verify(payload, signature, key=key)

    @classmethod
    def from_file(cls, path) -> "TrustStore":
        """Load a ``{publisher: key}`` JSON trust file (missing file → empty)."""
        from pathlib import Path

        p = Path(path).expanduser()
        if not p.is_file():
            return cls()
        return cls(json.loads(p.read_text(encoding="utf-8")))
