"""Emoji Stripper — bundled ARGO plugin.

Removes emoji and other non-text symbols from responses for channels that render them poorly.
"""

from __future__ import annotations

import re

from argo_brain.plugin.api import ArgoPlugin


class EmojiStripperPlugin(ArgoPlugin):
    """Removes emoji characters from responses."""

    name = "emoji-stripper"
    version = "1.0.0"
    description = "Strips emoji from agent responses."

    _EMOJI = re.compile(
        "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
    )

    def strip(self, text: str) -> str:
        """Return text with emoji characters removed."""
        return self._EMOJI.sub("", text)

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        if self.strip(content) != content:
            self.event("emoji.stripped", user_id=user_id)
