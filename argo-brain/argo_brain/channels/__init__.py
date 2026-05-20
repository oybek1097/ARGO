"""Channel adapters — spec section 4.5.

The skeleton ships the base interface, the Telegram adapter (long polling),
the Email adapter (IMAP/SMTP), webhook-based adapters (generic + Slack) and a
runner that bridges a polling channel to the agent. The remaining 26+
platforms (Discord, WhatsApp, ...) follow the same `Channel` contract in
Sprints 6-7.
"""

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)
from argo_brain.channels.email_channel import EmailChannel
from argo_brain.channels.runner import run_channel
from argo_brain.channels.telegram import TelegramChannel
from argo_brain.channels.webhook import (
    GenericWebhookChannel,
    SlackChannel,
    WebhookChannel,
)

__all__ = [
    "AuthMode",
    "Channel",
    "ChannelDirection",
    "ChannelHealth",
    "ChannelMessage",
    "EmailChannel",
    "GenericWebhookChannel",
    "SlackChannel",
    "TelegramChannel",
    "WebhookChannel",
    "run_channel",
]
