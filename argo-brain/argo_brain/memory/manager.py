"""Memory manager — unifies L0 + L1 + L2 under a single API.

Spec section 4.3: `MemoryManager` is a single interface over L0 (working),
L1 (persistent) and L2 (vector). L2 uses the stdlib-only `VectorMemory`
(a hashing vectorizer); it can later be swapped for ChromaDB/Qdrant.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from argo_brain.memory.graph import KnowledgeGraph
from argo_brain.memory.persistent import PersistentMemory
from argo_brain.memory.vector import VectorMemory
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
        self.vector = VectorMemory()
        self.graph = KnowledgeGraph()

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
        """Writes a message to L0, L1 and the L2 vector store at once."""
        self.working.add(user_id, role, content, language=language, channel=channel)
        await self.persistent.add(
            user_id, role, content,
            language=language, channel=channel, session_id=session_id,
        )
        self.vector.add(user_id, content, metadata={"role": role})

    async def history(self, user_id: str, limit: int = 20) -> list[dict]:
        """History: L0 first (fast), falling back to L1 if empty."""
        l0 = self.working.history(user_id, limit)
        if l0:
            return l0
        return await self.persistent.history(user_id, limit)

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        """Non-semantic full-text search via L1 FTS5."""
        return await self.persistent.search(user_id, query, limit)

    def semantic_search(self, user_id: str, query: str, k: int = 5) -> list[dict]:
        """Semantic (cosine-similarity) search via the L2 vector store."""
        return self.vector.search(user_id, query, k)

    async def profile(self, user_id: str) -> dict | None:
        return await self.persistent.profile(user_id)

    async def ensure_profile(self, user_id: str, language: str = "en") -> dict:
        prof = await self.persistent.profile(user_id)
        if prof is None:
            await self.persistent.upsert_profile(user_id, language=language)
            prof = await self.persistent.profile(user_id)
        assert prof is not None
        return prof
