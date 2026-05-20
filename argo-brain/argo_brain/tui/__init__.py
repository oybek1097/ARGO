"""ARGO brain terminal UI package.

Exposes the interactive `TUI` loop and the pure `SlashCommandRouter` that
parses slash commands. Both are stdlib-only.
"""

from __future__ import annotations

from argo_brain.tui.app import SlashCommandRouter, TUI

__all__ = ["TUI", "SlashCommandRouter"]
