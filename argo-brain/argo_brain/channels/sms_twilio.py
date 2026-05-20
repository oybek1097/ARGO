"""Twilio SMS channel adapter — spec section 4.5.

Twilio is a push-based platform: when an SMS arrives, Twilio delivers it
by HTTP POST to ``/webhook/sms`` on the gateway. This adapter extends
`WebhookChannel`. Outbound messages use the Twilio Messages REST API.

The Twilio Messages API expects ``application/x-www-form-urlencoded`` body
data and HTTP Basic auth (Account SID + auth token), so this adapter does
not reuse the JSON `_post_json` helper from `webhook.py`.

Dependency-free: HTTP is done with the stdlib `urllib`, moved to a worker
thread via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import base64
import urllib.error
import urllib.parse
import urllib.request

from argo_brain.channels.base import AuthMode, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel


class TwilioSMSChannel(WebhookChannel):
    """Twilio SMS adapter (webhook inbound) — spec section 4.5."""

    name = "sms"
    auth = AuthMode.TOKEN

    # Twilio Messages REST API base.
    _API_BASE = "https://api.twilio.com/2010-04-01"

    def __init__(self, account_sid: str, auth_token: str,
                 from_number: str) -> None:
        """Stores Twilio credentials without connecting.

        `from_number` is the Twilio phone number messages are sent from
        (E.164 format, e.g. ``+15551234567``).
        """
        super().__init__()
        if not account_sid:
            raise ValueError("Twilio account_sid is required")
        if not auth_token:
            raise ValueError("Twilio auth_token is required")
        if not from_number:
            raise ValueError("Twilio from_number is required")
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_number = from_number
        self._endpoint = (
            f"{self._API_BASE}/Accounts/{account_sid}/Messages.json"
        )

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts the SMS body and sender from a Twilio webhook payload.

        Twilio posts an inbound SMS as form fields, which the gateway
        passes here as a dict::

            {"From": "+15557654321", "To": "+15551234567",
             "Body": "hi", "MessageSid": "SM..."}

        Returns `None` for payloads with no ``Body`` (e.g. status callbacks).
        """
        text = payload.get("Body")
        if not text:
            return None
        sender = payload.get("From", "unknown")
        return ChannelMessage(
            channel=self.name,
            user_id=f"sms:{sender}",
            # Replies go back to the originating phone number.
            target=str(sender),
            text=str(text),
            raw=payload,
        )

    def _post_form(self, body: dict) -> None:
        """Blocking form-encoded POST with HTTP Basic auth (worker thread)."""
        data = urllib.parse.urlencode(body).encode()
        credentials = f"{self._account_sid}:{self._auth_token}"
        token = base64.b64encode(credentials.encode()).decode()
        req = urllib.request.Request(
            self._endpoint,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {token}",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()

    async def send(self, target: str, text: str) -> None:
        """Sends an SMS to `target` via the Twilio Messages API."""
        if not target:
            return
        body = {
            "From": self._from_number,
            "To": target,
            "Body": text or "(empty reply)",
        }
        try:
            await asyncio.to_thread(self._post_form, body)
        except (urllib.error.URLError, OSError):
            pass
