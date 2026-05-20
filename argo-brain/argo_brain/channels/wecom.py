"""WeCom (WeChat Work) channel adapter — spec section 4.5.

WeCom (Enterprise WeChat) delivers messages by HTTP POST to
``/webhook/wecom`` on the gateway, so this adapter extends
`WebhookChannel`. Outbound replies are POSTed to the WeCom message API.

Dependency-free: HTTP uses the stdlib `urllib`, moved to a worker thread
via `asyncio.to_thread` so the async `Channel` contract holds.
"""

from __future__ import annotations

import asyncio
import urllib.error

from argo_brain.channels.base import AuthMode, ChannelHealth, ChannelMessage
from argo_brain.channels.webhook import WebhookChannel, _post_json


class WeComChannel(WebhookChannel):
    """WeCom (WeChat Work) adapter (webhook inbound) — spec section 4.5."""

    name = "wecom"
    auth = AuthMode.TOKEN

    # WeCom application-message send endpoint; the access token authorizes
    # the call via the `access_token` query parameter.
    _SEND_URL = (
        "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="
    )

    def __init__(self, access_token: str, agent_id: str) -> None:
        """Stores WeCom credentials without connecting.

        `access_token` authorizes outbound API calls; `agent_id` is the
        WeCom application id messages are sent from.
        """
        super().__init__()
        if not access_token:
            raise ValueError("WeCom access_token is required")
        if not agent_id:
            raise ValueError("WeCom agent_id is required")
        self._access_token = access_token
        self._agent_id = agent_id

    def parse_webhook(self, payload: dict) -> ChannelMessage | None:
        """Extracts text from a WeCom callback payload.

        After the gateway decrypts and XML-to-dict converts a WeCom
        callback, a text message has ``MsgType`` ``"text"`` with the body
        under ``Content``; ``FromUserName`` identifies the sender and
        ``AgentID`` / ``FromUserName`` form the reply target. Non-text or
        empty payloads return ``None``.
        """
        if payload.get("MsgType") != "text":
            return None

        text = str(payload.get("Content", "")).strip()
        if not text:
            return None

        from_user = payload.get("FromUserName", "unknown")

        return ChannelMessage(
            channel=self.name,
            user_id=f"wecom:{from_user}",
            target=str(from_user),
            text=text,
            raw=payload,
        )

    async def send(self, target: str, text: str) -> None:
        """POSTs a text message to the WeCom message API.

        Network errors are swallowed so a delivery failure never crashes
        the agent loop.
        """
        if not target:
            return
        body = {
            "touser": target,
            "msgtype": "text",
            "agentid": self._agent_id,
            "text": {"content": text},
        }
        try:
            await asyncio.to_thread(
                _post_json,
                self._SEND_URL + self._access_token,
                body,
            )
        except (urllib.error.URLError, OSError):
            pass

    def health(self) -> ChannelHealth:
        """Reports adapter health (offline check, no network call)."""
        return ChannelHealth(ok=True, detail="wecom webhook")
