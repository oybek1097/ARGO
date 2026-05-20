"""DingTalk channel adapter — spec section 4.5.

DingTalk (DingDing) delivers bot messages by HTTP POST to
``/webhook/dingtalk`` on the gateway, so this adapter extends
`WebhookChannel`. Outbound replies are POSTed to the DingTalk bot webhook
URL provided when the channel is constructed.

Dependency-free: HTTP uses the stdlib `urllib`, moved to a worker thread
via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelHealth, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class DingTalkChannel(WebhookChannel):
    """DingTalk bot adapter (webhook inbound) — spec section 4.5."""

    name = "dingtalk"
    auth = AuthMode.WEBHOOK_SECRET

    def __init__(self, webhook_url: str) -> None:
        """Stores the DingTalk bot webhook URL without connecting.

        `webhook_url` is the outgoing-bot webhook URL DingTalk replies are
        POSTed to.
        """
        super().__init__()
        if not webhook_url:
            raise ValueError("DingTalk webhook_url is required")
        self._webhook_url = webhook_url

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts the text from a DingTalk bot callback payload.

        A DingTalk bot callback carries ``msgtype`` ``"text"`` with the body
        under ``text.content``; ``senderId`` identifies the user and
        ``conversationId`` is the reply target. Non-text or empty payloads
        return ``None``.
        """
        if payload.get("msgtype") != "text":
            return None

        text_block = payload.get("text")
        if not isinstance(text_block, dict):
            return None

        # DingTalk pads @-mention text with leading whitespace.
        text = str(text_block.get("content", "")).strip()
        if not text:
            return None

        sender_id = payload.get("senderId", "unknown")
        conversation_id = payload.get("conversationId", "")

        return ChannelMessage(
            channel=self.name,
            user_id=f"dingtalk:{sender_id}",
            target=str(conversation_id),
            text=text,
            raw=payload,
        )

    async def send(self, target: str, text: str) -> None:
        """POSTs a text message to the DingTalk bot webhook.

        The ``target`` (conversation id) is informational only — the
        DingTalk session webhook already addresses the conversation.
        Network errors are swallowed so delivery failures never crash the
        agent loop.
        """
        body = {"msgtype": "text", "text": {"content": text}}
        try:
            await asyncio.to_thread(_post_json, self._webhook_url, body)
        except (urllib.error.URLError, OSError):
            pass

    def health(self) -> ChannelHealth:
        """Reports adapter health (offline check, no network call)."""
        return ChannelHealth(ok=True, detail="dingtalk webhook")
