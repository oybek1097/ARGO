"""Whitespace Normalizer — bundled ARGO plugin.

Collapses excessive blank lines and trailing whitespace in responses for cleaner rendering.
"""

from __future__ import annotations

import re

from argo_brain.plugin.api import ArgoPlugin


class WhitespaceNormalizerPlugin(ArgoPlugin):
    """Tidies whitespace in responses."""

    name = "whitespace-normalizer"
    version = "1.0.0"
    description = "Normalizes whitespace in agent responses."

    _TRAILING = re.compile(r"[ \t]+$", re.MULTILINE)
    _BLANKS = re.compile(r"\n{3,}")

    def normalize(self, text: str) -> str:
        """Return text with trailing spaces and extra blank lines removed."""
        text = self._TRAILING.sub("", text)
        text = self._BLANKS.sub("\n\n", text)
        return text.strip()

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        if self.normalize(content) != content:
            self.event("whitespace.normalized", user_id=user_id)
