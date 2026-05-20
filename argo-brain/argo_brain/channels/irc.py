"""IRC channel adapter — spec section 4.5.

IRC is a simple line-based TCP protocol: each message is a single CRLF-
terminated line. This adapter speaks raw IRC over a plain TCP socket using
only the stdlib (`asyncio.open_connection`), so it has no third-party
dependency.

Protocol primer (enough for spec section 4.5):
  * On connect a client registers with `NICK <nick>` and `USER ...`.
  * `JOIN #channel` enters a channel.
  * Messages are `PRIVMSG <target> :<text>` lines.
  * Inbound message lines are prefixed with `:nick!user@host`.
  * The server periodically sends `PING :<token>`; the client must answer
    with `PONG :<token>` or it gets disconnected.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)

log = logging.getLogger("argo_brain.channels.irc")

_CRLF = "\r\n"
_DEFAULT_PORT = 6667


class IRCChannel(Channel):
    """Raw IRC adapter over a plain TCP socket (spec section 4.5)."""

    name = "irc"
    direction = ChannelDirection.BIDIRECTIONAL
    auth = AuthMode.TOKEN

    def __init__(
        self,
        host: str,
        port: int = _DEFAULT_PORT,
        nick: str = "argo",
        channel: str = "#argo",
    ) -> None:
        if not host:
            raise ValueError("IRC host is required")
        if not nick:
            raise ValueError("IRC nick is required")
        if not channel:
            raise ValueError("IRC channel is required")
        self._host = host
        self._port = port
        self._nick = nick
        self._channel = channel
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._running = False

    # --- low-level line I/O -------------------------------------------------

    async def _send_line(self, line: str) -> None:
        """Writes a single CRLF-terminated protocol line."""
        if self._writer is None:
            raise RuntimeError("IRC channel is not connected")
        self._writer.write((line + _CRLF).encode("utf-8", "replace"))
        await self._writer.drain()

    # --- lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """Connects, registers (NICK/USER) and joins the configured channel."""
        self._reader, self._writer = await asyncio.open_connection(
            self._host, self._port
        )
        self._running = True
        # Register with the server, then join the channel.
        await self._send_line(f"NICK {self._nick}")
        await self._send_line(f"USER {self._nick} 0 * :{self._nick}")
        await self._send_line(f"JOIN {self._channel}")
        log.info(
            "IRC channel started: %s:%s as %s in %s",
            self._host, self._port, self._nick, self._channel,
        )

    async def stop(self) -> None:
        """Sends QUIT and closes the TCP connection cleanly."""
        self._running = False
        if self._writer is not None:
            try:
                await self._send_line("QUIT :bye")
            except (OSError, RuntimeError) as exc:
                log.warning("IRC QUIT failed: %s", exc)
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError as exc:
                log.warning("IRC close failed: %s", exc)
        self._reader = None
        self._writer = None

    # --- sending ------------------------------------------------------------

    async def send(self, target: str, text: str) -> None:
        """Sends `PRIVMSG <target> :<text>` to the platform."""
        # IRC lines are single-line; replace any newlines so we never split a
        # message into stray protocol lines.
        clean = (text or "(empty reply)").replace("\r", " ").replace("\n", " ")
        await self._send_line(f"PRIVMSG {target} :{clean}")

    # --- protocol parsing (the test surface) --------------------------------

    @staticmethod
    def parse_line(line: str) -> ChannelMessage | None:
        """Parses a raw IRC line into a `ChannelMessage`.

        Returns a `ChannelMessage` only for `PRIVMSG` lines, e.g.
        `:nick!user@host PRIVMSG #channel :hello there`. Every other line
        (PING, JOIN, server notices, numeric replies, ...) yields `None`.

        The message body is everything after the first ` :` separator, so a
        body that itself contains `:` is preserved intact.
        """
        if line is None:
            return None
        line = line.rstrip("\r\n")
        if not line.startswith(":"):
            # PRIVMSG lines always carry a `:prefix`; without one it cannot
            # be an inbound user message (e.g. a bare `PING`).
            return None
        # Split off the source prefix: ":prefix rest".
        try:
            prefix, rest = line[1:].split(" ", 1)
        except ValueError:
            return None
        # `rest` is "PRIVMSG <target> :<body>"; the body starts at " :".
        try:
            head, body = rest.split(" :", 1)
        except ValueError:
            return None
        head_parts = head.split(" ")
        if len(head_parts) != 2 or head_parts[0].upper() != "PRIVMSG":
            return None
        target = head_parts[1]
        # The prefix is "nick!user@host"; the nick is the part before "!".
        nick = prefix.split("!", 1)[0]
        if not nick:
            return None
        return ChannelMessage(
            channel="irc",
            user_id=f"irc:{nick}",
            target=target,
            text=body,
            raw={"line": line},
        )

    @staticmethod
    def is_ping(line: str) -> bool:
        """Reports whether `line` is a server `PING` keepalive."""
        if line is None:
            return False
        return line.rstrip("\r\n").upper().startswith("PING")

    @staticmethod
    def pong_reply(line: str) -> str:
        """Builds the `PONG` answer matching a server `PING` line.

        `PING :token` must be answered with `PONG :token` so the server
        keeps the connection alive.
        """
        token = line.rstrip("\r\n")[len("PING"):].strip()
        return f"PONG {token}" if token else "PONG"

    # --- receiving ----------------------------------------------------------

    async def receive(self) -> AsyncIterator[ChannelMessage]:
        """Reads protocol lines, answers PINGs and yields user messages."""
        if self._reader is None:
            raise RuntimeError("IRC channel is not connected")
        while self._running:
            raw = await self._reader.readline()
            if not raw:
                # Empty read means the server closed the connection.
                log.warning("IRC connection closed by server")
                self._running = False
                break
            line = raw.decode("utf-8", "replace").rstrip("\r\n")
            if not line:
                continue
            if self.is_ping(line):
                # Keepalive: answer immediately, never surface to the agent.
                await self._send_line(self.pong_reply(line))
                continue
            parsed = self.parse_line(line)
            if parsed is not None:
                yield parsed

    def health(self) -> ChannelHealth:
        return ChannelHealth(
            ok=self._running,
            detail="connected" if self._running else "stopped",
        )
