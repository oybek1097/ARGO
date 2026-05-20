"""Language Detector — bundled ARGO plugin.

Heuristically detects whether a response is in Cyrillic or Latin script and emits a detection event.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class LanguageDetectorPlugin(ArgoPlugin):
    """Detects Cyrillic vs Latin script in responses."""

    name = "language-detector"
    version = "1.0.0"
    description = "Detects the script of agent responses."

    @staticmethod
    def detect_script(text: str) -> str:
        """Return 'cyrillic', 'latin', or 'unknown' for the dominant script."""
        cyr = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
        lat = sum(1 for c in text if c.isascii() and c.isalpha())
        if cyr == 0 and lat == 0:
            return "unknown"
        return "cyrillic" if cyr > lat else "latin"

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        self.event("language.detected", user_id=user_id,
                   script=self.detect_script(content))
