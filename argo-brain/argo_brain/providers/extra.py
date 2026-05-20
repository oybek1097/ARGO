"""Extra LLM providers — spec section 4.8.

This module adds two more native providers plus a set of OpenAI-compatible
vendor factories, keeping the same dependency-free style as the rest of the
provider layer (stdlib `urllib`, no vendor SDKs):

  * `CohereProvider` — talks to the Cohere v2 chat API, which uses its own
    JSON shape, so dedicated message-conversion / response-parsing helpers
    are provided (and exported for testing).
  * `AzureOpenAIProvider` — Azure OpenAI is wire-compatible with the OpenAI
    Chat Completions API but uses a different URL layout and an `api-key`
    header; it therefore reuses the OpenAI message conversion verbatim.
  * `nvidia_nim` / `fireworks` / `perplexity` — factory functions returning
    a pre-configured `OpenAICompatibleProvider` for vendors that already
    speak the OpenAI wire format.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

from argo_brain.providers.base import LLMProvider, LLMResponse
from argo_brain.providers.compatible import OpenAICompatibleProvider

# Reuse the OpenAI message converter for Azure (read-only import).
from argo_brain.providers.openai import convert_messages as _openai_convert_messages
from argo_brain.tools.base import ToolCall

_DEFAULT_MAX_TOKENS = 2048

# --- Endpoints -----------------------------------------------------------

COHERE_API_URL = "https://api.cohere.com/v2/chat"
AZURE_DEFAULT_API_VERSION = "2024-06-01"

# OpenAI-compatible vendor base URLs (full chat-completions endpoints).
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
FIREWORKS_BASE_URL = (
    "https://api.fireworks.ai/inference/v1/chat/completions"
)
PERPLEXITY_BASE_URL = "https://api.perplexity.ai/chat/completions"


# --- Cohere message-conversion / response helpers ------------------------
# Exported at module level so they can be imported and unit-tested offline.


def cohere_convert_messages(messages: list[dict]) -> list[dict]:
    """Converts the internal message list into Cohere v2 chat format.

    Internal roles: system / user / assistant / tool. Cohere v2 accepts the
    same four role names, but two shapes differ from the internal one:

      * An assistant message that requested tools carries `tool_calls`; each
        internal call (`id` / `name` / `arguments` dict) becomes a Cohere
        `tool_calls` entry whose `function.arguments` is a JSON *string*.
      * An internal `tool` message uses `tool_call_id`; Cohere expects the
        same key plus the result wrapped in a `content` list of `text`
        blocks, so the string content is wrapped accordingly.
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
            content = msg.get("content")
            out["content"] = str(content) if content else ""
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
            # Cohere v2 expects tool results as a list of content blocks.
            converted.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.get("tool_call_id", ""),
                    "content": [
                        {
                            "type": "document",
                            "document": {
                                "data": str(msg.get("content", "")),
                            },
                        }
                    ],
                }
            )

    return converted


def cohere_parse_response(raw: dict, fallback_model: str) -> LLMResponse:
    """Parses a raw Cohere v2 chat response into an `LLMResponse`.

    Cohere returns a top-level `message` object whose `content` is a list of
    typed blocks (`text` blocks carry the answer) and whose optional
    `tool_calls` mirror the OpenAI shape (JSON-string arguments -> dict).
    """
    message = raw.get("message", {}) or {}

    # Concatenate every `text` block into the final answer string.
    text_parts: list[str] = []
    content = message.get("content", [])
    if isinstance(content, str):
        text_parts.append(content)
    else:
        for block in content or []:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                text_parts.append(block)

    tool_calls: list[ToolCall] = []
    for call in message.get("tool_calls", []) or []:
        fn = call.get("function", {})
        raw_args = fn.get("arguments", "") or "{}"
        try:
            arguments = (
                json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            )
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
        content="".join(text_parts),
        tool_calls=tool_calls,
        model=raw.get("model", fallback_model),
    )


