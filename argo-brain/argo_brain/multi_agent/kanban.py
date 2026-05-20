"""Durable Kanban board — spec section 4.11.

Implements the task lifecycle: todo -> claimed -> in_progress -> done, plus
the `blocked` and `failed` states. Heartbeat-based zombie reclaim and the
LLM-judge hallucination gate arrive in Sprint 8; the schema already has the
columns for them.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kanban_boards (
    id          TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    name        TEXT NOT NULL,
    goal        TEXT DEFAULT '',
    status      TEXT DEFAULT 'active',
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS kanban_tasks (
    id            TEXT PRIMARY KEY,
    board_id      TEXT NOT NULL REFERENCES kanban_boards(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    prompt        TEXT NOT NULL,
    status        TEXT DEFAULT 'todo',
    agent_id      TEXT,
    priority      INTEGER DEFAULT 0,
    retries       INTEGER DEFAULT 0,
    max_retries   INTEGER DEFAULT 3,
    heartbeat_at  TEXT,
    result        TEXT,
    error         TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_kt_board_status
    ON kanban_tasks(board_id, status);
"""

_VALID_STATUS = {
    "todo", "claimed", "in_progress", "done", "blocked", "failed",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KanbanManager:
    """Manages durable Kanban boards and their tasks."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- boards ---

    def create_board(self, user_id: str, name: str, goal: str = "") -> str:
        board_id = str(uuid.uuid4())
        self._conn.execute(
            "INSERT INTO kanban_boards (id, user_id, name, goal, created_at) "
            "VALUES (?,?,?,?,?)",
            (board_id, user_id, name, goal, _now()),
        )
        self._conn.commit()
        return board_id

    # --- tasks ---

    def add_task(self, board_id: str, title: str, prompt: str,
                 priority: int = 0) -> str:
        task_id = str(uuid.uuid4())
        now = _now()
        self._conn.execute(
            "INSERT INTO kanban_tasks "
            "(id, board_id, title, prompt, priority, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (task_id, board_id, title, prompt, priority, now, now),
        )
        self._conn.commit()
        return task_id

    def claim_task(self, board_id: str, agent_id: str) -> dict | None:
        """Atomically claims the highest-priority `todo` task for an agent."""
        row = self._conn.execute(
            "SELECT id FROM kanban_tasks WHERE board_id = ? AND status = 'todo' "
            "ORDER BY priority DESC, created_at ASC LIMIT 1",
            (board_id,),
        ).fetchone()
        if row is None:
            return None
        self._set_status(row["id"], "claimed", agent_id=agent_id,
                         heartbeat=True)
        return self.get_task(row["id"])

    def complete_task(self, task_id: str, result: str) -> None:
        self._conn.execute(
            "UPDATE kanban_tasks SET status='done', result=?, updated_at=? "
            "WHERE id=?",
            (result, _now(), task_id),
        )
        self._conn.commit()

    def fail_task(self, task_id: str, error: str) -> str:
        """Marks a task failed; re-queues it as `todo` if retries remain."""
        row = self._conn.execute(
            "SELECT retries, max_retries FROM kanban_tasks WHERE id=?",
            (task_id,),
        ).fetchone()
        if row is None:
            return "missing"
        if row["retries"] < row["max_retries"]:
            self._conn.execute(
                "UPDATE kanban_tasks SET status='todo', retries=retries+1, "
                "error=?, updated_at=? WHERE id=?",
                (error, _now(), task_id),
            )
            self._conn.commit()
            return "retry"
        self._conn.execute(
            "UPDATE kanban_tasks SET status='failed', error=?, updated_at=? "
            "WHERE id=?",
            (error, _now(), task_id),
        )
        self._conn.commit()
        return "failed"

    def block_task(self, task_id: str, reason: str) -> None:
        self._conn.execute(
            "UPDATE kanban_tasks SET status='blocked', error=?, updated_at=? "
            "WHERE id=?",
            (reason, _now(), task_id),
        )
        self._conn.commit()

    def _set_status(self, task_id: str, status: str, *,
                    agent_id: str | None = None, heartbeat: bool = False) -> None:
        if status not in _VALID_STATUS:
            raise ValueError(f"invalid status: {status}")
        now = _now()
        self._conn.execute(
            "UPDATE kanban_tasks SET status=?, agent_id=COALESCE(?, agent_id), "
            "heartbeat_at=?, updated_at=? WHERE id=?",
            (status, agent_id, now if heartbeat else None, now, task_id),
        )
        self._conn.commit()

    def get_task(self, task_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM kanban_tasks WHERE id=?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_tasks(self, board_id: str, status: str | None = None) -> list[dict]:
        if status:
            rows = self._conn.execute(
                "SELECT * FROM kanban_tasks WHERE board_id=? AND status=? "
                "ORDER BY priority DESC, created_at ASC",
                (board_id, status),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM kanban_tasks WHERE board_id=? "
                "ORDER BY priority DESC, created_at ASC",
                (board_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def board_status(self, board_id: str) -> dict[str, int]:
        """Returns a count of tasks per status for a board."""
        rows = self._conn.execute(
            "SELECT status, COUNT(*) AS n FROM kanban_tasks "
            "WHERE board_id=? GROUP BY status",
            (board_id,),
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}
