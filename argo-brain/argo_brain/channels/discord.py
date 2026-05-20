"""Discord channel adapter — spec section 4.5.

Discord has a split API surface:

* **Sending** is plain HTTP REST — `POST /channels/{id}/messages` — so it
  uses the stdlib `urllib`, just like every other adapter here.
* **Receiving** requires the **Discord Gateway**, a WebSocket connection
  over which the bot performs an IDENTIFY handshake, sends periodic
  heartbeats, and receives `MESSAGE_CREATE` dispatch events.

Python's standard library has no WebSocket client, so the Gateway side is
built on the focused RFC 6455 client in `argo_brain.channels._ws`. All
blocking socket I/O runs in a worker thread so the async `Channel`
interface is preserved.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import urllib.error
import urllib.request
from collections.abc import AsyncIterator

from argo_brain.channels._ws import WSClient
from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)

log = logging.getLogger("argo_brain.channels.discord")

# Discord REST API base (versioned). Spec section 4.5.
_API_ROOT = "https://discord.com/api/v10"
# Gateway WebSocket URL. v10, JSON encoding.
_GATEWAY_URL = "wss://gateway.discord.gg/?v=10&encoding=json"
# Discord's per-message character limit.
_MAX_TEXT = 2000

# Gateway opcodes (Discord-specific, not WebSocket opcodes).
_OP_DISPATCH = 0        # An event was dispatched.
_OP_HEARTBEAT = 1       # Client -> server keep-alive.
_OP_IDENTIFY = 2        # Client -> server login.
_OP_HELLO = 10          # Server -> client, carries heartbeat_interval.
_OP_HEARTBEAT_ACK = 11  # Server -> client, confirms a heartbeat.

# Gateway intents bitmask: GUILD_MESSAGES (1<<9) + MESSAGE_CONTENT (1<<15)
# + DIRECT_MESSAGES (1<<12). Enough to receive message text in guilds + DMs.
_INTENTS = (1 << 9) | (1 << 12) | (1 << 15)


class DiscordChannel(Channel):
    """Discord adapter — REST for sending, Gateway WebSocket for receiving."""

    name = "discord"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(self, bot_token: str) -> None:
        if not bot_token:
            raise ValueError("Discord bot token is required")
        self._token = bot_token
        self._running = False
        # Last sequence number seen on the Gateway; sent with each heartbeat
        # so the server can detect a missed event.
        self._seq: int | None = None
        self._ws: WSClient | None = None

    # --- HTTP plumbing (sending) -------------------------------------------

    def _post_message(self, channel_id: str, text: str) -> dict:
        """Blocking REST call: POST a message to a channel."""
        url = f"{_API_ROOT}/channels/{channel_id}/messages"
        body = json.dumps({"content": text}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        # Bot tokens authenticate with the "Bot" auth scheme.
        req.add_header("Authorization", f"Bot {self._token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "ARGO-Agent (argo-brain, 1.0)")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())

    async def _call_post(self, channel_id: str, text: str) -> dict:
        return await asyncio.to_thread(self._post_message, channel_id, text)

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        log.info("Discord channel started")

    async def stop(self) -> None:
        self._running = False
        if self._ws is not None:
            self._ws.close()

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        """Sends a text message to a channel; long text is chunked."""
        for chunk in self._chunks(text or "(empty reply)"):
            await self._call_post(target, chunk)

    @staticmethod
    def _chunks(text: str) -> list[str]:
        """Splits `text` into Discord-sized (<= 2000 char) pieces."""
        return [text[i:i + _MAX_TEXT] for i in range(0, len(text), _MAX_TEXT)]

    # --- receiving ----------------------------------------------------------

    @staticmethod
    def parse_message(event: dict) -> ChannelMessage | None:
        """Converts a `MESSAGE_CREATE` payload into a `ChannelMessage`.

        Pure function (tested fully offline, spec section 4.5). `event` is
        the `d` field of a Gateway dispatch frame. Returns `None` when the
        message is not usable:

        * messages authored by a bot (`author.bot` is true) are skipped to
          avoid the bot reacting to itself or other bots;
        * messages with empty `content` (embeds-only, attachments-only, ...)
          are skipped.
        """
        if not event:
            return None
        author = event.get("author") or {}
        # Ignore anything sent by a bot account (including ourselves).
        if author.get("bot"):
            return None
        content = event.get("content")
        if not content:
            return None
        author_id = author.get("id")
        channel_id = event.get("channel_id")
        if author_id is None or channel_id is None:
            return None
        return ChannelMessage(
            channel="discord",
            user_id=f"discord:{author_id}",
            target=str(channel_id),
            text=content,
            raw=event,
        )

    def _identify_payload(self) -> str:
        """Builds the Gateway IDENTIFY frame (opcode 2)."""
        return json.dumps({
            "op": _OP_IDENTIFY,
            "d": {
                "token": self._token,
                "intents": _INTENTS,
                "properties": {
                    "os": "linux",
                    "browser": "argo-brain",
                    "device": "argo-brain",
                },
            },
        })

    def _heartbeat_payload(self) -> str:
        """Builds a Gateway HEARTBEAT frame (opcode 1) with the last seq."""
        return json.dumps({"op": _OP_HEARTBEAT, "d": self._seq})

    def _gateway_session(self) -> list[ChannelMessage]:
        """Runs one blocking Gateway session, returning collected messages.

        Connects the WebSocket, waits for HELLO, sends IDENTIFY, then reads
        frames. A heartbeat is sent whenever the interval elapses. The loop
        ends when the channel is stopped or the connection drops; whatever
        `MESSAGE_CREATE` events were seen are returned to the async caller.
        """
        messages: list[ChannelMessage] = []
        ws = WSClient()
        self._ws = ws
        ws.connect(_GATEWAY_URL)

        # First frame from the Gateway is always HELLO with the interval.
        hello = json.loads(ws.recv())
        interval_ms = hello.get("d", {}).get("heartbeat_interval", 41250)
        interval = interval_ms / 1000.0

        ws.send(self._identify_payload())
        next_heartbeat = time.monotonic() + interval

        while self._running:
            now = time.monotonic()
            if now >= next_heartbeat:
                ws.send(self._heartbeat_payload())
                next_heartbeat = now + interval

            frame = ws.recv()
            payload = json.loads(frame)

            seq = payload.get("s")
            if seq is not None:
                self._seq = seq

            op = payload.get("op")
            if op == _OP_HELLO:
                # A re-HELLO can arrive on resume; refresh the interval.
                interval = payload.get("d", {}).get(
                    "heartbeat_interval", interval_ms
                ) / 1000.0
            elif op == _OP_HEARTBEAT:
                # Server asked for an immediate heartbeat.
                ws.send(self._heartbeat_payload())
            elif op == _OP_HEARTBEAT_ACK:
                pass
            elif op == _OP_DISPATCH and payload.get("t") == "MESSAGE_CREATE":
                parsed = self.parse_message(payload.get("d", {}))
                if parsed is not None:
                    messages.append(parsed)
                    # Hand events back promptly rather than batching forever.
                    return messages

        return messages

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Connects to the Discord Gateway and yields inbound messages."""
        while self._running:
            try:
                batch = await asyncio.to_thread(self._gateway_session)
            except (ConnectionError, OSError, json.JSONDecodeError) as exc:
                log.warning("Gateway session failed, retrying: %s", exc)
                await asyncio.sleep(5)
                continue
            for parsed in batch:
                yield parsed

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="gateway" if self._running else "stopped",
        )
