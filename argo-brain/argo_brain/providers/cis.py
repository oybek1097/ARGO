"""CIS-region LLM providers — spec section 4.8.

ARGO's exclusive feature (spec section 0): native adapters for LLM providers
hosted inside the CIS region, so that conversations stay under **Russia data
residency** rules (152-FZ).  No data leaves the regional cloud boundary.

Two providers live here, both dependency-free (stdlib `urllib` instead of a
vendor SDK; the blocking HTTP call is moved onto a worker thread so the async
interface is preserved):

  * `YandexGPTProvider` — Yandex Foundation Models / YandexGPT completion API.
  * `GigaChatProvider`  — SberCloud GigaChat chat-completions API (OpenAI-like).

The message-conversion helpers are module-level functions so they can be
imported and unit-tested without the network.
"""

from __future__ import annotations

import asyncio
import json
import os
import urllib.error
import urllib.request

from argo_brain.providers.base import LLMProvider, LLMResponse
from argo_brain.tools.base import ToolCall

# --- Yandex Foundation Models ------------------------------------------------

_YANDEX_API_URL = (
    "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
)
_YANDEX_DEFAULT_MAX_TOKENS = 2048

# Friendly aliases -> concrete YandexGPT model slugs (the `modelUri` is built
# from `gpt://<folder_id>/<slug>` at request time).
_YANDEX_MODEL_ALIASES = {
    "yandex": "yandexgpt",
    "yandexgpt": "yandexgpt",
    "yandexgpt-lite": "yandexgpt-lite",
    "yagpt": "yandexgpt",
}

# --- SberCloud GigaChat ------------------------------------------------------

_GIGACHAT_API_URL = (
    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
)
_GIGACHAT_DEFAULT_MAX_TOKENS = 2048

# Friendly aliases -> concrete GigaChat model ids.
_GIGACHAT_MODEL_ALIASES = {
    "gigachat": "GigaChat",
    "giga": "GigaChat",
    "gigachat-pro": "GigaChat-Pro",
    "gigachat-max": "GigaChat-Max",
}


# --- YandexGPT message conversion -------------------------------------------


def convert_messages_yandex(messages: list[dict]) -> list[dict]:
    """Converts the internal message list into YandexGPT's format.

    Internal roles: system / user / assistant / tool.  The YandexGPT
    completion API expects a flat list of `{"role": ..., "text": ...}` objects.
    Role mapping:

      * `system`    -> `system`
      * `user`      -> `user`
      * `assistant` -> `assistant` (any requested tool calls are flattened to
        text, since the completion API has no native tool-call channel)
      * `tool`      -> `user` (the tool result is fed back as user text so the
        model can react to it)
    """
    converted: list[dict] = []

    for msg in messages:
        role = msg.get("role")
        if role == "system":
            converted.append(
                {"role": "system", "text": str(msg.get("content", ""))}
            )
        elif role == "user":
            converted.append(
                {"role": "user", "text": str(msg.get("content", ""))}
            )
        elif role == "assistant":
            text = str(msg.get("content", "") or "")
            for call in msg.get("tool_calls", []):
                # Flatten the tool request into readable text.
                args = json.dumps(call.get("arguments", {}), ensure_ascii=False)
                text = (text + f"\n[tool_call {call['name']} {args}]").strip()
            converted.append({"role": "assistant", "text": text})
        elif role == "tool":
            converted.append(
                {
                    "role": "user",
                    "text": f"[tool_result] {msg.get('content', '')}",
                }
            )

    return converted


def parse_response_yandex(raw: dict, fallback_model: str) -> LLMResponse:
    """Parses a raw YandexGPT completion response into an `LLMResponse`.

    The API returns `{"result": {"alternatives": [{"message": {...}}], ...}}`.
    The first alternative's message text becomes the response content.
    """
    result = raw.get("result", {})
    alternatives = result.get("alternatives", [])
    text = ""
    if alternatives:
        text = alternatives[0].get("message", {}).get("text", "") or ""
    return LLMResponse(
        content=text,
        tool_calls=[],
        model=result.get("modelVersion", fallback_model),
    )


# --- GigaChat message conversion --------------------------------------------


