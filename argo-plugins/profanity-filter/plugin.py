"""Profanity Filter — bundled ARGO plugin.

Redacts a configurable set of offensive words from agent responses.
"""

from __future__ import annotations

import re

from argo_brain.plugin.api import ArgoPlugin


class ProfanityFilterPlugin(ArgoPlugin):
    """Masks blacklisted words in the final response."""

    name = "profanity-filter"
    version = "1.0.0"
    description = "Redacts offensive language from agent responses."

    BLACKLIST = ("damn", "crap", "hell")

    def __init__(self) -> None:
        self._pattern = re.compile(
            r"\b(" + "|".join(self.BLACKLIST) + r")\b", re.IGNORECASE
        )

    def clean(self, text: str) -> str:
        """Return text with blacklisted words replaced by asterisks."""
        return self._pattern.sub(lambda m: "*" * len(m.group(0)), text)

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        if self._pattern.search(content):
            self.event("profanity.redacted", user_id=user_id)
