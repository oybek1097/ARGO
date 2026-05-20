"""L2 — semantic (vector) memory.

Spec section 4.3: `VectorMemory` is the L2 semantic layer of the unified
memory stack (L0 working, L1 persistent, L2 vector). It stores text entries
and retrieves them by semantic similarity rather than exact keyword match.

A real deployment would back this with an embedding model and a vector
database (ChromaDB/Qdrant). To keep the project pure-stdlib and fully
deterministic, this module ships a self-contained hashing bag-of-words
vectorizer (`embed`) and an in-memory store scoped per user.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict

# Fixed embedding dimensionality. Any text maps to a vector of this length.
EMBED_DIM = 256

# Word tokenizer: runs of alphanumeric characters, Unicode aware.
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Splits text into lowercased word tokens."""
    return _TOKEN_RE.findall(text.lower())


def _hash_bucket(word: str) -> int:
    """Maps a word deterministically into one of EMBED_DIM buckets.

    Uses MD5 so the result is stable across processes and Python runs
    (unlike the built-in `hash`, which is salted per interpreter).
    """
    digest = hashlib.md5(word.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % EMBED_DIM


def embed(text: str) -> list[float]:
    """Embeds text into a fixed-dimension, L2-normalized vector.

    This is a hashing bag-of-words vectorizer: each token is hashed into a
    bucket of a length-`EMBED_DIM` vector, occurrence counts are accumulated,
    and the resulting vector is L2-normalized so cosine similarity reduces
    to a plain dot product.

    The mapping is deterministic — identical input always yields an
    identical vector. An empty / token-less text yields an all-zero vector.
    """
    vec = [0.0] * EMBED_DIM
    for word in _tokenize(text):
        vec[_hash_bucket(word)] += 1.0

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0.0:
        vec = [x / norm for x in vec]
    return vec


def _cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors.

    Vectors produced by `embed` are already L2-normalized, so this is just
    their dot product. Returns 0.0 if either vector is a zero vector.
    """
    return sum(x * y for x, y in zip(a, b))


class VectorMemory:
    """L2 semantic memory — per-user store with similarity search."""

    def __init__(self) -> None:
        # Maps user_id -> list of entry dicts.
        # Each entry: {"text": str, "metadata": dict, "vector": list[float]}
        self._store: dict[str, list[dict]] = defaultdict(list)

    def add(
        self,
        user_id: str,
        text: str,
        metadata: dict | None = None,
    ) -> None:
        """Stores a text entry for `user_id`, embedding it on insertion."""
        self._store[user_id].append(
            {
                "text": text,
                "metadata": metadata or {},
                "vector": embed(text),
            }
        )

    def search(self, user_id: str, query: str, k: int = 5) -> list[dict]:
        """Returns the top-`k` most similar entries for `user_id`.

        Results are ordered by descending cosine similarity. Each result is
        a dict with `text`, `score` and `metadata`. Returns an empty list if
        the user has no stored entries.
        """
        entries = self._store.get(user_id, [])
        if not entries:
            return []

        query_vec = embed(query)
        scored = [
            {
                "text": entry["text"],
                "score": _cosine(query_vec, entry["vector"]),
                "metadata": entry["metadata"],
            }
            for entry in entries
        ]
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[: max(0, k)]

    def count(self, user_id: str) -> int:
        """Returns the number of entries stored for `user_id`."""
        return len(self._store.get(user_id, []))
