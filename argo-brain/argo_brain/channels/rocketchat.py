"""Rocket.Chat channel adapter — spec section 4.5.

Uses the Rocket.Chat REST API (v1). Dependency-free: HTTP is done with the
stdlib `urllib`, moved to a worker thread so the async `Channel` interface
holds.

Rocket.Chat authenticates REST calls with a paired `X-User-Id` /
`X-Auth-Token` header set. Inbound messages are gathered by polling
`GET /api/v1/channels.history` for the rooms the bot watches. Outbound
messages use `POST /api/v1/chat.postMessage`.
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

log = logging.getLogger("argo_brain.channels.rocketchat")

# Rocket.Chat REST API prefix (spec section 4.5).
_API_PREFIX = "/api/v1"
# Seconds between inbound polling passes.
_POLL_INTERVAL = 5.0


class RocketChatChannel(Channel):
    """Rocket.Chat REST API adapter (poll-based receive)."""

    name = "rocketchat"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(self, server_url: str, user_id: str,
                 auth_token: str) -> None:
        if not server_url:
            raise ValueError("Rocket.Chat server_url is required")
        if not user_id:
            raise ValueError("Rocket.Chat user_id is required")
        if not auth_token:
            raise ValueError("Rocket.Chat auth_token is required")
        # Normalize: strip a trailing slash so URL joining is predictable.
        self._server_url = server_url.rstrip("/")
        self._user_id = user_id
        self._auth_token = auth_token
        self._base = f"{self._server_url}{_API_PREFIX}"
        self._running = False
        # Rooms to poll for inbound messages, plus the last seen message
        # timestamp (ISO 8601) per room so each poll is incremental.
        self._watched: dict[str, str | None] = {}

    # --- HTTP plumbing ------------------------------------------------------

    def _request(self, method: str, path: str, params: dict | None = None,
                 body: dict | None = None, timeout: float = 30.0) -> dict:
        """Blocking REST API call (runs in a worker thread)."""
        url = f"{self._base}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        # Rocket.Chat pairs a user id and a token for REST auth.
        req.add_header("X-User-Id", self._user_id)
        req.add_header("X-Auth-Token", self._auth_token)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    async def _call(self, method: str, path: str, params: dict | None = None,
                    body: dict | None = None, timeout: float = 30.0) -> dict:
        return await asyncio.to_thread(
            self._request, method, path, params, body, timeout
        )

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        # /me confirms the user-id / auth-token pair is valid before polling.
        me = await self._call("GET", "/me")
        log.info("Rocket.Chat channel started as %s",
                 me.get("username", "?"))

    async def stop(self) -> None:
        self._running = False

    def watch(self, room_id: str) -> None:
        """Registers a Rocket.Chat room id for inbound polling."""
        self._watched.setdefault(room_id, None)

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        """Sends a text message via POST /api/v1/chat.postMessage."""
        body = {"roomId": target, "text": text or "(empty reply)"}
        await self._call("POST", "/chat.postMessage", body=body)

    # --- receiving ----------------------------------------------------------

    @staticmethod
    def parse_message(msg: dict) -> ChannelMessage | None:
        """Converts a Rocket.Chat message dict into a ChannelMessage.

        Returns `None` for messages with an empty `msg` body (system
        messages, joins, etc.). This is a pure function so tests can
        exercise it fully offline (spec section 4.5).
        """
        text = msg.get("msg", "")
        if not text:
            return None
        # The sender lives under the nested `u` (user) object.
        user = msg.get("u", {})
        user_id = user.get("_id", "")
        room_id = msg.get("rid", "")
        return ChannelMessage(
            channel="rocketchat",
            user_id=f"rocketchat:{user_id}",
            target=room_id,
            text=text,
            raw=msg,
        )

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Polls watched rooms for new messages and yields text messages."""
        while self._running:
            for room_id in list(self._watched):
                since = self._watched[room_id]
                params: dict = {"roomId": room_id}
                if since:
                    # Only fetch messages created after the last seen one.
                    params["oldest"] = since
                try:
                    data = await self._call(
                        "GET", "/channels.history", params=params,
                    )
                except (urllib.error.URLError, TimeoutError, OSError,
                        json.JSONDecodeError) as exc:
                    log.warning("history poll failed, retrying: %s", exc)
                    continue

                # `messages` is returned newest-first; reverse for stable
                # oldest-to-newest yield order.
                for msg in reversed(data.get("messages", [])):
                    ts = msg.get("ts")
                    if ts:
                        self._watched[room_id] = ts
                    parsed = self.parse_message(msg)
                    if parsed is not None:
                        yield parsed
            await asyncio.sleep(_POLL_INTERVAL)

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="polling" if self._running else "stopped",
        )