# --- Cohere provider -----------------------------------------------------


class CohereProvider(LLMProvider):
    """Calls the Cohere v2 chat API (tool calling supported).

    The API key is read from the `api_key` constructor argument or, if not
    given, from the `COHERE_API_KEY` environment variable. Like the other
    skeleton providers it uses stdlib `urllib` and offloads the blocking
    HTTP call to a worker thread to keep the async interface.
    """

    def __init__(
        self,
        model: str = "command-r-plus",
        api_key: str | None = None,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = model
        self._api_key = api_key or os.environ.get("COHERE_API_KEY", "")
        self._max_tokens = max_tokens

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            COHERE_API_URL,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "accept": "application/json",
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
            "messages": cohere_convert_messages(messages),
        }
        if tools:
            # The internal tool schema already matches Cohere's `tools` shape.
            payload["tools"] = tools

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return cohere_parse_response(raw, self.model)


# --- Azure OpenAI provider ----------------------------------------------


def azure_chat_url(
    endpoint: str, deployment: str, api_version: str
) -> str:
    """Builds the Azure OpenAI chat-completions URL.

    Azure uses a per-deployment URL of the form
    `{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=...`.
    A trailing slash on `endpoint` is tolerated.
    """
    base = endpoint.rstrip("/")
    return (
        f"{base}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={api_version}"
    )


class AzureOpenAIProvider(LLMProvider):
    """Calls an Azure OpenAI deployment (OpenAI Chat Completions compatible).

    Azure speaks the exact OpenAI wire format, so message conversion is
    reused verbatim from `argo_brain.providers.openai`. Only two things
    differ from vanilla OpenAI:

      * the URL is per-deployment (see `azure_chat_url`), and
      * authentication uses an `api-key` header instead of a Bearer token.

    The key is read from the `api_key` argument or the `AZURE_OPENAI_KEY`
    environment variable.
    """

    def __init__(
        self,
        endpoint: str,
        deployment: str,
        api_key: str | None = None,
        api_version: str = AZURE_DEFAULT_API_VERSION,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.endpoint = endpoint
        self.deployment = deployment
        self.api_version = api_version
        # On Azure the model id is the deployment name.
        self.model = deployment
        self._api_key = api_key or os.environ.get("AZURE_OPENAI_KEY", "")
        self._max_tokens = max_tokens
        self.base_url = azure_chat_url(endpoint, deployment, api_version)

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "api-key": self._api_key,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        payload: dict = {
            "max_tokens": self._max_tokens,
            # Identical Chat Completions format — reuse OpenAI's converter.
            "messages": _openai_convert_messages(messages),
        }
        if tools:
            payload["tools"] = tools

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        # Azure responses are OpenAI-shaped — reuse the OpenAI parser.
        from argo_brain.providers.openai import parse_response

        return parse_response(raw, self.model)


# --- OpenAI-compatible vendor factories ---------------------------------
# Each returns an `OpenAICompatibleProvider` pre-wired with the right
# `base_url`, so callers only supply `model` and `api_key`.


def nvidia_nim(
    model: str, api_key: str, base_url: str = NVIDIA_NIM_BASE_URL
) -> OpenAICompatibleProvider:
    """NVIDIA NIM (https://integrate.api.nvidia.com) — OpenAI-compatible.

    `base_url` is overridable so self-hosted NIM microservices can be used.
    """
    return OpenAICompatibleProvider(
        base_url=base_url, api_key=api_key, model=model
    )


def fireworks(model: str, api_key: str) -> OpenAICompatibleProvider:
    """Fireworks AI (https://api.fireworks.ai) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=FIREWORKS_BASE_URL, api_key=api_key, model=model
    )


def perplexity(model: str, api_key: str) -> OpenAICompatibleProvider:
    """Perplexity (https://api.perplexity.ai) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=PERPLEXITY_BASE_URL, api_key=api_key, model=model
    )
