"""LLM provider layer — spec section 4.8.

Skeleton stage:
  * `LLMProvider` — the abstract interface
  * `MockProvider` — a deterministic provider that works without an API key
    (for demos and tests; it heuristically simulates tool calls)

`AnthropicProvider` and 30+ native adapters will be added under
`transports/` in Sprint 2. The `get_provider()` signature stays the same.
"""

from __future__ import annotations

import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from argo_brain.tools.base import ToolCall

_MATH_RE = re.compile(r"[-+]?\d[\d\s.]*(?:[-+*/%]\s*[-+]?\d[\d\s.]*)+")
_TIME_WORDS = ("vaqt", "soat", "sana", "time", "date", "время", "уакыт")
_CALC_WORDS = ("hisobla", "calculate", "compute", "посчитай", "qancha")


@dataclass
class LLMResponse:
    """Provider response — text and/or tool calls."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = "unknown"

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class LLMProvider(ABC):
    """Interface for all LLM providers."""

    model: str = "unknown"

    @abstractmethod
    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        """Conversation messages + tool schemas -> response."""
        raise NotImplementedError


class MockProvider(LLMProvider):
    """A deterministic provider that works without an API key.

    Logic:
      * If the last message has the `tool` role -> turn the tool result
        into the final answer (ends the loop).
      * If the user asks for the time -> a `current_time` tool call.
      * If the user writes an arithmetic expression -> a `calculate` tool
        call.
      * Otherwise -> a plain text response (echo).
    """

    model = "mock"

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        if not messages:
            return LLMResponse(content="(empty request)", model=self.model)

        last = messages[-1]
        tool_names = {
            t.get("function", {}).get("name") for t in (tools or [])
        }

        # 1) The last message is a tool result -> final answer
        if last.get("role") == "tool":
            return LLMResponse(
                content=f"Result: {last.get('content', '')}",
                model=self.model,
            )

        user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_text = str(m.get("content", ""))
                break
        low = user_text.lower()

        # 2) Arithmetic expression -> calculate
        math_match = _MATH_RE.search(user_text)
        if math_match and "calculate" in tool_names and (
            any(w in low for w in _CALC_WORDS) or math_match.group(0).strip() == user_text.strip()
        ):
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name="calculate",
                        arguments={"expression": math_match.group(0).strip()},
                    )
                ],
                model=self.model,
            )

        # 3) Time request -> current_time
        if any(w in low for w in _TIME_WORDS) and "current_time" in tool_names:
            return LLMResponse(
                tool_calls=[
                    ToolCall(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name="current_time",
                        arguments={},
                    )
                ],
                model=self.model,
            )

        # 4) Plain text response
        return LLMResponse(
            content=f"[mock] Received: {user_text}",
            model=self.model,
        )


def get_provider(model: str = "mock") -> LLMProvider:
    """Returns a provider based on the model name.

    * `mock` (or no API key) -> `MockProvider`, which needs no credentials.
    * Any other model with `ANTHROPIC_API_KEY` set -> `AnthropicProvider`.

    More native adapters (OpenAI, Gemini, Yandex GPT, ...) will register here
    in later sprints; the signature stays stable.
    """
    if model and model != "mock" and os.environ.get("ANTHROPIC_API_KEY"):
        # Imported lazily so the mock path never requires the network stack.
        from argo_brain.providers.anthropic import AnthropicProvider

        return AnthropicProvider(model=model)
    return MockProvider()
