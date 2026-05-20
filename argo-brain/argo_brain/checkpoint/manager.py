"""Checkpoint manager — auto-snapshot + rollback.

Snapshots a set of files into timestamped checkpoint directories so that the
agent can roll back to a known-good state. Stdlib only.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

_META_NAME = "checkpoint.json"
_FILES_DIRNAME = "files"


class CheckpointManager:
    """Creates, lists, restores and deletes file checkpoints under a base dir."""

    def __init__(self, base_dir: str) -> None:
        """Initialize the manager rooted at ``base_dir`` (created if missing)."""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create(self, label: str, files: list[str]) -> str:
        """Snapshot ``files`` into a new timestamped checkpoint directory.

        Files are copied into a ``files/`` subdirectory keyed by their basename.
        Missing source files are skipped. Returns the new checkpoint id.
        """
        now = datetime.now(timezone.utc)
        # Timestamp prefix keeps directories sortable; uuid suffix avoids clashes.
        checkpoint_id = now.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        cp_dir = self.base_dir / checkpoint_id
        files_dir = cp_dir / _FILES_DIRNAME
        files_dir.mkdir(parents=True, exist_ok=True)

        stored: list[dict] = []
        for f in files:
            src = Path(f)
            if not src.is_file():
                continue
            dest = files_dir / src.name
            shutil.copy2(src, dest)
            stored.append({"name": src.name, "original_path": str(src.resolve())})

        meta = {
            "id": checkpoint_id,
            "label": label,
            "created_at": now.isoformat(),
            "files": stored,
        }
        (cp_dir / _META_NAME).write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return checkpoint_id

    def _read_meta(self, cp_dir: Path) -> dict | None:
        """Return the parsed metadata for a checkpoint directory, or None."""
        meta_path = cp_dir / _META_NAME
        if not meta_path.is_file():
            return None
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def list(self) -> list[dict]:
        """List all checkpoints as dicts (id, label, created_at, file_count)."""
        result: list[dict] = []
        for cp_dir in sorted(self.base_dir.iterdir()):
            if not cp_dir.is_dir():
                continue
            meta = self._read_meta(cp_dir)
            if meta is None:
                continue
            result.append({
                "id": meta["id"],
                "label": meta.get("label", ""),
                "created_at": meta.get("created_at", ""),
                "file_count": len(meta.get("files", [])),
            })
        return result

    def restore(self, checkpoint_id: str, target_dir: str) -> int:
        """Restore a checkpoint's files into ``target_dir``.

        Returns the number of files restored. Raises ``KeyError`` if the
        checkpoint does not exist.
        """
        cp_dir = self.base_dir / checkpoint_id
        meta = self._read_meta(cp_dir)
        if meta is None:
            raise KeyError(f"unknown checkpoint: {checkpoint_id}")

        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        files_dir = cp_dir / _FILES_DIRNAME

        count = 0
        for entry in meta.get("files", []):
            src = files_dir / entry["name"]
            if not src.is_file():
                continue
            shutil.copy2(src, target / entry["name"])
            count += 1
        return count

    def delete(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint. Returns True if it existed and was removed."""
        cp_dir = self.base_dir / checkpoint_id
        if not cp_dir.is_dir():
            return False
        shutil.rmtree(cp_dir)
        return True
