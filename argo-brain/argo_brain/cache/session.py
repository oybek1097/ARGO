"""In-memory session / prompt cache (spec section 4.2 — prompt cache lookup).

The agent loop builds a list of LLM messages on every request. When the same
conversation prefix is replayed against the same model, the response can be
served from a cache instead of calling the provider again. This module
provides:

* ``fingerprint`` — a deterministic SHA-256 hash of the messages + model that
  serves as the cache key.
* ``SessionCache`` — an in-memory, per-user, TTL-scoped cache with lazy
  expiry and basic hit/miss statistics.

Stdlib only: ``time``, ``hashlib``, ``json``.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Callable


def fingerprint(messages: list[dict], model: str) -> str:
    """Return a stable SHA-256 hash of ``messages`` plus ``model``.

    The hash is used as a cache key for prompt-cache lookups. It is stable
    across processes and runs: the messages are serialised with sorted keys
    so that dict ordering never affects the result, and the model name is
    folded into the same digest so different models never collide.

    Args:
        messages: The conversation messages (role/content dicts) as built by
            the agent loop. Any JSON-serialisable structure is accepted.
        model: The model identifier the messages would be sent to.

    Returns:
        A 64-character lowercase hexadecimal SHA-256 digest.
    """
    # ``sort_keys`` makes the serialisation independent of dict insertion
    # order; the compact separators keep the payload deterministic.
    payload = json.dumps(
        {"model": model, "messages": messages},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class SessionCache:
    """An in-memory TTL cache, scoped per user.

    Entries are keyed by ``(user_id, key)``. Each entry stores a value and an
    absolute expiry timestamp. Expired entries are evicted lazily — that is,
    only when they are accessed — so no background thread is required.

    The cache also tracks ``hits``, ``misses`` and current ``size`` which are
    exposed via :meth:`stats`.
    """

    def __init__(self, time_func: Callable[[], float] = time.monotonic) -> None:
        """Create an empty cache.

        Args:
            time_func: Callable returning the current time in seconds. It is
                injectable so tests can simulate the passage of time without
                sleeping. Defaults to :func:`time.monotonic`.
        """
        self._time = time_func
        # Nested mapping: user_id -> { key -> (value, expires_at) }.
        self._store: dict[str, dict[str, tuple[Any, float]]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, user_id: str, key: str) -> Any | None:
        """Return the cached value for ``(user_id, key)`` or ``None``.

        Returns ``None`` if the entry is missing or has passed its TTL. An
        expired entry is evicted as a side effect of this lookup.

        Args:
            user_id: The owning user's identifier.
            key: The cache key (typically a :func:`fingerprint`).

        Returns:
            The stored value, or ``None`` when missing/expired.
        """
        user_entries = self._store.get(user_id)
        if user_entries is None or key not in user_entries:
            self._misses += 1
            return None

        value, expires_at = user_entries[key]
        if self._time() >= expires_at:
            # Lazy eviction of the expired entry.
            del user_entries[key]
            if not user_entries:
                del self._store[user_id]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, user_id: str, key: str, value: Any, ttl: float = 3600) -> None:
        """Store ``value`` under ``(user_id, key)`` with a time-to-live.

        Args:
            user_id: The owning user's identifier.
            key: The cache key (typically a :func:`fingerprint`).
            value: The value to cache. Any object is accepted.
            ttl: Seconds the entry remains valid. Defaults to one hour.
        """
        expires_at = self._time() + ttl
        self._store.setdefault(user_id, {})[key] = (value, expires_at)

    def invalidate(self, user_id: str) -> None:
        """Drop every cached entry belonging to ``user_id``.

        Other users' entries are left untouched. A no-op if the user has no
        cached entries.

        Args:
            user_id: The user whose entries should be removed.
        """
        self._store.pop(user_id, None)

    def clear(self) -> None:
        """Remove all entries for all users.

        Statistics counters (hits/misses) are reset as well, returning the
        cache to its freshly constructed state.
        """
        self._store.clear()
        self._hits = 0
        self._misses = 0

    def stats(self) -> dict:
        """Return a snapshot of cache statistics.

        The reported ``size`` counts only entries that have not yet expired;
        encountering an expired entry here evicts it lazily.

        Returns:
            A dict with keys ``hits``, ``misses`` and ``size``.
        """
        now = self._time()
        size = 0
        for user_id in list(self._store.keys()):
            user_entries = self._store[user_id]
            for key in list(user_entries.keys()):
                _value, expires_at = user_entries[key]
                if now >= expires_at:
                    # Lazy eviction during the stats walk.
                    del user_entries[key]
                else:
                    size += 1
            if not user_entries:
                del self._store[user_id]
        return {"hits": self._hits, "misses": self._misses, "size": size}
