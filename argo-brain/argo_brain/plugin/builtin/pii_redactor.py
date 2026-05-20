"""PII redactor plugin — spec section 4.6 (general plugin).

Wraps the `PIIRedactor` from `argo_brain.security.redaction` so that PII
appearing in tool results is scrubbed before it reaches the model or the
conversation log.
"""

from __future__ import annotations

import dataclasses

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.security.redaction import PIIRedactor
from argo_brain.tools.base import ToolCall, ToolResult


class PIIRedactorPlugin(ArgoPlugin):
    """Redacts PII from tool results via `transform_tool_result`."""

    name = "pii-redactor"
    version = "1.0.0"
    description = "Redacts PII from tool results before they are used."

    def __init__(self, redactor: PIIRedactor | None = None) -> None:
        """Create the plugin.

        Args:
            redactor: Optional pre-built `PIIRedactor`; a default one is
                created when omitted.
        """
        self.redactor = redactor or PIIRedactor()
        # Running total of PII matches scrubbed, keyed by PII type.
        self.redaction_counts: dict[str, int] = {}

    async def transform_tool_result(
        self, call: ToolCall, result: ToolResult, user_id: str
    ) -> ToolResult:
        """Return a new `ToolResult` with PII redacted from its content."""
        original = result.content or ""
        for pii_type, count in self.redactor.count_pii(original).items():
            if count:
                self.redaction_counts[pii_type] = (
                    self.redaction_counts.get(pii_type, 0) + count
                )
        redacted = self.redactor.redact(original)
        # Build a fresh ToolResult so the original object is left intact.
        return dataclasses.replace(result, content=redacted)
