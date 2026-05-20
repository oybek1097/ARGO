"""Handoff manager — spec section 4: /handoff and /claim.

Implements session handoff tickets: one user/agent hands a session off to a
target, and the target later claims it, receiving the goal and a snapshot of
conversation history. Backed by SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS handoff_tickets (
    id                TEXT PRIMARY KEY,
    from_user         TEXT NOT NULL,
    to_target         TEXT NOT NULL,
    session_id        TEXT NOT NULL,
    goal              TEXT DEFAULT '',
    history_snapshot  TEXT DEFAULT '[]',
    status            TEXT DEFAULT 'pending',
    claimed_by        TEXT,
    created_at        TEXT NOT NULL,
    claimed_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_handoff_target_status
    ON handoff_tickets(to_target, status);
"""


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class HandoffManager:
    """Creates, claims and queries session handoff tickets in SQLite."""

    def __init__(self, db_path: str) -> None:
        """Initialize the manager and ensure the schema exists at ``db_path``."""
        self.db_path = db_path
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with row access by column name."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict:
        """Convert a ticket row into a plain dict, decoding the snapshot JSON."""
        data = dict(row)
        try:
            data["history_snapshot"] = json.loads(data.get("history_snapshot") or "[]")
        except (json.JSONDecodeError, TypeError):
            data["history_snapshot"] = []
        return data

    def create(
        self,
        from_user: str,
        to_target: str,
        session_id: str,
        goal: str,
        history_snapshot: list,
    ) -> str:
        """Create a pending handoff ticket and return its id."""
        ticket_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO handoff_tickets
                   (id, from_user, to_target, session_id, goal,
                    history_snapshot, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                (
                    ticket_id,
                    from_user,
                    to_target,
                    session_id,
                    goal,
                    json.dumps(history_snapshot or []),
                    _now(),
                ),
            )
        return ticket_id

    def claim(self, ticket_id: str, claimed_by: str) -> dict | None:
        """Claim a pending ticket.

        Returns the ticket data if the claim succeeded, or None if the ticket
        does not exist or has already been claimed.
        """
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE handoff_tickets
                   SET status = 'claimed', claimed_by = ?, claimed_at = ?
                   WHERE id = ? AND status = 'pending'""",
                (claimed_by, _now(), ticket_id),
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM handoff_tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def pending(self, to_target: str) -> list[dict]:
        """List unclaimed (pending) tickets addressed to ``to_target``."""
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM handoff_tickets
                   WHERE to_target = ? AND status = 'pending'
                   ORDER BY created_at ASC""",
                (to_target,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def get(self, ticket_id) -> dict | None:
        """Return a single ticket by id, or None if not found."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM handoff_tickets WHERE id = ?", (ticket_id,)
            ).fetchone()
        return self._row_to_dict(row) if row else None
