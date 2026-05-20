"""Authentication primitives (spec section 10).

Provides two building blocks for the ARGO Agent auth model:

* API keys generated with a cryptographically secure RNG, hashed at rest
  with PBKDF2-HMAC-SHA256 and verified in constant time.
* A JSON Web Token implementation for the HS256 algorithm, including
  signing, verification and validation of the ``exp`` / ``iat`` / ``nbf``
  claims.

Design notes:

* PBKDF2-HMAC-SHA256 (``hashlib.pbkdf2_hmac``) is used for API-key
  hashing rather than ``hashlib.scrypt``. PBKDF2 is in the standard
  library, FIPS-approved, has no memory-tuning parameters to mis-set and
  is entirely sufficient for high-entropy machine-generated keys (a
  32-byte random key is not subject to dictionary attacks). The
  iteration count is stored alongside the hash so it can be raised
  later without breaking existing keys.
* RS256 is intentionally out of scope: it needs asymmetric crypto that
  the standard library does not provide for JWT-style signing. It is
  noted here as a roadmap item; HS256 is the spec default.

This module depends only on the Python 3.12 standard library.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time


class AuthError(Exception):
    """Raised when authentication fails.

    Covers malformed or tampered tokens, expired/not-yet-valid tokens,
    unsupported algorithms and signature mismatches.
    """


# --------------------------------------------------------------------------
# Base64url helpers (RFC 7515 / JWT use unpadded base64url).
# --------------------------------------------------------------------------


def _b64url_encode(data: bytes) -> str:
    """Encode bytes as unpadded base64url text."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    """Decode unpadded base64url text back to bytes.

    Raises:
        AuthError: If the input is not valid base64url.
    """
    pad = "=" * (-len(text) % 4)
    try:
        return base64.urlsafe_b64decode(text + pad)
    except (ValueError, TypeError) as exc:
        raise AuthError("malformed base64url segment") from exc


# --------------------------------------------------------------------------
# API keys.
# --------------------------------------------------------------------------

# PBKDF2 parameters. The iteration count is encoded into every stored
# hash, so raising this value only affects newly created keys.
_PBKDF2_ITERATIONS = 240_000
_PBKDF2_SALT_BYTES = 16
_API_KEY_BYTES = 32
_API_KEY_PREFIX = "argo_"


def generate_api_key() -> str:
    """Generate a new high-entropy API key.

    The key carries an ``argo_`` prefix for easy identification in logs
    and config files. The random portion is 32 bytes (256 bits) of
    secure randomness, base64url-encoded.

    Returns:
        A freshly generated API key string. Show this to the user once;
        only its hash should be stored.
    """
    return _API_KEY_PREFIX + _b64url_encode(secrets.token_bytes(_API_KEY_BYTES))


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage at rest.

    Args:
        api_key: The plaintext API key to hash.

    Returns:
        A self-describing hash string of the form
        ``pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>``.
    """
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256", api_key.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(_PBKDF2_ITERATIONS),
            _b64url_encode(salt),
            _b64url_encode(derived),
        ]
    )


def verify_api_key(api_key: str, stored_hash: str) -> bool:
    """Verify a plaintext API key against a stored hash.

    The comparison uses :func:`hmac.compare_digest` so the running time
    does not depend on how many leading bytes match.

    Args:
        api_key: The plaintext API key presented by the caller.
        stored_hash: A hash previously produced by :func:`hash_api_key`.

    Returns:
        ``True`` if the key matches the stored hash, ``False`` otherwise.
        A malformed ``stored_hash`` yields ``False`` rather than raising.
    """
    try:
        algorithm, iterations_text, salt_b64, hash_b64 = stored_hash.split("$")
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    try:
        iterations = int(iterations_text)
        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(hash_b64)
    except (ValueError, AuthError):
        return False
    derived = hashlib.pbkdf2_hmac(
        "sha256", api_key.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(derived, expected)


# --------------------------------------------------------------------------
# JWT (HS256).
# --------------------------------------------------------------------------

_JWT_ALGORITHM = "HS256"


def _sign_hs256(signing_input: bytes, secret: str) -> bytes:
    """Compute the HMAC-SHA256 signature of a JWT signing input."""
    return hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()


def jwt_encode(
    payload: dict,
    secret: str,
    *,
    expires_in: int | None = None,
) -> str:
    """Encode and sign a JWT using HS256.

    Args:
        payload: The claims to embed. Copied before mutation; the caller's
            dict is left untouched.
        secret: The shared secret used for the HMAC signature.
        expires_in: Optional lifetime in seconds. When given, an ``exp``
            claim is added relative to now. An ``iat`` claim is always
            added if absent.

    Returns:
        The compact-serialized JWT string (``header.payload.signature``).
    """
    header = {"alg": _JWT_ALGORITHM, "typ": "JWT"}
    claims = dict(payload)
    now = int(time.time())
    claims.setdefault("iat", now)
    if expires_in is not None:
        claims["exp"] = now + int(expires_in)

    header_segment = _b64url_encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_segment = _b64url_encode(
        json.dumps(claims, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = _sign_hs256(signing_input, secret)
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def jwt_decode(
    token: str,
    secret: str,
    *,
    verify_exp: bool = True,
    leeway: int = 0,
) -> dict:
    """Verify and decode a JWT signed with HS256.

    Args:
        token: The compact-serialized JWT string.
        secret: The shared secret the token must have been signed with.
        verify_exp: Whether to enforce the ``exp`` / ``nbf`` claims.
        leeway: Clock-skew allowance in seconds applied to time claims.

    Returns:
        The decoded claims dictionary.

    Raises:
        AuthError: If the token is malformed, uses an unsupported
            algorithm, fails the signature check, has expired or is not
            yet valid.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("token must have three segments")
    header_segment, payload_segment, signature_segment = parts

    try:
        header = json.loads(_b64url_decode(header_segment))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("invalid token header") from exc
    if not isinstance(header, dict) or header.get("alg") != _JWT_ALGORITHM:
        # Reject "alg": "none" and any algorithm we do not implement.
        raise AuthError(f"unsupported algorithm: {header.get('alg')!r}")

    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = _sign_hs256(signing_input, secret)
    actual_signature = _b64url_decode(signature_segment)
    # Constant-time compare so a tampered signature cannot be probed
    # byte-by-byte via timing.
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise AuthError("signature verification failed")

    try:
        claims = json.loads(_b64url_decode(payload_segment))
    except (ValueError, json.JSONDecodeError) as exc:
        raise AuthError("invalid token payload") from exc
    if not isinstance(claims, dict):
        raise AuthError("token payload must be a JSON object")

    if verify_exp:
        now = int(time.time())
        exp = claims.get("exp")
        if exp is not None and now > int(exp) + leeway:
            raise AuthError("token has expired")
        nbf = claims.get("nbf")
        if nbf is not None and now + leeway < int(nbf):
            raise AuthError("token is not yet valid")

    return claims


__all__ = [
    "AuthError",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "jwt_encode",
    "jwt_decode",
]
