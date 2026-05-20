"""Telegram channel adapter — spec section 4.5.

Uses the Telegram Bot API with long polling (`getUpdates`). Dependency-free:
HTTP is done with the stdlib `urllib`, moved to a worker thread so the async
interface holds.

Webhook mode (with HMAC secret verification) is a later-sprint addition;
long polling needs no public endpoint and works behind NAT.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import AsyncIterator

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)

log = logging.getLogger("argo_brain.channels.telegram")

_API_ROOT = "https://api.telegram.org"
_MAX_TEXT = 4096  # Telegram's per-message character limit


class TelegramChannel(Channel):
    """Telegram Bot API adapter (long-polling)."""

    name = "telegram"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(self, token: str, poll_timeout: int = 30) -> None:
        if not token:
            raise ValueError("Telegram bot token kerak")
        self._token = token
        self._base = f"{_API_ROOT}/bot{token}"
        self._poll_timeout = poll_timeout
        self._offset = 0
        self._running = False

    # --- HTTP plumbing ------------------------------------------------------

    def _api(self, method: str, params: dict) -> dict:
        """Blocking Bot API call (runs in a worker thread)."""
        url = f"{self._base}/{method}"
        data = urllib.parse.urlencode(params).encode()
        # The read timeout must outlast the long-poll timeout.
        with urllib.request.urlopen(url, data=data,
                                    timeout=self._poll_timeout + 15) as resp:
            return json.loads(resp.read())

    async def _call(self, method: str, params: dict) -> dict:
        return await asyncio.to_thread(self._api, method, params)

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        me = await self._call("getMe", {})
        username = me.get("result", {}).get("username", "?")
        log.info("Telegram channel started as @%s", username)

    async def stop(self) -> None:
        self._running = False

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        # Telegram rejects empty or over-long messages; chunk if needed.
        for chunk in self._chunks(text or "(boʻsh javob)"):
            await self._call("sendMessage", {"chat_id": target, "text": chunk})

    @staticmethod
    def _chunks(text: str) -> list[str]:
        return [text[i:i + _MAX_TEXT] for i in range(0, len(text), _MAX_TEXT)]

    # --- receiving ----------------------------------------------------------

    @staticmethod
    def parse_update(update: dict) -> ChannelMessage | None:
        """Converts a raw Telegram update into a `ChannelMessage`.

        Returns `None` for updates without usable text (joins, edits of
        non-text content, callbacks, ...).
        """
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return None
        text = msg.get("text")
        if not text:
            return None
        chat_id = msg.get("chat", {}).get("id")
        from_id = msg.get("from", {}).get("id")
        if chat_id is None or from_id is None:
            return None
        return ChannelMessage(
            channel="telegram",
            user_id=f"telegram:{from_id}",
            target=str(chat_id),
            text=text,
            raw=update,
        )

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Long-polls Telegram and yields inbound text messages."""
        while self._running:
            try:
                data = await self._call(
                    "getUpdates",
                    {"offset": self._offset, "timeout": self._poll_timeout},
                )
            except (urllib.error.URLError, TimeoutError, OSError,
                    json.JSONDecodeError) as exc:
                log.warning("getUpdates failed, retrying: %s", exc)
                await asyncio.sleep(3)
                continue

            for update in data.get("result", []):
                self._offset = update.get("update_id", self._offset) + 1
                parsed = self.parse_update(update)
                if parsed is not None:
                    yield parsed

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="polling" if self._running else "stopped",
        )
