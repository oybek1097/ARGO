"""PII redaction pipeline (spec sections 4.1 / 4.14).

Detects common personally identifiable information in free text using
regular expressions and replaces every match with a placeholder token.
"""

from __future__ import annotations

import re

# Default placeholder tokens, keyed by PII type. The constructor accepts
# an override mapping so callers can customise the redaction output.
DEFAULT_PLACEHOLDERS: dict[str, str] = {
    "email": "[EMAIL]",
    "phone": "[PHONE]",
    "card": "[CARD]",
    "ip": "[IP]",
    "iban": "[IBAN]",
}

# Regex patterns for each PII type. Order matters in `redact`: patterns
# that could otherwise be partially consumed (e.g. cards before phones)
# are applied first.
_PATTERNS: dict[str, re.Pattern[str]] = {
    # Email addresses, e.g. user.name+tag@example.co.uk
    "email": re.compile(
        r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"
    ),
    # IBAN-like codes: 2 letters, 2 digits, then 11-30 alphanumerics.
    "iban": re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
    # Credit-card-like 16-digit numbers, optionally grouped by spaces
    # or hyphens (e.g. 4111 1111 1111 1111).
    "card": re.compile(r"\b(?:\d[ -]?){15}\d\b"),
    # IPv4 addresses, e.g. 192.168.0.1
    "ip": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
        r"(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
    ),
    # Phone numbers: optional +, then 7-15 digits with common separators.
    "phone": re.compile(
        r"(?<![\w.])\+?\d[\d\s().\-]{6,}\d(?![\w.])"
    ),
}

# Application order: detect specific/structured types before generic
# phone numbers so digits are not stolen by the looser phone pattern.
_ORDER = ["email", "iban", "card", "ip", "phone"]


class PIIRedactor:
    """Redacts PII from text by substituting placeholder tokens."""

    def __init__(self, placeholders: dict[str, str] | None = None) -> None:
        """Create a redactor.

        Args:
            placeholders: Optional mapping of PII type -> placeholder
                token. Any unspecified type falls back to its default.
        """
        merged = dict(DEFAULT_PLACEHOLDERS)
        if placeholders:
            merged.update(placeholders)
        self.placeholders = merged

    def redact(self, text: str) -> str:
        """Return `text` with every detected PII match replaced.

        Args:
            text: Arbitrary input string.

        Returns:
            The text with PII substituted by placeholder tokens.
        """
        if not text:
            return text
        result = text
        for pii_type in _ORDER:
            placeholder = self.placeholders[pii_type]
            result = _PATTERNS[pii_type].sub(placeholder, result)
        return result

    def count_pii(self, text: str) -> dict[str, int]:
        """Count how many PII matches of each type appear in `text`.

        The counting works on the original text type-by-type, so the
        numbers reflect raw detections before any substitution.

        Args:
            text: Arbitrary input string.

        Returns:
            A mapping of PII type -> number of matches found.
        """
        counts: dict[str, int] = {key: 0 for key in _ORDER}
        if not text:
            return counts
        # Walk types in priority order and consume matches from a working
        # copy so generic phone matches do not double-count, e.g., IBANs.
        working = text
        for pii_type in _ORDER:
            matches = _PATTERNS[pii_type].findall(working)
            counts[pii_type] = len(matches)
            working = _PATTERNS[pii_type].sub(" ", working)
        return counts
