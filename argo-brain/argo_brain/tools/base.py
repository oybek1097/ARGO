"""Tool abstraction — spec section 4.4.

The `Tool` ABC, `ToolResult` and `ToolCall`. At the skeleton stage fields
such as `cost_estimate` and `cacheable` are simplified; the full taxonomy
arrives in Sprint 4.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """The result of a tool execution."""

    content: str
    success: bool = True
    duration_ms: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class ToolCall:
    """A single tool call requested by the model."""

    id: str
    name: str
    arguments: dict = field(default_factory=dict)


class Tool(ABC):
    """Base class for all tools.

    Subclasses define `name`, `description` and `parameters` (a JSON schema)
    and implement `run()`.
    """

    name: str = ""
    description: str = ""
    parameters: dict = {"type": "object", "properties": {}}
    dangerous: bool = False  # if True, confirmation is requested for mutations

    @abstractmethod
    async def run(self, user_id: str, **kwargs) -> ToolResult:
        """Executes the tool and returns a `ToolResult`."""
        raise NotImplementedError

    async def __call__(self, user_id: str, **kwargs) -> ToolResult:
        """Wraps `run()` while measuring the execution time."""
        started = time.perf_counter()
        try:
            result = await self.run(user_id, **kwargs)
        except Exception as exc:  # noqa: BLE001 — a tool error must not break the loop
            result = ToolResult(content=f"Xato: {exc}", success=False)
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        return result

    def schema(self) -> dict:
        """OpenAI-style function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
