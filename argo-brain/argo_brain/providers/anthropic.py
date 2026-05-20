"""Anthropic provider — spec section 4.8.

A real provider that calls the Anthropic Messages API. To keep the skeleton
dependency-free it uses the stdlib `urllib` instead of the `anthropic` SDK;
the blocking HTTP call is moved to a worker thread so the async interface is
preserved.

Activated automatically by `get_provider()` when `ANTHROPIC_API_KEY` is set.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

from argo_brain.providers.base import LLMProvider, LLMResponse
from argo_brain.tools.base import ToolCall

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"
_DEFAULT_MAX_TOKENS = 2048

# Friendly aliases -> concrete Anthropic model ids.
_MODEL_ALIASES = {
    "claude": "claude-sonnet-4-6",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
    "haiku": "claude-haiku-4-5-20251001",
}


def _split_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Splits the internal message list into (system_prompt, anthropic_messages).

    Internal roles: system / user / assistant / tool. The Anthropic API takes
    `system` separately and expects tool results inside a `user` message as
    `tool_result` content blocks.
    """
    system_parts: list[str] = []
    converted: list[dict] = []

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            system_parts.append(str(msg.get("content", "")))
        elif role == "user":
            converted.append({"role": "user", "content": str(msg.get("content", ""))})
        elif role == "assistant":
            blocks: list[dict] = []
            if msg.get("content"):
                blocks.append({"type": "text", "text": str(msg["content"])})
            for call in msg.get("tool_calls", []):
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": call["id"],
                        "name": call["name"],
                        "input": call.get("arguments", {}),
                    }
                )
            converted.append({"role": "assistant", "content": blocks or ""})
        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": msg.get("tool_call_id", ""),
                "content": str(msg.get("content", "")),
            }
            # Merge consecutive tool results into one user message.
            if converted and converted[-1]["role"] == "user" and isinstance(
                converted[-1]["content"], list
            ):
                converted[-1]["content"].append(block)
            else:
                converted.append({"role": "user", "content": [block]})

    return "\n\n".join(system_parts), converted


class AnthropicProvider(LLMProvider):
    """Calls the Anthropic Messages API (tool use supported)."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = _MODEL_ALIASES.get(model, model)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._max_tokens = max_tokens

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            _API_URL,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": _API_VERSION,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        system, conv = _split_messages(messages)
        payload: dict = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": conv,
        }
        if system:
            payload["system"] = system
        if tools:
            # OpenAI-style schema -> Anthropic tool schema.
            payload["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                }
                for t in tools
            ]

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in raw.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=block.get("input", {}) or {},
                    )
                )
        return LLMResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            model=raw.get("model", self.model),
        )
