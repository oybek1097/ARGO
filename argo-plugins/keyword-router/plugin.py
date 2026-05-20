"""Keyword Router — bundled ARGO plugin.

Watches responses for keywords and emits routing events so downstream systems can escalate or notify on matches.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class KeywordRouterPlugin(ArgoPlugin):
    """Fires a routing event when a watched keyword appears."""

    name = "keyword-router"
    version = "1.0.0"
    description = "Emits routing events when keywords appear in responses."

    DEFAULT_KEYWORDS = ("urgent", "incident", "outage", "escalate")

    def __init__(self, keywords: tuple[str, ...] = DEFAULT_KEYWORDS) -> None:
        self._keywords = tuple(k.lower() for k in keywords)

    def match(self, text: str) -> list[str]:
        """Return the watched keywords found in the text."""
        low = text.lower()
        return [k for k in self._keywords if k in low]

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        for hit in self.match(content):
            self.event("route.keyword", user_id=user_id, keyword=hit)
