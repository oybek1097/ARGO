"""Trajectory collection and export (spec section: trajectory export).

A `TrajectoryCollector` records agent interactions in memory and can export
them as ShareGPT conversations or plain SFT instruction/output pairs, either
as Python objects or written to disk as JSONL.
"""

from __future__ import annotations

import json
import os


class TrajectoryCollector:
    """Records agent interactions for RL / SFT use.

    Each recorded trajectory is a dict with the user input, the agent output,
    the tools used, the model name, a success flag and the duration.
    """

    def __init__(self) -> None:
        # Internal list of trajectory dicts, kept in insertion order.
        self._trajectories: list[dict] = []

    def record(
        self,
        user_input: str,
        output: str,
        tools_used: list[str],
        model: str,
        success: bool,
        duration_ms: int = 0,
    ) -> None:
        """Appends a single trajectory to the collection."""
        self._trajectories.append(
            {
                "user_input": user_input,
                "output": output,
                # Copy the list so later mutation by the caller is harmless.
                "tools_used": list(tools_used),
                "model": model,
                "success": bool(success),
                "duration_ms": int(duration_ms),
            }
        )

    def all(self) -> list[dict]:
        """Returns a shallow copy of every recorded trajectory."""
        return list(self._trajectories)

    def count(self) -> int:
        """Returns the number of recorded trajectories."""
        return len(self._trajectories)

    def clear(self) -> None:
        """Removes all recorded trajectories."""
        self._trajectories.clear()

    def successful(self) -> list[dict]:
        """Returns only the trajectories whose `success` flag is true."""
        return [t for t in self._trajectories if t["success"]]

    def export_sharegpt(self, only_successful: bool = False) -> list[dict]:
        """Converts trajectories to ShareGPT conversation format.

        Each entry looks like::

            {"conversations": [
                {"from": "human", "value": <user_input>},
                {"from": "gpt", "value": <output>},
            ]}
        """
        source = self.successful() if only_successful else self._trajectories
        return [
            {
                "conversations": [
                    {"from": "human", "value": t["user_input"]},
                    {"from": "gpt", "value": t["output"]},
                ]
            }
            for t in source
        ]

    def export_sft(self, only_successful: bool = False) -> list[dict]:
        """Converts trajectories to SFT instruction/output format.

        Each entry looks like ``{"instruction": ..., "output": ...}``.
        """
        source = self.successful() if only_successful else self._trajectories
        return [
            {"instruction": t["user_input"], "output": t["output"]}
            for t in source
        ]

    def export_jsonl(
        self, path: str, fmt: str = "sharegpt", only_successful: bool = False
    ) -> int:
        """Writes the chosen format as JSONL to `path`.

        `fmt` must be either "sharegpt" or "sft". Returns the number of rows
        written (one JSON object per line).
        """
        if fmt == "sharegpt":
            rows = self.export_sharegpt(only_successful=only_successful)
        elif fmt == "sft":
            rows = self.export_sft(only_successful=only_successful)
        else:
            raise ValueError(f"unknown export format: {fmt!r}")

        # Make sure the parent directory exists before writing.
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False))
                fh.write("\n")
        return len(rows)
