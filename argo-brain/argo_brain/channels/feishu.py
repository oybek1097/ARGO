"""Feishu / Lark channel adapter — spec section 4.5.

Feishu (Lark outside mainland China) is a push-based platform: the
platform delivers events by HTTP POST to ``/webhook/feishu`` on the
gateway. This adapter therefore extends `WebhookChannel`.

Two inbound payload shapes are handled:

* The one-time URL-verification challenge, answered by `verify()`.
* An event-callback carrying a user message, parsed by `parse_webhook()`.

Outbound messages are POSTed to the Feishu message API. HTTP is done with
the stdlib `urllib`, moved to a worker thread via `asyncio.to_thread` so
the async `Channel` contract holds — no third-party dependencies.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelHealth, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class FeishuChannel(WebhookChannel):
    """Feishu / Lark adapter (webhook inbound) — spec section 4.5."""

    name = "feishu"
    auth = AuthMode.TOKEN

    # Feishu message-send endpoint; `receive_id_type` selects the id scheme.
    _SEND_URL = (
        "https://open.feishu.cn/open-apis/im/v1/messages"
        "?receive_id_type=chat_id"
    )

    def __init__(self, tenant_access_token: str) -> None:
        """Stores the Feishu tenant access token without connecting.

        `tenant_access_token` is the bot's tenant access token used to
        authorize outbound calls to the Feishu message API.
        """
        super().__init__()
        if not tenant_access_token:
            raise ValueError("Feishu tenant_access_token is required")
        self._token = tenant_access_token

    def verify(self, payload: dict) -> dict | None:
        """Answers the Feishu URL-verification handshake.

        On configuration, Feishu POSTs ``{"challenge": "...", "type":
        "url_verification"}``. The endpoint must echo the challenge back.
        """
        if "challenge" in payload:
            return {"challenge": payload.get("challenge", "")}
        return None

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts a text message from a Feishu event-callback payload.

        Feishu's v2 event schema nests the event under ``header`` /
        ``event``; a message event carries ``event.message`` with a JSON
        string ``content`` like ``{"text": "hello"}``. Non-message or empty
        payloads return ``None``.
        """
        # Never treat the verification handshake as a message.
        if "challenge" in payload:
            return None

        event = payload.get("event")
        if not isinstance(event, dict):
            return None

        message = event.get("message")
        if not isinstance(message, dict):
            return None

        # Only plain-text messages are supported here.
        if message.get("message_type") not in (None, "text"):
            return None

        text = self._extract_text(message.get("content"))
        if not text:
            return None

        # The sender's open_id namespaces the user; the chat id is the
        # reply target.
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {}) if isinstance(sender, dict) else {}
        open_id = sender_id.get("open_id") or sender_id.get("user_id") or "unknown"
        chat_id = message.get("chat_id", "")

        return ChannelMessage(
            channel=self.name,
            user_id=f"feishu:{open_id}",
            target=str(chat_id),
            text=text,
            raw=payload,
        )

    @staticmethod
    def _extract_text(content: object) -> str:
        """Pulls the ``text`` field out of a Feishu message ``content``.

        Feishu encodes ``content`` as a JSON string; tolerate a dict too.
        """
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (ValueError, TypeError):
                return ""
        if isinstance(content, dict):
            return str(content.get("text", ""))
        return ""

    async def send(self, target: str, text: str) -> None:
        """POSTs a text message to the Feishu message API.

        Network errors are swallowed so a delivery failure never crashes
        the agent loop.
        """
        if not target:
            return
        body = {
            "receive_id": target,
            "msg_type": "text",
            "content": json.dumps({"text": text}),
        }
        try:
            await asyncio.to_thread(
                _post_json,
                self._SEND_URL,
                body,
                {"Authorization": f"Bearer {self._token}"},
            )
        except (urllib.error.URLError, OSError):
            pass

    def health(self) -> ChannelHealth:
        """Reports adapter health (offline check, no network call)."""
        return ChannelHealth(ok=True, detail="feishu webhook")
