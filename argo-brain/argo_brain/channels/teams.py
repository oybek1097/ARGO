"""Microsoft Teams channel adapter — spec section 4.5.

Microsoft Teams (via the Bot Framework) is a push-based platform: the Bot
Framework delivers activities by HTTP POST to ``/webhook/teams`` on the
gateway. This adapter therefore extends `WebhookChannel`. Outbound replies
are POSTed back as activities to the inbound activity's ``serviceUrl``.

Dependency-free: HTTP is done with the stdlib `urllib`, moved to a worker
thread via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelHealth, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class TeamsChannel(WebhookChannel):
    """Microsoft Teams Bot Framework adapter (webhook inbound).

    Spec section 4.5.
    """

    name = "teams"
    auth = AuthMode.TOKEN

    def __init__(self, app_id: str = "", app_password: str = "") -> None:
        """Stores Bot Framework credentials without connecting.

        `app_id` / `app_password` are the Azure Bot registration's
        credentials, used to acquire a bearer token for outbound replies.
        Both default to empty so the adapter can be exercised offline.
        """
        super().__init__()
        self._app_id = app_id
        self._app_password = app_password

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts the text from a Bot Framework activity payload.

        A Teams Bot Framework activity payload looks like::

            {"type": "message",
             "text": "hello teams",
             "from": {"id": "29:user-aad-id", "name": "Alice"},
             "conversation": {"id": "19:meeting@thread.v2"},
             "serviceUrl": "https://smba.trafficmanager.net/..."}

        Returns `None` for non-``message`` activities (e.g.
        ``conversationUpdate``, ``typing``) and for activities with empty
        text. The conversation id is used as the reply `target`.
        """
        if payload.get("type") != "message":
            return None
        text = payload.get("text")
        if not text:
            return None
        sender = payload.get("from", {})
        from_id = sender.get("id", "unknown")
        conversation = payload.get("conversation", {})
        conversation_id = conversation.get("id", "")
        return ChannelMessage(
            channel=self.name,
            user_id=f"teams:{from_id}",
            target=str(conversation_id),
            text=str(text),
            raw=payload,
        )

    async def send(self, target: str, text: str,
                   service_url: str = "") -> None:
        """Sends an activity back to the Bot Framework `serviceUrl`.

        `target` is the conversation id. `service_url` is the inbound
        activity's ``serviceUrl``; without it there is no endpoint to POST
        to, so the call is a no-op (fire-and-forget).
        """
        if not target or not service_url:
            return
        # Bot Framework reply: POST /v3/conversations/{id}/activities.
        base = service_url.rstrip("/")
        url = f"{base}/v3/conversations/{target}/activities"
        activity = {"type": "message", "text": text or "(empty reply)"}
        headers = {}
        if self._app_password:
            # A real deployment exchanges app credentials for a bearer
            # token; offline we simply attach whatever was configured.
            headers["Authorization"] = f"Bearer {self._app_password}"
        try:
            await asyncio.to_thread(_post_json, url, activity, headers)
        except (urllib.error.URLError, OSError):
            pass

    def health(self) -> ChannelHealth:
        return ChannelHealth(ok=True, detail="webhook")
