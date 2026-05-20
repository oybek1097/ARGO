"""Google Gemini provider — spec section 4.8.

A real provider that calls the Google Gemini (generativelanguage) API. To
keep the skeleton dependency-free it uses the stdlib `urllib` instead of the
`google-generativeai` SDK; the blocking HTTP call is moved to a worker
thread so the async interface is preserved.

Activated by `get_provider()` when `GEMINI_API_KEY` is set (see the one-line
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

_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
_DEFAULT_MAX_TOKENS = 2048

# Friendly aliases -> concrete Gemini model ids.
_MODEL_ALIASES = {
    "gemini": "gemini-1.5-flash",
    "gemini-flash": "gemini-1.5-flash",
    "gemini-pro": "gemini-1.5-pro",
}


def extract_system(messages: list[dict]) -> str:
    """Collects all `system` role messages into a single instruction string.

    Gemini takes the system prompt separately as `systemInstruction`, so the
    system parts are extracted out of the conversation here.
    """
    return "\n\n".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "system"
    )


def convert_messages(messages: list[dict]) -> list[dict]:
    """Converts the internal message list into Gemini's `contents` format.

    Internal roles map to Gemini roles as follows:

      * `system`  -> skipped here (handled by `extract_system`).
      * `user`    -> a `user` content with a `text` part.
      * `assistant` -> a `model` content; plain text becomes a `text` part
        and each internal `tool_calls` entry becomes a `functionCall` part.
      * `tool`    -> a `user` content with a `functionResponse` part keyed by
        the tool name (Gemini matches responses by name, not call id).
    """
    contents: list[dict] = []

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            continue
        if role == "user":
            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": str(msg.get("content", ""))}],
                }
            )
        elif role == "assistant":
            parts: list[dict] = []
            if msg.get("content"):
                parts.append({"text": str(msg["content"])})
            for call in msg.get("tool_calls", []):
                parts.append(
                    {
                        "functionCall": {
                            "name": call["name"],
                            "args": call.get("arguments", {}),
                        }
                    }
                )
            contents.append({"role": "model", "parts": parts})
        elif role == "tool":
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": msg.get("name", ""),
                                "response": {
                                    "result": str(msg.get("content", ""))
                                },
                            }
                        }
                    ],
                }
            )

    return contents


def convert_tools(tools: list[dict]) -> list[dict]:
    """Converts internal (OpenAI-style) tool schemas to Gemini's format.

    Gemini groups all callable functions under a single `functionDeclarations`
    list inside one `tools` entry.
    """
    declarations = [
        {
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "parameters": t["function"].get(
                "parameters", {"type": "object", "properties": {}}
            ),
        }
        for t in tools
    ]
    return [{"functionDeclarations": declarations}]


def parse_response(raw: dict, fallback_model: str) -> LLMResponse:
    """Parses a raw Gemini `generateContent` response into an `LLMResponse`.

    The first candidate's `content.parts` are scanned: `text` parts are
    concatenated and `functionCall` parts are decoded into internal
    `ToolCall` objects. Gemini omits call ids, so a synthetic id is built
    from the function name.
    """
    candidates = raw.get("candidates", [])
    parts = (
        candidates[0].get("content", {}).get("parts", [])
        if candidates
        else []
    )

    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for part in parts:
        if "text" in part:
            text_parts.append(part.get("text", ""))
        elif "functionCall" in part:
            fn = part["functionCall"]
            name = fn.get("name", "")
            tool_calls.append(
                ToolCall(
                    id=f"call_{name}",
                    name=name,
                    arguments=fn.get("args", {}) or {},
                )
            )

    return LLMResponse(
        content="".join(text_parts),
        tool_calls=tool_calls,
        model=raw.get("modelVersion", fallback_model),
    )


class GeminiProvider(LLMProvider):
    """Calls the Google Gemini API (function calling supported)."""

    def __init__(
        self,
        model: str = "gemini-1.5-flash",
        api_key: str | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = _MODEL_ALIASES.get(model, model)
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._max_tokens = max_tokens

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        url = (
            f"{_API_BASE}/{self.model}:generateContent"
            f"?key={self._api_key}"
        )
        req = urllib.request.Request(
            url,
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
            "contents": convert_messages(messages),
            "generationConfig": {"maxOutputTokens": self._max_tokens},
        }
        system = extract_system(messages)
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            payload["tools"] = convert_tools(tools)

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return parse_response(raw, self.model)
