"""Channel adapters — spec section 4.5.

The skeleton ships the base interface, the Telegram adapter (long polling),
the Email adapter (IMAP/SMTP), the IRC adapter (TCP), webhook-based adapters
(generic + Slack) and a runner that bridges a polling channel to the agent.
The remaining 25+ platforms follow the same `Channel` contract.
"""

from argo_brain.channels.base import (
    AuthMode,
    Channel,
    ChannelDirection,
    ChannelHealth,
    ChannelMessage,
)
from argo_brain.channels.discord import DiscordChannel
from argo_brain.channels.email_channel import EmailChannel
from argo_brain.channels.google_chat import GoogleChatChannel
from argo_brain.channels.irc import IRCChannel
from argo_brain.channels.line import LINEChannel
from argo_brain.channels.matrix import MatrixChannel
from argo_brain.channels.mattermost import MattermostChannel
from argo_brain.channels.rocketchat import RocketChatChannel
from argo_brain.channels.runner import run_channel
from argo_brain.channels.sms_twilio import TwilioSMSChannel
from argo_brain.channels.teams import TeamsChannel
from argo_brain.channels.viber import ViberChannel
from argo_brain.channels.whatsapp import WhatsAppChannel
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
    "DiscordChannel",
    "EmailChannel",
    "GenericWebhookChannel",
    "GoogleChatChannel",
    "IRCChannel",
    "LINEChannel",
    "MatrixChannel",
    "MattermostChannel",
    "RocketChatChannel",
    "SlackChannel",
    "TeamsChannel",
    "TelegramChannel",
    "TwilioSMSChannel",
    "ViberChannel",
    "WebhookChannel",
    "WhatsAppChannel",
    "run_channel",
]
