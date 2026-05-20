"""Memory manager — unifies L0 + L1 under a single API.

Spec section 4.3: `MemoryManager` is a single interface over L0 (working),
L1 (persistent) and L2 (vector). At the skeleton stage only L0 + L1 are
present. L2 (ChromaDB/Qdrant) will be added in Sprint 2 as `vector.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from argo_brain.memory.persistent import PersistentMemory
from argo_brain.memory.working import WorkingMemory


@dataclass
class Message:
    """A single conversation message."""

    role: str          # "user" | "assistant" | "system" | "tool"
    content: str
    language: str = "en"
    channel: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "language": self.language,
            "channel": self.channel,
        }


class MemoryManager:
    """A single entry point over L0 + L1 memory."""

    def __init__(self, db_path: Path | str, working_size: int = 200) -> None:
        self.working = WorkingMemory(maxlen=working_size)
        self.persistent = PersistentMemory(db_path)

    def close(self) -> None:
        self.persistent.close()

    async def add(
        self,
        user_id: str,
        role: str,
        content: str,
        *,
        language: str = "en",
        channel: str = "unknown",
        session_id: str | None = None,
    ) -> None:
        """Writes a message to L0 and L1 at the same time."""
        self.working.add(user_id, role, content, language=language, channel=channel)
        await self.persistent.add(
            user_id, role, content,
            language=language, channel=channel, session_id=session_id,
        )

    async def history(self, user_id: str, limit: int = 20) -> list[dict]:
        """History: L0 first (fast), falling back to L1 if empty."""
        l0 = self.working.history(user_id, limit)
        if l0:
            return l0
        return await self.persistent.history(user_id, limit)

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        """Non-semantic full-text search via L1 FTS5."""
        return await self.persistent.search(user_id, query, limit)

    async def profile(self, user_id: str) -> dict | None:
        return await self.persistent.profile(user_id)

    async def ensure_profile(self, user_id: str, language: str = "en") -> dict:
        prof = await self.persistent.profile(user_id)
        if prof is None:
            await self.persistent.upsert_profile(user_id, language=language)
            prof = await self.persistent.profile(user_id)
        assert prof is not None
        return prof
