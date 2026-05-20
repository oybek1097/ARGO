"""Response Translator — bundled ARGO plugin.

Hooks the response stage to flag responses that should be translated to a user's preferred language.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin


class ResponseTranslatorPlugin(ArgoPlugin):
    """Records the target language each user wants responses in."""

    name = "response-translator"
    version = "1.0.0"
    description = "Flags responses for translation to a user's preferred language."

    def __init__(self) -> None:
        self._lang: dict[str, str] = {}

    async def handle_command(self, command: str, user_id: str, args: str) -> str | None:
        if command != "lang":
            return None
        code = args.strip().lower()
        if not code:
            return f"Current language: {self._lang.get(user_id, 'en')}"
        self._lang[user_id] = code
        return f"Responses will be flagged for translation to '{code}'."

    async def on_response(self, user_id: str, content: str, model: str) -> None:
        target = self._lang.get(user_id)
        if target and target != "en":
            self.event("translate.requested", user_id=user_id, target=target)
