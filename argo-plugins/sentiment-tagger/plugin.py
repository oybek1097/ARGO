"""Sentiment Tagger — bundled ARGO plugin.

Applies a lightweight lexicon-based sentiment score to responses and emits a tag event.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class SentimentTaggerPlugin(ArgoPlugin):
    """Lexicon-based coarse sentiment tagging."""

    name = "sentiment-tagger"
    version = "1.0.0"
    description = "Tags responses with a coarse sentiment score."

    POSITIVE = ("success", "done", "great", "fixed", "resolved", "ready")
    NEGATIVE = ("error", "failed", "unable", "problem", "broken", "denied")

    def score(self, text: str) -> str:
        """Return 'positive', 'negative', or 'neutral' for the text."""
        low = text.lower()
        pos = sum(low.count(w) for w in self.POSITIVE)
        neg = sum(low.count(w) for w in self.NEGATIVE)
        if pos > neg:
            return "positive"
        if neg > pos:
            return "negative"
        return "neutral"

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        self.event("sentiment.tagged", user_id=user_id, label=self.score(content))
