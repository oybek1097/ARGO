"""Ollama provider — spec section 4.8.

Talks to a locally running Ollama server (https://ollama.com) using the
stdlib `urllib` only, so the skeleton stays dependency-free. Ollama needs no
API key — it is meant for self-hosted models running on `localhost`.

The blocking HTTP call is moved to a worker thread so the async `complete()`
interface defined by `LLMProvider` is preserved.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from argo_brain.providers.base import LLMProvider, LLMResponse
from argo_brain.tools.base import ToolCall

_DEFAULT_URL = "http://localhost:11434/api/chat"
_DEFAULT_MODEL = "llama3"


def convert_messages(messages: list[dict]) -> list[dict]:
    """Converts the internal message list into Ollama's chat format.

    Internal roles: system / user / assistant / tool. Ollama's `/api/chat`
    endpoint accepts the same four roles, but a few shapes need translation:

      * An assistant message that requested tools carries `tool_calls`; each
        internal call (`id` / `name` / `arguments` dict) becomes an Ollama
        `tool_calls` entry whose `function.arguments` is a JSON *object*
        (Ollama keeps arguments as a dict, unlike OpenAI's JSON string).
      * An internal `tool` message uses `tool_call_id`. Ollama does not use
        that key, so only `role` and `content` are carried over.
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
            out: dict = {
                "role": "assistant",
                # Ollama expects a string; use "" when there is no text.
                "content": str(msg["content"]) if msg.get("content") else "",
            }
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                out["tool_calls"] = [
                    {
                        "function": {
                            "name": call["name"],
                            # Ollama keeps arguments as a JSON object.
                            "arguments": call.get("arguments", {}),
                        }
                    }
                    for call in tool_calls
                ]
            converted.append(out)
        elif role == "tool":
            converted.append(
                {
                    "role": "tool",
                    "content": str(msg.get("content", "")),
                }
            )

    return converted


def parse_response(raw: dict, fallback_model: str) -> LLMResponse:
    """Parses a raw Ollama `/api/chat` response into an `LLMResponse`.

    The top-level `message` object is read: plain `content` becomes text, and
    any `tool_calls` entries are decoded back into internal `ToolCall`
    objects. Ollama omits a stable call id, so a synthetic one is generated.
    """
    message = raw.get("message", {}) or {}

    tool_calls: list[ToolCall] = []
    for idx, call in enumerate(message.get("tool_calls", []) or []):
        fn = call.get("function", {})
        raw_args = fn.get("arguments", {})
        if isinstance(raw_args, str):
            try:
                arguments = json.loads(raw_args or "{}")
            except (json.JSONDecodeError, TypeError):
                arguments = {}
        else:
            arguments = raw_args or {}
        tool_calls.append(
            ToolCall(
                # Ollama has no call id of its own; synthesise a stable one.
                id=call.get("id") or f"call_{idx}",
                name=fn.get("name", ""),
                arguments=arguments or {},
            )
        )

    return LLMResponse(
        content=message.get("content") or "",
        tool_calls=tool_calls,
        model=raw.get("model", fallback_model),
    )


class OllamaProvider(LLMProvider):
    """Calls a local Ollama server (tool calling supported on capable models).

    No API key is required; the server is expected to be reachable at
    `base_url` (default `http://localhost:11434/api/chat`).
    """

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEFAULT_URL,
    ) -> None:
        self.model = model
        self.base_url = base_url

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={"content-type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        payload: dict = {
            "model": self.model,
            "messages": convert_messages(messages),
            # Ollama streams by default; ask for a single complete response.
            "stream": False,
        }
        if tools:
            # The internal tool schema already matches Ollama's `tools` shape.
            payload["tools"] = tools

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return parse_response(raw, self.model)
