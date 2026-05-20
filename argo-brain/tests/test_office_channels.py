"""Offline tests for the office-suite webhook channels — spec section 4.5.

Covers `GoogleChatChannel` and `TeamsChannel`. Every test is fully
offline: `parse_webhook` is a pure function exercised with sample dicts,
and constructors are checked to store config without opening any
connection. No network I/O happens here.
"""

import unittest

from argo_brain.channels.base import ChannelHealth, ChannelMessage
from argo_brain.channels.google_chat import GoogleChatChannel
from argo_brain.channels.teams import TeamsChannel


# A realistic Google Chat MESSAGE event payload.
GCHAT_MESSAGE = {
    "type": "MESSAGE",
    "message": {"text": "hello from google chat"},
    "user": {"name": "users/12345", "displayName": "Akbar"},
    "space": {"name": "spaces/AAAA1111"},
}

# A realistic Bot Framework "message" activity payload.
TEAMS_MESSAGE = {
    "type": "message",
    "text": "hello from teams",
    "from": {"id": "29:abcdef"},
    "conversation": {"id": "19:meeting_xyz@thread.v2"},
    "serviceUrl": "https://smba.trafficmanager.net/amer",
}


class TestGoogleChatParseWebhook(unittest.TestCase):
    """Exercises GoogleChatChannel.parse_webhook offline."""

    def setUp(self):
        self.ch = GoogleChatChannel("https://chat.googleapis.com/v1/spaces/x")

    def test_parse_returns_channel_message(self):
        msg = self.ch.parse_webhook(GCHAT_MESSAGE)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_user_id_prefix(self):
        msg = self.ch.parse_webhook(GCHAT_MESSAGE)
        self.assertEqual(msg.user_id, "google_chat:users/12345")

    def test_parse_target_is_space_name(self):
        msg = self.ch.parse_webhook(GCHAT_MESSAGE)
        self.assertEqual(msg.target, "spaces/AAAA1111")

    def test_parse_text_and_channel(self):
        msg = self.ch.parse_webhook(GCHAT_MESSAGE)
        self.assertEqual(msg.text, "hello from google chat")
        self.assertEqual(msg.channel, "google_chat")

    def test_parse_non_message_event_returns_none(self):
        added = {"type": "ADDED_TO_SPACE", "space": {"name": "spaces/x"}}
        self.assertIsNone(self.ch.parse_webhook(added))

    def test_parse_empty_payload_returns_none(self):
        self.assertIsNone(self.ch.parse_webhook({}))

    def test_parse_message_without_text_returns_none(self):
        payload = {"type": "MESSAGE", "message": {}, "user": {"name": "u/1"}}
        self.assertIsNone(self.ch.parse_webhook(payload))


class TestGoogleChatChannelConfig(unittest.TestCase):
    """Constructor / health checks for GoogleChatChannel (no I/O)."""

    def test_constructor_stores_webhook_url(self):
        url = "https://chat.googleapis.com/v1/spaces/AAAA"
        ch = GoogleChatChannel(url)
        self.assertEqual(ch._webhook_url, url)
        self.assertEqual(ch.name, "google_chat")

    def test_constructor_rejects_empty_url(self):
        with self.assertRaises(ValueError):
            GoogleChatChannel("")

    def test_health_ok(self):
        ch = GoogleChatChannel("https://chat.googleapis.com/v1/spaces/x")
        health = ch.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertTrue(health.ok)


class TestTeamsParseWebhook(unittest.TestCase):
    """Exercises TeamsChannel.parse_webhook offline."""

    def setUp(self):
        self.ch = TeamsChannel(app_id="app", app_password="pw")

    def test_parse_returns_channel_message(self):
        msg = self.ch.parse_webhook(TEAMS_MESSAGE)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_user_id_prefix(self):
        msg = self.ch.parse_webhook(TEAMS_MESSAGE)
        self.assertEqual(msg.user_id, "teams:29:abcdef")

    def test_parse_target_is_conversation_id(self):
        msg = self.ch.parse_webhook(TEAMS_MESSAGE)
        self.assertEqual(msg.target, "19:meeting_xyz@thread.v2")

    def test_parse_text_and_channel(self):
        msg = self.ch.parse_webhook(TEAMS_MESSAGE)
        self.assertEqual(msg.text, "hello from teams")
        self.assertEqual(msg.channel, "teams")

    def test_parse_non_message_activity_returns_none(self):
        typing = {"type": "typing", "from": {"id": "29:x"}}
        self.assertIsNone(self.ch.parse_webhook(typing))

    def test_parse_empty_payload_returns_none(self):
        self.assertIsNone(self.ch.parse_webhook({}))

    def test_parse_message_without_text_returns_none(self):
        payload = {"type": "message", "from": {"id": "29:x"},
                   "conversation": {"id": "19:y"}}
        self.assertIsNone(self.ch.parse_webhook(payload))


class TestTeamsChannelConfig(unittest.TestCase):
    """Constructor / health checks for TeamsChannel (no I/O)."""

    def test_constructor_stores_credentials(self):
        ch = TeamsChannel(app_id="my-app", app_password="secret")
        self.assertEqual(ch._app_id, "my-app")
        self.assertEqual(ch._app_password, "secret")
        self.assertEqual(ch.name, "teams")

    def test_constructor_allows_empty_credentials(self):
        ch = TeamsChannel()
        self.assertEqual(ch._app_id, "")

    def test_health_ok(self):
        ch = TeamsChannel(app_id="a", app_password="p")
        health = ch.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertTrue(health.ok)


if __name__ == "__main__":
    unittest.main()
