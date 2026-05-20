"""Language enforcer plugin — spec section 4.6 (general plugin).

Observes agent responses via the `on_response` hook and checks whether
they appear to be written in a configured target language. Detection is
deliberately lightweight (script/character heuristics only) so the
plugin stays stdlib-only and easily testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from argo_brain.plugin.api import ArgoPlugin

# Unicode code-point ranges used for crude script detection. A response
# is considered to match a language if its dominant script matches.
_SCRIPT_RANGES: dict[str, tuple[tuple[int, int], ...]] = {
    "latin": ((0x41, 0x5A), (0x61, 0x7A)),
    "cyrillic": ((0x0400, 0x04FF),),
    "arabic": ((0x0600, 0x06FF),),
    "han": ((0x4E00, 0x9FFF),),
}

# Maps a target language name to the script expected for it.
_LANGUAGE_SCRIPT: dict[str, str] = {
    "english": "latin",
    "spanish": "latin",
    "french": "latin",
    "german": "latin",
    "russian": "cyrillic",
    "ukrainian": "cyrillic",
    "arabic": "arabic",
    "chinese": "han",
}


@dataclass
class ResponseRecord:
    """A single recorded response and whether it matched the target."""

    user_id: str
    content: str
    detected_script: str
    matched: bool


class LanguageEnforcerPlugin(ArgoPlugin):
    """Records responses and checks them against a target language."""

    name = "language-enforcer"
    version = "1.0.0"
    description = "Checks agent responses against a target language."

    def __init__(self, target_language: str = "english") -> None:
        """Create the plugin.

        Args:
            target_language: Name of the language responses should use
                (e.g. "english", "russian"). Case-insensitive.
        """
        self.target_language = target_language.lower()
        self._records: list[ResponseRecord] = []

    @staticmethod
    def detect_script(text: str) -> str:
        """Return the dominant script name of `text`, or "unknown"."""
        counts: dict[str, int] = {script: 0 for script in _SCRIPT_RANGES}
        for char in text:
            point = ord(char)
            for script, ranges in _SCRIPT_RANGES.items():
                if any(low <= point <= high for low, high in ranges):
                    counts[script] += 1
                    break
        best = max(counts, key=lambda script: counts[script])
        return best if counts[best] > 0 else "unknown"

    def expected_script(self) -> str:
        """Return the script expected for the configured target language."""
        return _LANGUAGE_SCRIPT.get(self.target_language, "latin")

    async def on_response(
        self, user_id: str, content: str, model: str
    ) -> None:
        """Record the response and whether its script matches the target."""
        detected = self.detect_script(content)
        matched = detected == self.expected_script()
        self._records.append(
            ResponseRecord(
                user_id=user_id,
                content=content,
                detected_script=detected,
                matched=matched,
            )
        )

    @property
    def records(self) -> list[ResponseRecord]:
        """Return every recorded response (in observation order)."""
        return list(self._records)

    def mismatches(self) -> list[ResponseRecord]:
        """Return the recorded responses that did not match the target."""
        return [record for record in self._records if not record.matched]

    def clear(self) -> None:
        """Drop every recorded response."""
        self._records.clear()
