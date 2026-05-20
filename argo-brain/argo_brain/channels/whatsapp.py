"""WhatsApp Cloud API channel adapter — spec section 4.5.

WhatsApp is a push-based platform: Meta's Cloud API delivers messages by
HTTP POST to ``/webhook/whatsapp`` on the gateway. This adapter extends
`WebhookChannel`. Outbound messages use the Cloud API messages endpoint.

The Cloud API also performs a one-time GET-style webhook verification
handshake (``hub.mode`` / ``hub.verify_token`` / ``hub.challenge``); this
adapter answers it in `verify()`.

Dependency-free: HTTP is done with the stdlib `urllib`, moved to a worker
thread via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class WhatsAppChannel(WebhookChannel):
    """WhatsApp Cloud API adapter (webhook inbound) — spec section 4.5."""

    name = "whatsapp"
    auth = AuthMode.TOKEN

    # Graph API version used for the Cloud API messages endpoint.
    _GRAPH_VERSION = "v18.0"

    def __init__(self, access_token: str, phone_number_id: str,
                 verify_token: str = "") -> None:
        """Stores Cloud API credentials without connecting.

        `phone_number_id` is the WhatsApp business phone number id used in
        the messages endpoint URL. `verify_token` is the shared secret the
        gateway expects during the one-time webhook verification handshake.
        """
        super().__init__()
        if not access_token:
            raise ValueError("WhatsApp access token is required")
        if not phone_number_id:
            raise ValueError("WhatsApp phone_number_id is required")
        self._token = access_token
        self._phone_number_id = phone_number_id
        self._verify_token = verify_token
        self._endpoint = (
            f"https://graph.facebook.com/{self._GRAPH_VERSION}/"
            f"{phone_number_id}/messages"
        )

    def verify(self, payload: dict) -> dict | None:
        """Handles the Cloud API webhook verification handshake.

        Meta sends a GET request whose query parameters are passed in here
        as a dict: ``hub.mode``, ``hub.verify_token`` and ``hub.challenge``.
        When the mode is ``subscribe`` and the token matches the configured
        `verify_token`, the challenge value must be echoed back.
        """
        if payload.get("hub.mode") != "subscribe":
            return None
        if "hub.challenge" not in payload:
            return None
        # When a verify token is configured, it must match exactly.
        if self._verify_token and \
                payload.get("hub.verify_token") != self._verify_token:
            return None
        return {"hub.challenge": payload.get("hub.challenge", "")}

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts the first text message from a Cloud API webhook payload.

        A Cloud API payload looks like::

            {"entry": [{"changes": [{"value": {
                "messages": [{"from": "1555...", "type": "text",
                              "text": {"body": "hi"}}]}}]}]}

        Status callbacks (``statuses``) and non-text messages yield `None`.
        """
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    if message.get("type") != "text":
                        continue
                    text = message.get("text", {}).get("body")
                    if not text:
                        continue
                    sender = message.get("from", "unknown")
                    return ChannelMessage(
                        channel=self.name,
                        user_id=f"whatsapp:{sender}",
                        # Replies are addressed back to the sender's number.
                        target=str(sender),
                        text=str(text),
                        raw=payload,
                    )
        return None

    async def send(self, target: str, text: str) -> None:
        """Sends `text` to a WhatsApp number via the Cloud API."""
        if not target:
            return
        body = {
            "messaging_product": "whatsapp",
            "to": target,
            "type": "text",
            "text": {"body": text or "(empty reply)"},
        }
        try:
            await asyncio.to_thread(
                _post_json,
                self._endpoint,
                body,
                {"Authorization": f"Bearer {self._token}"},
            )
        except (urllib.error.URLError, OSError):
            pass
