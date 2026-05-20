"""L1 — persistent memory (SQLite WAL + FTS5).

A skeleton subset of the schema from spec section 4.3: `messages`,
`messages_fts`, `user_profiles`. The full schema (sessions, skills, kanban,
audit, ...) will be added across Sprints 2-8.

Skeleton stage: stdlib `sqlite3` (synchronous) instead of `aiosqlite`. The
API is `async` to allow a transparent migration to `aiosqlite` later.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS messages (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    session_id TEXT,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    language   TEXT DEFAULT 'en',
    channel    TEXT DEFAULT 'unknown',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_msg_user_time
    ON messages(user_id, created_at DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content, user_id UNINDEXED, language UNINDEXED,
    content='messages', content_rowid='rowid',
    tokenize='unicode61 remove_diacritics 1'
);

CREATE TRIGGER IF NOT EXISTS msg_ai AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts(rowid, content, user_id, language)
    VALUES (new.rowid, new.content, new.user_id, new.language);
END;
CREATE TRIGGER IF NOT EXISTS msg_ad AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts(messages_fts, rowid, content, user_id, language)
    VALUES ('delete', old.rowid, old.content, old.user_id, old.language);
END;

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id    TEXT PRIMARY KEY,
    name       TEXT,
    language   TEXT DEFAULT 'en',
    timezone   TEXT DEFAULT 'UTC',
    summary    TEXT DEFAULT '',
    task_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PersistentMemory:
    """SQLite-based L1 memory: messages, FTS search, profiles."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- messages ---

    async def add(
        self,
        user_id: str,
        role: str,
        content: str,
        *,
        language: str = "en",
        channel: str = "unknown",
        session_id: str | None = None,
    ) -> str:
        msg_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO messages "
            "(id, user_id, session_id, role, content, language, channel, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (msg_id, user_id, session_id, role, content, language, channel, _now()),
        )
        self._conn.commit()
        return msg_id

    async def history(self, user_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT role, content, language, channel, created_at FROM messages "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]

    async def search(self, user_id: str, query: str, limit: int = 10) -> list[dict]:
        """FTS5 full-text search (scoped to a single user)."""
        if not query.strip():
            return []
        try:
            rows = self._conn.execute(
                "SELECT m.role, m.content, m.created_at "
                "FROM messages_fts f JOIN messages m ON m.rowid = f.rowid "
                "WHERE messages_fts MATCH ? AND f.user_id = ? "
                "ORDER BY rank LIMIT ?",
                (query, user_id, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # FTS syntax error -> empty result (skeleton)
            return []
        return [dict(r) for r in rows]

    async def count(self, user_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM messages WHERE user_id = ?", (user_id,)
        ).fetchone()
        return int(row["n"])

    # --- profiles ---

    async def profile(self, user_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
        return dict(row) if row else None

    async def upsert_profile(
        self, user_id: str, *, name: str | None = None, language: str = "en"
    ) -> None:
        now = _now()
        self._conn.execute(
            "INSERT INTO user_profiles (user_id, name, language, created_at, updated_at) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "  name = COALESCE(excluded.name, user_profiles.name), "
            "  language = excluded.language, "
            "  updated_at = excluded.updated_at",
            (user_id, name, language, now, now),
        )
        self._conn.commit()
