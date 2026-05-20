"""Matrix channel adapter — spec section 4.5.

Uses the Matrix client-server REST API. Dependency-free: HTTP is done with
the stdlib `urllib`, moved to a worker thread so the async interface holds.

The Matrix `/sync` endpoint is HTTP long-polling (the server holds the
request open until events arrive or the timeout elapses), so no WebSocket
is required. Outbound messages use `PUT /rooms/{room}/send/m.room.message`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
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

log = logging.getLogger("argo_brain.channels.matrix")

# Matrix client-server API prefix (spec section 4.5).
_API_PREFIX = "/_matrix/client/v3"
# How long (ms) the server holds a /sync request open while waiting.
_SYNC_TIMEOUT_MS = 30000


class MatrixChannel(Channel):
    """Matrix client-server API adapter (/sync long-polling)."""

    name = "matrix"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(self, homeserver: str, access_token: str,
                 user_id: str) -> None:
        if not homeserver:
            raise ValueError("Matrix homeserver URL is required")
        if not access_token:
            raise ValueError("Matrix access token is required")
        if not user_id:
            raise ValueError("Matrix user_id is required")
        # Normalize: strip a trailing slash so URL joining is predictable.
        self._homeserver = homeserver.rstrip("/")
        self._access_token = access_token
        self._user_id = user_id
        self._base = f"{self._homeserver}{_API_PREFIX}"
        # Opaque token marking our position in the event stream.
        self._since: str | None = None
        self._running = False
        # Monotonic counter for the per-request transaction id (de-dup key).
        self._txn = 0

    # --- HTTP plumbing ------------------------------------------------------

    def _request(self, method: str, path: str, params: dict | None = None,
                 body: dict | None = None, timeout: float = 45.0) -> dict:
        """Blocking client-server API call (runs in a worker thread)."""
        url = f"{self._base}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._access_token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    async def _call(self, method: str, path: str, params: dict | None = None,
                    body: dict | None = None, timeout: float = 45.0) -> dict:
        return await asyncio.to_thread(
            self._request, method, path, params, body, timeout
        )

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        self._running = True
        # whoami confirms the access token is valid before we long-poll.
        who = await self._call("GET", "/account/whoami")
        log.info("Matrix channel started as %s", who.get("user_id", "?"))

    async def stop(self) -> None:
        self._running = False

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        """Sends a text message to a room via PUT .../send/m.room.message."""
        self._txn += 1
        # Transaction ids must be unique per request to make sends idempotent.
        txn_id = f"argo{int(time.time() * 1000)}-{self._txn}"
        room = urllib.parse.quote(target, safe="")
        path = f"/rooms/{room}/send/m.room.message/{txn_id}"
        body = {"msgtype": "m.text", "body": text or "(empty reply)"}
        await self._call("PUT", path, body=body)

    # --- receiving ----------------------------------------------------------

    @staticmethod
    def parse_sync(sync_response: dict) -> list[ChannelMessage]:
        """Extracts all text message events from a Matrix /sync response.

        Walks `rooms.join.<room_id>.timeline.events` across every joined
        room, keeping only `m.room.message` events whose `msgtype` is
        `m.text`. Non-text events (membership changes, images, reactions,
        ...) are ignored. This is a pure function so tests can exercise it
        fully offline (spec section 4.5).
        """
        messages: list[ChannelMessage] = []
        rooms = sync_response.get("rooms", {})
        joined = rooms.get("join", {})
        for room_id, room_data in joined.items():
            timeline = room_data.get("timeline", {})
            for event in timeline.get("events", []):
                if event.get("type") != "m.room.message":
                    continue
                content = event.get("content", {})
                if content.get("msgtype") != "m.text":
                    continue
                body = content.get("body")
                if not body:
                    continue
                sender = event.get("sender")
                if not sender:
                    continue
                messages.append(
                    ChannelMessage(
                        channel="matrix",
                        user_id=f"matrix:{sender}",
                        target=room_id,
                        text=body,
                        raw=event,
                    )
                )
        return messages

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Long-polls Matrix /sync and yields inbound text messages."""
        while self._running:
            params = {"timeout": _SYNC_TIMEOUT_MS}
            if self._since is not None:
                params["since"] = self._since
            try:
                # Read timeout must outlast the server-side long-poll window.
                data = await self._call(
                    "GET", "/sync", params=params,
                    timeout=_SYNC_TIMEOUT_MS / 1000 + 15,
                )
            except (urllib.error.URLError, TimeoutError, OSError,
                    json.JSONDecodeError) as exc:
                log.warning("/sync failed, retrying: %s", exc)
                await asyncio.sleep(3)
                continue

            # Advance the stream position so the next /sync is incremental.
            self._since = data.get("next_batch", self._since)
            for parsed in self.parse_sync(data):
                yield parsed

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="syncing" if self._running else "stopped",
        )
