"""Unified configuration.

At the skeleton stage a stdlib `dataclass` is used instead of
`pydantic-settings`. It will be migrated to `pydantic-settings` in Sprint 2
(the API stays the same).

Sources (in order of priority):
  1. Default values (below)
  2. The `~/.argo/config.json` file
  3. `ARGO_*` environment variables (highest priority)
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path


def _argo_home() -> Path:
    return Path(os.environ.get("ARGO_HOME", Path.home() / ".argo"))


@dataclass
class Settings:
    """Runtime settings for the ARGO brain."""

    data_dir: str = ""               # if empty -> ~/.argo/data
    db_path: str = ""                # if empty -> <data_dir>/argo.db
    ipc_socket: str = ""             # if empty -> ~/.argo/argo.sock
    model: str = "mock"              # "mock" | "claude-sonnet-4-6" | ...
    max_iterations: int = 8          # max iterations of the agent loop
    context_history: int = 20        # history length added to the prompt
    max_parallel_tools: int = 8      # parallel tool dispatch limit
    working_memory_size: int = 200   # L0 deque maxlen (per user)
    log_level: str = "INFO"

    # --- derived paths ---

    @property
    def resolved_data_dir(self) -> Path:
        return Path(self.data_dir) if self.data_dir else _argo_home() / "data"

    @property
    def resolved_db_path(self) -> Path:
        return Path(self.db_path) if self.db_path else self.resolved_data_dir / "argo.db"

    @property
    def resolved_ipc_socket(self) -> Path:
        return Path(self.ipc_socket) if self.ipc_socket else _argo_home() / "argo.sock"

    def ensure_dirs(self) -> None:
        self.resolved_data_dir.mkdir(parents=True, exist_ok=True)


_TRUTHY = {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    """Loads settings in the order: defaults -> config.json -> ARGO_* env."""
    values: dict[str, object] = {}

    cfg_file = _argo_home() / "config.json"
    if cfg_file.is_file():
        try:
            raw = json.loads(cfg_file.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                values.update(raw)
        except (json.JSONDecodeError, OSError):
            pass  # a corrupt config is silently ignored (skeleton)

    field_types = {f.name: f.type for f in fields(Settings)}
    for name in field_types:
        env_val = os.environ.get(f"ARGO_{name.upper()}")
        if env_val is not None:
            values[name] = env_val

    # type coercion
    coerced: dict[str, object] = {}
    for name, val in values.items():
        if name not in field_types:
            continue
        ftype = field_types[name]
        if ftype is int or ftype == "int":
            try:
                coerced[name] = int(val)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
        elif ftype is bool or ftype == "bool":
            coerced[name] = str(val).lower() in _TRUTHY
        else:
            coerced[name] = str(val)

    return Settings(**coerced)  # type: ignore[arg-type]
