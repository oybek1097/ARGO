"""Google Chat channel adapter — spec section 4.5.

Google Chat is a push-based platform: Google delivers events by HTTP POST
to ``/webhook/google_chat`` on the gateway. This adapter therefore extends
`WebhookChannel`. Outbound messages are POSTed to a Google Chat space
webhook (or the ``spaces.messages.create`` API URL).

Dependency-free: HTTP is done with the stdlib `urllib`, moved to a worker
thread via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelHealth, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class GoogleChatChannel(WebhookChannel):
    """Google Chat adapter (webhook inbound) — spec section 4.5."""

    name = "google_chat"
    auth = AuthMode.WEBHOOK_SECRET

    def __init__(self, webhook_url: str) -> None:
        """Stores the Google Chat space webhook URL without connecting.

        `webhook_url` is the incoming-webhook (or ``spaces.messages.create``
        API) URL Google Chat replies are POSTed to.
        """
        super().__init__()
        if not webhook_url:
            raise ValueError("Google Chat webhook_url is required")
        self._webhook_url = webhook_url

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts the text from a Google Chat ``MESSAGE`` event payload.

        A Google Chat event payload looks like::

            {"type": "MESSAGE",
             "message": {"text": "hello chat",
                         "space": {"name": "spaces/AAAA"}},
             "user": {"name": "users/12345",
                      "displayName": "Alice"},
             "space": {"name": "spaces/AAAA"}}

        Returns `None` for non-``MESSAGE`` events (e.g. ``ADDED_TO_SPACE``)
        and for payloads with empty text. The space name is used as the
        reply `target`.
        """
        if payload.get("type") != "MESSAGE":
            return None
        message = payload.get("message", {})
        text = message.get("text")
        if not text:
            return None
        # The user may appear at the top level or inside the message.
        user = payload.get("user") or message.get("sender") or {}
        user_name = user.get("name", "unknown")
        # The space may appear at the top level or inside the message.
        space = payload.get("space") or message.get("space") or {}
        space_name = space.get("name", "")
        return ChannelMessage(
            channel=self.name,
            user_id=f"google_chat:{user_name}",
            target=str(space_name),
            text=str(text),
            raw=payload,
        )

    async def send(self, target: str, text: str) -> None:
        """Sends `text` to a Google Chat space via its webhook / API URL.

        Google Chat ignores the per-message `target` for an incoming
        webhook (the webhook URL is already space-scoped), so `target` is
        accepted for interface symmetry but the configured webhook URL is
        always used.
        """
        if not self._webhook_url:
            return
        body = {"text": text or "(empty reply)"}
        # If a fully-qualified space name was given as the target, attach it
        # so an API-style endpoint can still route the message.
        if target:
            body["space"] = target
        try:
            await asyncio.to_thread(_post_json, self._webhook_url, body)
        except (urllib.error.URLError, OSError):
            pass

    def health(self) -> ChannelHealth:
        return ChannelHealth(ok=True, detail="webhook")
