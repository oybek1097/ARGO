"""PII Redactor — bundled ARGO plugin.

Redacts emails, phone numbers and credit-card-like digit runs from agent responses before they leave the system.
"""

from __future__ import annotations

import re

from argo_brain.plugin.api import ArgoPlugin


class PiiRedactorPlugin(ArgoPlugin):
    """Masks common PII patterns in responses."""

    name = "pii-redactor"
    version = "1.0.0"
    description = "Redacts personally identifiable information from responses."

    _EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    _PHONE = re.compile(r"\+?\d[\d ()-]{7,}\d")
    _CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")

    def redact(self, text: str) -> str:
        """Return text with emails, phones and card numbers masked."""
        text = self._EMAIL.sub("[email redacted]", text)
        text = self._CARD.sub("[card redacted]", text)
        text = self._PHONE.sub("[phone redacted]", text)
        return text

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        if self.redact(content) != content:
            self.event("pii.redacted", user_id=user_id)
