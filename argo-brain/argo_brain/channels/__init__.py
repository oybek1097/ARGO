"""Channel adapters — spec section 4.5.

The skeleton ships the base interface, the Telegram adapter and a runner that
bridges a channel to the agent. The remaining 29+ platforms (Discord, Slack,
WhatsApp, ...) follow the same `Channel` contract in Sprints 6-7.
"""

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)
from argo_brain.channels.runner import run_channel
from argo_brain.channels.telegram import TelegramChannel

__all__ = [
    "AuthMode",
    "Channel",
    "ChannelDirection",
    "ChannelHealth",
    "ChannelMessage",
    "TelegramChannel",
    "run_channel",
]
