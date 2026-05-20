"""Channel adapter base interface — spec section 4.5.

Every messaging platform implements `Channel`. The agent stays platform-
agnostic: it only ever sees a `ChannelMessage` in and a string out.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum


class ChannelDirection(str, Enum):
    """Whether a channel can receive, send, or both."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"
    BIDIRECTIONAL = "bidirectional"


class AuthMode(str, Enum):
    """How a channel authenticates with its platform."""

    TOKEN = "token"
    OAUTH = "oauth"
    WEBHOOK_SECRET = "webhook_secret"


@dataclass
class ChannelMessage:
    """A normalized inbound message from any platform."""

    channel: str          # e.g. "telegram"
    user_id: str          # namespaced, e.g. "telegram:12345"
    target: str           # where a reply must be sent (e.g. chat id)
    text: str
    raw: dict = field(default_factory=dict)


@dataclass
class ChannelHealth:
    """Health snapshot of a channel."""

    ok: bool
    detail: str = ""


class Channel(ABC):
    """Base class for all messaging-platform adapters."""

    name: str = "unnamed"
    direction: ChannelDirection = ChannelDirection.BIDIRECTIONAL
    auth: AuthMode = AuthMode.TOKEN

    @abstractmethod
    async def start(self) -> None:
        """Prepares the channel for receiving/sending."""

    @abstractmethod
    async def stop(self) -> None:
        """Stops the channel cleanly."""

    @abstractmethod
    async def send(self, target: str, text: str) -> None:
        """Sends a text message to `target` on the platform."""

    @abstractmethod
    def receive(self) -> AsyncIterator[ChannelMessage]:
        """Yields inbound messages as an async iterator."""

    def health(self) -> ChannelHealth:
        """Reports channel health (overridable)."""
        return ChannelHealth(ok=True)
