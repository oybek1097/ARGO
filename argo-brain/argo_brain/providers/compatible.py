"""OpenAI-compatible provider — spec section 4.8.

Many hosted LLM APIs (DeepSeek, Groq, Mistral, OpenRouter, Together, ...)
speak the exact same Chat Completions wire format as OpenAI. Rather than
ship a near-identical adapter per vendor, `OpenAICompatibleProvider` is a
single generic provider parameterised by `base_url`, `api_key` and `model`.

It reuses the OpenAI message-conversion and response-parsing helpers (see
`argo_brain.providers.openai`, imported read-only) and, like the other
skeleton providers, uses the stdlib `urllib` instead of any vendor SDK.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from argo_brain.providers.base import LLMProvider, LLMResponse

# Reuse the OpenAI-style conversion helpers (read-only import).
from argo_brain.providers.openai import convert_messages, parse_response

_DEFAULT_MAX_TOKENS = 2048

# Known OpenAI-compatible endpoints. Each value is the full chat-completions
# URL the corresponding factory below pre-configures.
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
MISTRAL_BASE_URL = "https://api.mistral.ai/v1/chat/completions"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
TOGETHER_BASE_URL = "https://api.together.xyz/v1/chat/completions"


class OpenAICompatibleProvider(LLMProvider):
    """Generic provider for any OpenAI Chat Completions-compatible API.

    The constructor takes the vendor's chat-completions `base_url`, an
    `api_key` (sent as a Bearer token) and the `model` id. Message conversion
    and response parsing are delegated to the OpenAI helpers, since the wire
    format is identical.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self._api_key = api_key or ""
        self._max_tokens = max_tokens

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            self.base_url,
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
            # Identical Chat Completions format — reuse OpenAI's converter.
            "messages": convert_messages(messages),
        }
        if tools:
            payload["tools"] = tools

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return parse_response(raw, self.model)


# --- Vendor factory functions -------------------------------------------
# Each returns an `OpenAICompatibleProvider` pre-wired with the right
# `base_url`, so callers only supply `model` and `api_key`.


def deepseek(model: str, api_key: str) -> OpenAICompatibleProvider:
    """DeepSeek (https://api.deepseek.com) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=DEEPSEEK_BASE_URL, api_key=api_key, model=model
    )


def groq(model: str, api_key: str) -> OpenAICompatibleProvider:
    """Groq (https://api.groq.com) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=GROQ_BASE_URL, api_key=api_key, model=model
    )


def mistral(model: str, api_key: str) -> OpenAICompatibleProvider:
    """Mistral (https://api.mistral.ai) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=MISTRAL_BASE_URL, api_key=api_key, model=model
    )


def openrouter(model: str, api_key: str) -> OpenAICompatibleProvider:
    """OpenRouter (https://openrouter.ai) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=OPENROUTER_BASE_URL, api_key=api_key, model=model
    )


def together(model: str, api_key: str) -> OpenAICompatibleProvider:
    """Together AI (https://api.together.xyz) — OpenAI-compatible."""
    return OpenAICompatibleProvider(
        base_url=TOGETHER_BASE_URL, api_key=api_key, model=model
    )
