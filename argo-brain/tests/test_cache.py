"""Tests for the session / prompt cache subsystem (spec section 4.2).

Covers the deterministic ``fingerprint`` helper and the per-user, TTL-scoped
``SessionCache``. A fake clock is injected into the cache so that TTL expiry
can be exercised without real sleeping.
"""

import unittest

from argo_brain.cache import SessionCache, fingerprint


class _FakeClock:
    """A manually advanceable clock for deterministic TTL testing."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        """Return the current fake time (in seconds)."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Move the fake clock forward by ``seconds``."""
        self.now += seconds


# Sample conversation prefixes reused across the fingerprint tests.
_MSGS_A = [
    {"role": "system", "content": "You are ARGO."},
    {"role": "user", "content": "Hello"},
]
_MSGS_B = [
    {"role": "system", "content": "You are ARGO."},
    {"role": "user", "content": "Goodbye"},
]


class TestFingerprint(unittest.TestCase):
    """Exercise the deterministic conversation fingerprint."""

    def test_deterministic_for_same_input(self) -> None:
        """Identical messages + model produce an identical digest."""
        self.assertEqual(
            fingerprint(_MSGS_A, "gpt-4"),
            fingerprint(_MSGS_A, "gpt-4"),
        )

    def test_returns_sha256_hex_digest(self) -> None:
        """The fingerprint is a 64-char lowercase hexadecimal string."""
        fp = fingerprint(_MSGS_A, "gpt-4")
        self.assertEqual(len(fp), 64)
        self.assertEqual(fp, fp.lower())
        int(fp, 16)  # Raises ValueError if not valid hexadecimal.

    def test_differs_for_different_messages(self) -> None:
        """Different message content yields a different digest."""
        self.assertNotEqual(
            fingerprint(_MSGS_A, "gpt-4"),
            fingerprint(_MSGS_B, "gpt-4"),
        )

    def test_differs_for_different_model(self) -> None:
        """The model name is folded into the digest, so it matters."""
        self.assertNotEqual(
            fingerprint(_MSGS_A, "gpt-4"),
            fingerprint(_MSGS_A, "claude-3"),
        )

    def test_independent_of_dict_key_order(self) -> None:
        """Key insertion order within messages does not affect the hash."""
        ordered = [{"role": "user", "content": "Hi"}]
        reordered = [{"content": "Hi", "role": "user"}]
        self.assertEqual(
            fingerprint(ordered, "gpt-4"),
            fingerprint(reordered, "gpt-4"),
        )

    def test_empty_messages_is_stable(self) -> None:
        """An empty conversation still produces a stable digest."""
        self.assertEqual(
            fingerprint([], "gpt-4"),
            fingerprint([], "gpt-4"),
        )


class TestSessionCache(unittest.TestCase):
    """Exercise SessionCache get/set/invalidate/clear/stats."""

    def test_set_get_round_trip(self) -> None:
        """A value stored with ``set`` is returned by ``get``."""
        cache = SessionCache()
        cache.set("user1", "key1", {"answer": 42})
        self.assertEqual(cache.get("user1", "key1"), {"answer": 42})

    def test_get_missing_key_returns_none(self) -> None:
        """``get`` returns None when the key was never stored."""
        cache = SessionCache()
        self.assertIsNone(cache.get("user1", "missing"))

    def test_get_missing_user_returns_none(self) -> None:
        """``get`` returns None when the user has no entries at all."""
        cache = SessionCache()
        cache.set("user1", "key1", "value")
        self.assertIsNone(cache.get("user2", "key1"))

    def test_entry_expires_after_ttl(self) -> None:
        """An entry past its TTL is no longer returned and is evicted."""
        clock = _FakeClock()
        cache = SessionCache(time_func=clock)
        cache.set("user1", "key1", "value", ttl=10)
        self.assertEqual(cache.get("user1", "key1"), "value")
        clock.advance(11)  # Move past the TTL.
        self.assertIsNone(cache.get("user1", "key1"))

    def test_entry_valid_just_before_ttl(self) -> None:
        """An entry remains available right up to (but before) its TTL."""
        clock = _FakeClock()
        cache = SessionCache(time_func=clock)
        cache.set("user1", "key1", "value", ttl=10)
        clock.advance(9)  # Still within the TTL window.
        self.assertEqual(cache.get("user1", "key1"), "value")

    def test_invalidate_drops_only_target_user(self) -> None:
        """``invalidate`` removes one user's entries, leaving others intact."""
        cache = SessionCache()
        cache.set("user1", "key1", "v1")
        cache.set("user2", "key2", "v2")
        cache.invalidate("user1")
        self.assertIsNone(cache.get("user1", "key1"))
        self.assertEqual(cache.get("user2", "key2"), "v2")

    def test_invalidate_unknown_user_is_noop(self) -> None:
        """Invalidating a user with no entries does not raise."""
        cache = SessionCache()
        cache.invalidate("nobody")  # Should simply be a no-op.

    def test_clear_removes_all_entries_and_resets_stats(self) -> None:
        """``clear`` empties the cache and resets hit/miss counters."""
        cache = SessionCache()
        cache.set("user1", "key1", "v1")
        cache.get("user1", "key1")        # 1 hit
        cache.get("user1", "missing")     # 1 miss
        cache.clear()
        self.assertIsNone(cache.get("user1", "key1"))
        # The lookup above is itself a miss after the reset.
        stats = cache.stats()
        self.assertEqual(stats, {"hits": 0, "misses": 1, "size": 0})

    def test_stats_counts_hits_and_misses(self) -> None:
        """``stats`` reports accurate hit, miss and size counts."""
        cache = SessionCache()
        cache.set("user1", "key1", "v1")
        cache.get("user1", "key1")        # hit
        cache.get("user1", "key1")        # hit
        cache.get("user1", "absent")      # miss
        stats = cache.stats()
        self.assertEqual(stats["hits"], 2)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)

    def test_stats_size_excludes_expired_entries(self) -> None:
        """Expired entries are not counted by ``stats`` and are evicted."""
        clock = _FakeClock()
        cache = SessionCache(time_func=clock)
        cache.set("user1", "key1", "v1", ttl=5)
        cache.set("user1", "key2", "v2", ttl=100)
        clock.advance(10)  # key1 expires, key2 survives.
        self.assertEqual(cache.stats()["size"], 1)

    def test_set_overwrites_existing_key(self) -> None:
        """Storing a key twice replaces the previous value."""
        cache = SessionCache()
        cache.set("user1", "key1", "old")
        cache.set("user1", "key1", "new")
        self.assertEqual(cache.get("user1", "key1"), "new")

    def test_expired_get_counts_as_miss(self) -> None:
        """A lookup of an expired entry increments the miss counter."""
        clock = _FakeClock()
        cache = SessionCache(time_func=clock)
        cache.set("user1", "key1", "value", ttl=5)
        clock.advance(10)
        cache.get("user1", "key1")  # expired -> miss
        self.assertEqual(cache.stats()["misses"], 1)

    def test_fingerprint_usable_as_cache_key(self) -> None:
        """A fingerprint can be used directly as a SessionCache key."""
        cache = SessionCache()
        key = fingerprint(_MSGS_A, "gpt-4")
        cache.set("user1", key, "cached-response")
        self.assertEqual(
            cache.get("user1", fingerprint(_MSGS_A, "gpt-4")),
            "cached-response",
        )


if __name__ == "__main__":
    unittest.main()
