"""LINE Messaging API channel adapter — spec section 4.5.

LINE is a push-based platform: the LINE platform delivers events by HTTP
POST to ``/webhook/line`` on the gateway. This adapter therefore extends
`WebhookChannel`. Outbound messages use the LINE Messaging API: a reply
via the short-lived reply token, or a push to a user id.

Dependency-free: HTTP is done with the stdlib `urllib`, moved to a worker
thread via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class LINEChannel(WebhookChannel):
    """LINE Messaging API adapter (webhook inbound) — spec section 4.5."""

    name = "line"
    auth = AuthMode.TOKEN

    # LINE Messaging API endpoints.
    _REPLY_ENDPOINT = "https://api.line.me/v2/bot/message/reply"
    _PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"

    def __init__(self, channel_access_token: str) -> None:
        """Stores the LINE channel access token without connecting."""
        super().__init__()
        if not channel_access_token:
            raise ValueError("LINE channel access token is required")
        self._token = channel_access_token

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts the first text message event from a LINE webhook payload.

        A LINE webhook payload looks like::

            {"events": [{"type": "message", "replyToken": "...",
                         "source": {"userId": "U..."},
                         "message": {"type": "text", "text": "hi"}}]}

        Returns `None` for payloads with no text message event. The reply
        token is preferred as the reply `target` (it is single-use and
        time-limited); callers may fall back to the user id for a push.
        """
        events = payload.get("events", [])
        for event in events:
            if event.get("type") != "message":
                continue
            message = event.get("message", {})
            if message.get("type") != "text":
                continue
            text = message.get("text")
            if not text:
                continue
            source = event.get("source", {})
            user_id = source.get("userId", "unknown")
            # Prefer the reply token; fall back to the user id for a push.
            target = event.get("replyToken") or user_id
            return ChannelMessage(
                channel=self.name,
                user_id=f"line:{user_id}",
                target=str(target),
                text=str(text),
                raw=payload,
            )
        return None

    async def send(self, target: str, text: str) -> None:
        """Sends `text` to `target` via the LINE Messaging API.

        A reply token (issued per inbound event) is short and opaque; a
        user id always starts with ``U``. We pick the reply endpoint for a
        reply token and the push endpoint for a user id.
        """
        if not target:
            return
        messages = [{"type": "text", "text": text or "(empty reply)"}]
        if target.startswith("U"):
            url = self._PUSH_ENDPOINT
            body = {"to": target, "messages": messages}
        else:
            url = self._REPLY_ENDPOINT
            body = {"replyToken": target, "messages": messages}
        try:
            await asyncio.to_thread(
                _post_json,
                url,
                body,
                {"Authorization": f"Bearer {self._token}"},
            )
        except (urllib.error.URLError, OSError):
            pass
