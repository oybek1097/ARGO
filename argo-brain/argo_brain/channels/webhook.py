"""Webhook-based channel adapters — spec section 4.5.

Unlike Telegram (which long-polls), these channels are *push-based*: the
platform delivers messages by HTTP POST to `/webhook/<platform>` on the
gateway. This needs no WebSocket client, so it stays dependency-free.

Ships a generic webhook channel and a Slack adapter (Events API).
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import AsyncIterator

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)


class WebhookChannel(Channel):
    """Base class for push-based (webhook) channels.

    Webhook channels do not poll: the gateway feeds them payloads via
    `verify()` / `parse_webhook()`. `receive()` therefore yields nothing.
    """

    direction = ChannelDirection.BIDIRECTIONAL

    def __init__(self) -> None:
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        # Push-based: there is nothing to poll.
        return
        yield  # noqa — unreachable, but makes this an async generator

    def verify(self, payload: dict) -> dict | None:
        """Return a dict to reply with immediately (e.g. a handshake).

        Default: no verification step.
        """
        return None

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Convert a raw webhook payload into a `ChannelMessage`."""
        raise NotImplementedError

    def health(self) -> ChannelHealth:
        return ChannelHealth(ok=True, detail="webhook")


def _post_json(url: str, body: dict, headers: dict | None = None) -> None:
    """Blocking JSON POST helper (run via `asyncio.to_thread`)."""
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


class GenericWebhookChannel(WebhookChannel):
    """Accepts a simple JSON envelope from any HTTP service.

    Inbound:  ``{"user_id": "...", "message": "...", "reply_url": "..."}``
    Outbound: HTTP POST ``{"text": "..."}`` to ``reply_url`` if one was given.
    """

    name = "generic"
    auth = AuthMode.WEBHOOK_SECRET

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        text = payload.get("message") or payload.get("text")
        if not text:
            return None
        user_id = str(payload.get("user_id", "webhook-user"))
        return ChannelMessage(
            channel=self.name,
            user_id=f"generic:{user_id}",
            target=str(payload.get("reply_url", "")),
            text=str(text),
            raw=payload,
        )

    async def send(self, target: str, text: str) -> None:
        if not target:
            return  # fire-and-forget inbound, no reply URL
        try:
            await asyncio.to_thread(_post_json, target, {"text": text})
        except (urllib.error.URLError, OSError):
            pass


class SlackChannel(WebhookChannel):
    """Slack adapter via the Events API — spec section 4.5.

    Inbound via ``POST /webhook/slack``; outbound via ``chat.postMessage``.
    """

    name = "slack"
    auth = AuthMode.OAUTH
    _POST_MESSAGE = "https://slack.com/api/chat.postMessage"

    def __init__(self, bot_token: str) -> None:
        super().__init__()
        if not bot_token:
            raise ValueError("Slack bot token is required")
        self._token = bot_token

    def verify(self, payload: dict) -> dict | None:
        # Slack's one-time URL-verification handshake.
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge", "")}
        return None

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        event = payload.get("event", {})
        if event.get("type") != "message":
            return None
        # Ignore bot messages (including our own) to prevent reply loops.
        if event.get("bot_id") or event.get("subtype"):
            return None
        text = event.get("text")
        if not text:
            return None
        return ChannelMessage(
            channel=self.name,
            user_id=f"slack:{event.get('user', 'unknown')}",
            target=str(event.get("channel", "")),
            text=text,
            raw=payload,
        )

    async def send(self, target: str, text: str) -> None:
        if not target:
            return
        try:
            await asyncio.to_thread(
                _post_json,
                self._POST_MESSAGE,
                {"channel": target, "text": text},
                {"Authorization": f"Bearer {self._token}"},
            )
        except (urllib.error.URLError, OSError):
            pass
