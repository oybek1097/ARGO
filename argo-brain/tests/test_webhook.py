"""Webhook channel adapter tests (offline — no network calls)."""

import unittest

from argo_brain.channels import GenericWebhookChannel, SlackChannel
from argo_brain.channels.base import ChannelMessage


class TestGenericWebhookChannel(unittest.TestCase):
    def setUp(self):
        self.ch = GenericWebhookChannel()

    def test_parse_message_key(self):
        msg = self.ch.parse_webhook(
            {"user_id": "u7", "message": "salom", "reply_url": "http://x/cb"}
        )
        self.assertIsInstance(msg, ChannelMessage)
        self.assertEqual(msg.user_id, "generic:u7")
        self.assertEqual(msg.text, "salom")
        self.assertEqual(msg.target, "http://x/cb")

    def test_parse_text_key(self):
        msg = self.ch.parse_webhook({"text": "hi"})
        self.assertEqual(msg.text, "hi")
        self.assertEqual(msg.user_id, "generic:webhook-user")

    def test_empty_payload_ignored(self):
        self.assertIsNone(self.ch.parse_webhook({}))

    def test_no_verification_step(self):
        self.assertIsNone(self.ch.verify({"anything": 1}))


class TestSlackChannel(unittest.TestCase):
    def setUp(self):
        self.ch = SlackChannel("xoxb-test-token")

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            SlackChannel("")

    def test_url_verification_handshake(self):
        result = self.ch.verify(
            {"type": "url_verification", "challenge": "abc123"}
        )
        self.assertEqual(result, {"challenge": "abc123"})

    def test_no_handshake_for_normal_event(self):
        self.assertIsNone(self.ch.verify({"type": "event_callback"}))

    def test_parse_message_event(self):
        msg = self.ch.parse_webhook(
            {"event": {"type": "message", "user": "U1",
                       "channel": "C9", "text": "hello argo"}}
        )
        self.assertEqual(msg.user_id, "slack:U1")
        self.assertEqual(msg.target, "C9")
        self.assertEqual(msg.text, "hello argo")

    def test_ignores_bot_message(self):
        msg = self.ch.parse_webhook(
            {"event": {"type": "message", "bot_id": "B1", "text": "loop"}}
        )
        self.assertIsNone(msg)

    def test_ignores_subtype_message(self):
        msg = self.ch.parse_webhook(
            {"event": {"type": "message", "subtype": "channel_join",
                       "text": "joined"}}
        )
        self.assertIsNone(msg)

    def test_ignores_non_message_event(self):
        self.assertIsNone(
            self.ch.parse_webhook({"event": {"type": "reaction_added"}})
        )


if __name__ == "__main__":
    unittest.main()
