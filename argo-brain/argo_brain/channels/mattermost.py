"""Mattermost channel adapter — spec section 4.5.

Uses the Mattermost REST API (v4). Dependency-free: HTTP is done with the
stdlib `urllib`, moved to a worker thread so the async `Channel` interface
holds.

Mattermost has no long-poll endpoint comparable to Matrix `/sync`, so
inbound messages are gathered by polling `GET /api/v4/posts` for the
channels the bot watches. Outbound messages use `POST /api/v4/posts`.
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

log = logging.getLogger("argo_brain.channels.mattermost")

# Mattermost REST API prefix (spec section 4.5).
_API_PREFIX = "/api/v4"
# Seconds between inbound polling passes.
_POLL_INTERVAL = 5.0


class MattermostChannel(Channel):
    """Mattermost REST API adapter (poll-based receive)."""

    name = "mattermost"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(self, server_url: str, token: str,
                 team_id: str = "") -> None:
        if not server_url:
            raise ValueError("Mattermost server_url is required")
        if not token:
            raise ValueError("Mattermost token is required")
        # Normalize: strip a trailing slash so URL joining is predictable.
        self._server_url = server_url.rstrip("/")
        self._token = token
        self._team_id = team_id
        self._base = f"{self._server_url}{_API_PREFIX}"
        self._running = False
        # Channels to poll for inbound posts, plus the last seen post time
        # (epoch ms) per channel so each poll is incremental.
        self._watched: dict[str, int] = {}

    # --- HTTP plumbing ------------------------------------------------------

    def _request(self, method: str, path: str, params: dict | None = None,
                 body: dict | None = None, timeout: float = 30.0) -> dict:
        """Blocking REST API call (runs in a worker thread)."""
        url = f"{self._base}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
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
        # /users/me confirms the access token is valid before polling.
        me = await self._call("GET", "/users/me")
        log.info("Mattermost channel started as %s",
                 me.get("username", "?"))

    async def stop(self) -> None:
        self._running = False

    def watch(self, channel_id: str) -> None:
        """Registers a Mattermost channel id for inbound polling."""
        self._watched.setdefault(channel_id, 0)

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        """Sends a text message to a channel via POST /api/v4/posts."""
        body = {"channel_id": target, "message": text or "(empty reply)"}
        await self._call("POST", "/posts", body=body)

    # --- receiving ----------------------------------------------------------

    @staticmethod
    def parse_post(post: dict) -> ChannelMessage | None:
        """Converts a Mattermost post dict into a ChannelMessage.

        Returns `None` for posts with an empty `message` (system posts,
        joins, etc.). This is a pure function so tests can exercise it
        fully offline (spec section 4.5).
        """
        message = post.get("message", "")
        if not message:
            return None
        user_id = post.get("user_id", "")
        channel_id = post.get("channel_id", "")
        return ChannelMessage(
            channel="mattermost",
            user_id=f"mattermost:{user_id}",
            target=channel_id,
            text=message,
            raw=post,
        )

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Polls watched channels for new posts and yields text messages."""
        while self._running:
            for channel_id in list(self._watched):
                since = self._watched[channel_id]
                params: dict = {}
                if since:
                    # Only fetch posts created after the last seen one.
                    params["since"] = since
                try:
                    data = await self._call(
                        "GET", f"/channels/{channel_id}/posts",
                        params=params,
                    )
                except (urllib.error.URLError, TimeoutError, OSError,
                        json.JSONDecodeError) as exc:
                    log.warning("post poll failed, retrying: %s", exc)
                    continue

                posts = data.get("posts", {})
                # `order` lists post ids oldest-to-newest for stable yield.
                order = data.get("order", list(posts))
                for post_id in order:
                    post = posts.get(post_id, {})
                    create_at = post.get("create_at", 0)
                    if create_at > self._watched[channel_id]:
                        self._watched[channel_id] = create_at
                    parsed = self.parse_post(post)
                    if parsed is not None:
                        yield parsed
            await asyncio.sleep(_POLL_INTERVAL)

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="polling" if self._running else "stopped",
        )
