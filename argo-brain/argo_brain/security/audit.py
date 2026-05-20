"""Append-only audit log (spec sections 4.1 / 10).

Records security-relevant events in a SQLite database. The log is
append-only by design: this module deliberately provides no update or
delete operations.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

# DDL for the audit table. `id` is an autoincrement primary key and `ts`
# stores a UTC ISO-8601 timestamp.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    action   TEXT NOT NULL,
    tool     TEXT,
    detail   TEXT NOT NULL DEFAULT '',
    severity TEXT NOT NULL DEFAULT 'info'
)
"""


def _utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class AuditLog:
    """An append-only, SQLite-backed audit log."""

    def __init__(self, db_path: str) -> None:
        """Open (or create) the audit database at `db_path`.

        Args:
            db_path: Filesystem path to the SQLite database. The special
                value ":memory:" creates an in-memory database.
        """
        self.db_path = db_path
        # check_same_thread=False keeps the connection usable if the
        # caller hands it across threads; access remains serialized here.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def log(
        self,
        user_id: str,
        action: str,
        tool: str | None = None,
        detail: str = "",
        severity: str = "info",
    ) -> int:
        """Append a single event to the audit log.

        Args:
            user_id: Identifier of the acting user.
            action: Short description of what happened.
            tool: Optional name of the tool involved.
            detail: Optional free-form detail string.
            severity: Severity level (e.g. "info", "warning", "error").

        Returns:
            The autoincremented row id of the inserted record.
        """
        cursor = self._conn.execute(
            "INSERT INTO audit_log (ts, user_id, action, tool, detail, severity) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_utc_now_iso(), user_id, action, tool, detail, severity),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def _query(self, where: str, params: tuple, limit: int) -> list[dict]:
        """Run a SELECT against the log, newest-first, and return dicts."""
        sql = "SELECT * FROM audit_log"
        if where:
            sql += " WHERE " + where
        # Order by id DESC so newest rows come first even when several
        # rows share the same timestamp.
        sql += " ORDER BY id DESC LIMIT ?"
        rows = self._conn.execute(sql, params + (limit,)).fetchall()
        return [dict(row) for row in rows]

    def recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent entries, newest first.

        Args:
            limit: Maximum number of rows to return.

        Returns:
            A list of row dictionaries ordered newest-first.
        """
        return self._query("", (), limit)

    def by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        """Return the most recent entries for a given user.

        Args:
            user_id: User identifier to filter on.
            limit: Maximum number of rows to return.

        Returns:
            A list of row dictionaries ordered newest-first.
        """
        return self._query("user_id = ?", (user_id,), limit)

    def by_severity(self, severity: str, limit: int = 50) -> list[dict]:
        """Return the most recent entries with a given severity.

        Args:
            severity: Severity level to filter on.
            limit: Maximum number of rows to return.

        Returns:
            A list of row dictionaries ordered newest-first.
        """
        return self._query("severity = ?", (severity,), limit)

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()
