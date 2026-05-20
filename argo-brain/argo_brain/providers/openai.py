"""OpenAI provider — spec section 4.8.

A real provider that calls the OpenAI Chat Completions API. To keep the
skeleton dependency-free it uses the stdlib `urllib` instead of the `openai`
SDK; the blocking HTTP call is moved to a worker thread so the async
interface is preserved.

Activated by `get_provider()` when `OPENAI_API_KEY` is set (see the one-line
registration note in `base.py`).
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

from argo_brain.providers.base import LLMProvider, LLMResponse
from argo_brain.tools.base import ToolCall

_API_URL = "https://api.openai.com/v1/chat/completions"
_DEFAULT_MAX_TOKENS = 2048

# Friendly aliases -> concrete OpenAI model ids.
_MODEL_ALIASES = {
    "openai": "gpt-4o",
    "gpt": "gpt-4o",
    "gpt4": "gpt-4o",
    "gpt-4": "gpt-4o",
    "gpt4o": "gpt-4o",
    "gpt-mini": "gpt-4o-mini",
}


def convert_messages(messages: list[dict]) -> list[dict]:
    """Converts the internal message list into OpenAI Chat Completions format.

    Internal roles: system / user / assistant / tool. OpenAI accepts all four
    roles directly, but two shapes need translation:

      * An assistant message that requested tools carries `tool_calls`; each
        internal call (`id` / `name` / `arguments` dict) becomes an OpenAI
        `tool_calls` entry whose `function.arguments` is a JSON *string*.
      * An internal `tool` message uses `tool_call_id`; OpenAI expects the
        same key, so it is passed through with the result content.
    """
    converted: list[dict] = []

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            converted.append(
                {"role": "system", "content": str(msg.get("content", ""))}
            )
        elif role == "user":
            converted.append(
                {"role": "user", "content": str(msg.get("content", ""))}
            )
        elif role == "assistant":
            out: dict = {"role": "assistant"}
            # OpenAI requires `content` to be present even when null.
            out["content"] = str(msg["content"]) if msg.get("content") else None
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                out["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call.get("arguments", {})),
                        },
                    }
                    for call in tool_calls
                ]
            converted.append(out)
        elif role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": str(msg.get("content", "")),
                }
            )

    return converted


def parse_response(raw: dict, fallback_model: str) -> LLMResponse:
    """Parses a raw OpenAI Chat Completions response into an `LLMResponse`.

    The first choice's `message` is read: plain `content` becomes text, and
    any `tool_calls` entries are decoded back into internal `ToolCall`
    objects (JSON-string arguments -> dict).
    """
    choices = raw.get("choices", [])
    message = choices[0].get("message", {}) if choices else {}

    tool_calls: list[ToolCall] = []
    for call in message.get("tool_calls", []) or []:
        fn = call.get("function", {})
        raw_args = fn.get("arguments", "") or "{}"
        try:
            arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except (json.JSONDecodeError, TypeError):
            arguments = {}
        tool_calls.append(
            ToolCall(
                id=call.get("id", ""),
                name=fn.get("name", ""),
                arguments=arguments or {},
            )
        )

    return LLMResponse(
        content=message.get("content") or "",
        tool_calls=tool_calls,
        model=raw.get("model", fallback_model),
    )


class OpenAIProvider(LLMProvider):
    """Calls the OpenAI Chat Completions API (tool calling supported)."""

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = _MODEL_ALIASES.get(model, model)
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._max_tokens = max_tokens

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            _API_URL,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self._api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": convert_messages(messages),
        }
        if tools:
            # The internal tool schema already matches OpenAI's `tools` shape.
            payload["tools"] = tools

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return parse_response(raw, self.model)