def convert_messages_gigachat(messages: list[dict]) -> list[dict]:
    """Converts the internal message list into GigaChat's chat format.

    GigaChat's API is OpenAI-like, but to keep the skeleton simple this
    adapter targets plain chat (no native tool-call channel).  Role mapping:

      * `system`    -> `system`
      * `user`      -> `user`
      * `assistant` -> `assistant` (requested tool calls flattened to text)
      * `tool`      -> `user` (the tool result fed back as user text)
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
            content = str(msg.get("content", "") or "")
            for call in msg.get("tool_calls", []):
                args = json.dumps(call.get("arguments", {}), ensure_ascii=False)
                content = (
                    content + f"\n[tool_call {call['name']} {args}]"
                ).strip()
            converted.append({"role": "assistant", "content": content})
        elif role == "tool":
            converted.append(
                {
                    "role": "user",
                    "content": f"[tool_result] {msg.get('content', '')}",
                }
            )

    return converted


def parse_response_gigachat(raw: dict, fallback_model: str) -> LLMResponse:
    """Parses a raw GigaChat chat-completions response into an `LLMResponse`.

    GigaChat mirrors the OpenAI shape: `{"choices": [{"message": {...}}]}`.
    The first choice's message content becomes the response text.
    """
    choices = raw.get("choices", [])
    message = choices[0].get("message", {}) if choices else {}
    return LLMResponse(
        content=message.get("content") or "",
        tool_calls=[],
        model=raw.get("model", fallback_model),
    )


# --- Providers ---------------------------------------------------------------


class YandexGPTProvider(LLMProvider):
    """Calls the Yandex Foundation Models / YandexGPT completion API.

    CIS-region provider — data stays within Yandex Cloud (Russia data
    residency).  Authentication uses an API key (`YANDEX_API_KEY`) plus the
    Yandex Cloud folder id, which together build the `modelUri`.
    """

    def __init__(
        self,
        model: str = "yandexgpt",
        api_key: str | None = None,
        folder_id: str | None = None,
        max_tokens: int = _YANDEX_DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = _YANDEX_MODEL_ALIASES.get(model, model)
        self._api_key = api_key or os.environ.get("YANDEX_API_KEY", "")
        self._folder_id = folder_id or os.environ.get("YANDEX_FOLDER_ID", "")
        self._max_tokens = max_tokens

    @property
    def model_uri(self) -> str:
        """The `gpt://<folder_id>/<model>` URI required by the API."""
        return f"gpt://{self._folder_id}/{self.model}"

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            _YANDEX_API_URL,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "authorization": f"Api-Key {self._api_key}",
                "x-folder-id": self._folder_id,
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        # `tools` is accepted for interface parity; the completion API has no
        # native tool-call channel, so tool requests are surfaced as text.
        payload: dict = {
            "modelUri": self.model_uri,
            "completionOptions": {
                "stream": False,
                "maxTokens": str(self._max_tokens),
            },
            "messages": convert_messages_yandex(messages),
        }

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return parse_response_yandex(raw, self.model)


class GigaChatProvider(LLMProvider):
    """Calls SberCloud GigaChat's chat-completions API.

    CIS-region provider — data stays within SberCloud (Russia data
    residency).  Authentication uses a bearer access token (`GIGACHAT_TOKEN`),
    which the caller obtains from SberCloud's OAuth endpoint.
    """

    def __init__(
        self,
        model: str = "GigaChat",
        access_token: str | None = None,
        max_tokens: int = _GIGACHAT_DEFAULT_MAX_TOKENS,
    ) -> None:
        self.model = _GIGACHAT_MODEL_ALIASES.get(model, model)
        self._access_token = access_token or os.environ.get(
            "GIGACHAT_TOKEN", ""
        )
        self._max_tokens = max_tokens

    def _request(self, payload: dict) -> dict:
        """Performs the blocking HTTP POST (runs in a worker thread)."""
        req = urllib.request.Request(
            _GIGACHAT_API_URL,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "content-type": "application/json",
                "accept": "application/json",
                "authorization": f"Bearer {self._access_token}",
            },
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())

    async def complete(
        self, messages: list[dict], tools: list[dict] | None = None
    ) -> LLMResponse:
        # `tools` is accepted for interface parity; this adapter targets plain
        # chat, so tool requests are surfaced as text.
        payload: dict = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "messages": convert_messages_gigachat(messages),
        }

        try:
            raw = await asyncio.to_thread(self._request, payload)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return LLMResponse(
                content=f"LLM provider error: {exc}", model=self.model
            )

        return parse_response_gigachat(raw, self.model)
