"""L0 — in-process working memory.

Spec section 4.3: a `deque(maxlen=N)` per user. The fastest layer — used
for the current session view. It lives for the lifetime of the process.
"""

from __future__ import annotations

from collections import defaultdict, deque


class WorkingMemory:
    """In-memory copy of the last N messages, per user."""

    def __init__(self, maxlen: int = 200) -> None:
        self._maxlen = maxlen
        self._store: dict[str, deque[dict]] = defaultdict(
            lambda: deque(maxlen=maxlen)
        )

    def add(self, user_id: str, role: str, content: str, **meta) -> None:
        self._store[user_id].append({"role": role, "content": content, **meta})

    def history(self, user_id: str, limit: int | None = None) -> list[dict]:
        items = list(self._store.get(user_id, ()))
        return items[-limit:] if limit else items

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)

    def users(self) -> list[str]:
        return list(self._store.keys())
