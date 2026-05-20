"""Viber channel adapter — spec section 4.5.

Viber is a push-based platform: the Viber service delivers callbacks by
HTTP POST to ``/webhook/viber`` on the gateway. This adapter extends
`WebhookChannel`. Outbound messages use the Viber ``send_message`` API.

Dependency-free: HTTP is done with the stdlib `urllib`, moved to a worker
thread via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class ViberChannel(WebhookChannel):
    """Viber REST API adapter (webhook inbound) — spec section 4.5."""

    name = "viber"
    auth = AuthMode.TOKEN

    # Viber send_message API endpoint.
    _SEND_ENDPOINT = "https://chatapi.viber.com/pa/send_message"

    def __init__(self, auth_token: str, sender_name: str = "ARGO") -> None:
        """Stores the Viber bot auth token without connecting."""
        super().__init__()
        if not auth_token:
            raise ValueError("Viber auth token is required")
        self._token = auth_token
        self._sender_name = sender_name

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts a text "message" callback from a Viber webhook payload.

        A Viber "message" callback looks like::

            {"event": "message", "sender": {"id": "01..."},
             "message": {"type": "text", "text": "hi"}}

        Returns `None` for non-message events (delivered, seen, conversation
        started, etc.) and for messages without text.
        """
        if payload.get("event") != "message":
            return None
        message = payload.get("message", {})
        if message.get("type") != "text":
            return None
        text = message.get("text")
        if not text:
            return None
        sender = payload.get("sender", {})
        user_id = sender.get("id", "unknown")
        return ChannelMessage(
            channel=self.name,
            user_id=f"viber:{user_id}",
            # Viber replies are addressed to the same user id.
            target=str(user_id),
            text=str(text),
            raw=payload,
        )

    async def send(self, target: str, text: str) -> None:
        """Sends `text` to a Viber user via the send_message API."""
        if not target:
            return
        body = {
            "receiver": target,
            "sender": {"name": self._sender_name},
            "type": "text",
            "text": text or "(empty reply)",
        }
        try:
            await asyncio.to_thread(
                _post_json,
                self._SEND_ENDPOINT,
                body,
                {"X-Viber-Auth-Token": self._token},
            )
        except (urllib.error.URLError, OSError):
            pass
