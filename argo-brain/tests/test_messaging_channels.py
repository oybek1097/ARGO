"""Offline tests for the webhook messaging channels — spec section 4.5.

Covers `LINEChannel`, `ViberChannel`, `WhatsAppChannel` and
`TwilioSMSChannel`. All tests are fully offline: `parse_webhook` and
`verify` are exercised with realistic sample payloads, and each
constructor is checked to store config without opening a connection.
"""

import unittest

from argo_brain.channels.base import ChannelMessage
from argo_brain.channels.line import LINEChannel
from argo_brain.channels.sms_twilio import TwilioSMSChannel
from argo_brain.channels.viber import ViberChannel
from argo_brain.channels.whatsapp import WhatsAppChannel


class TestLINEChannel(unittest.TestCase):
    """Exercises LINEChannel.parse_webhook and construction."""

    SAMPLE = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-tok-123",
                "source": {"type": "user", "userId": "Uabcdef"},
                "message": {"type": "text", "text": "hello line"},
            }
        ]
    }

    def test_parse_webhook_returns_channel_message(self):
        ch = LINEChannel("tok")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_webhook_user_id_prefix(self):
        ch = LINEChannel("tok")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.user_id, "line:Uabcdef")

    def test_parse_webhook_target_is_reply_token(self):
        ch = LINEChannel("tok")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.target, "reply-tok-123")
        self.assertEqual(msg.text, "hello line")
        self.assertEqual(msg.channel, "line")

    def test_parse_webhook_empty_payload_returns_none(self):
        ch = LINEChannel("tok")
        self.assertIsNone(ch.parse_webhook({}))

    def test_parse_webhook_non_text_event_returns_none(self):
        ch = LINEChannel("tok")
        payload = {"events": [{"type": "message", "replyToken": "r",
                               "source": {"userId": "U1"},
                               "message": {"type": "sticker"}}]}
        self.assertIsNone(ch.parse_webhook(payload))

    def test_construction_stores_token_without_connecting(self):
        ch = LINEChannel("my-line-token")
        self.assertEqual(ch._token, "my-line-token")
        self.assertEqual(ch.name, "line")
        self.assertFalse(ch._running)

    def test_construction_requires_token(self):
        with self.assertRaises(ValueError):
            LINEChannel("")


class TestViberChannel(unittest.TestCase):
    """Exercises ViberChannel.parse_webhook and construction."""

    SAMPLE = {
        "event": "message",
        "timestamp": 1700000000000,
        "sender": {"id": "01234567890A=", "name": "Alice"},
        "message": {"type": "text", "text": "hello viber"},
    }

    def test_parse_webhook_returns_channel_message(self):
        ch = ViberChannel("tok")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_webhook_user_id_prefix(self):
        ch = ViberChannel("tok")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.user_id, "viber:01234567890A=")

    def test_parse_webhook_target_and_text(self):
        ch = ViberChannel("tok")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.target, "01234567890A=")
        self.assertEqual(msg.text, "hello viber")
        self.assertEqual(msg.channel, "viber")

    def test_parse_webhook_empty_payload_returns_none(self):
        ch = ViberChannel("tok")
        self.assertIsNone(ch.parse_webhook({}))

    def test_parse_webhook_non_message_event_returns_none(self):
        ch = ViberChannel("tok")
        payload = {"event": "delivered", "message_token": 1}
        self.assertIsNone(ch.parse_webhook(payload))

    def test_construction_stores_token_without_connecting(self):
        ch = ViberChannel("viber-token", "MyBot")
        self.assertEqual(ch._token, "viber-token")
        self.assertEqual(ch._sender_name, "MyBot")
        self.assertEqual(ch.name, "viber")
        self.assertFalse(ch._running)

    def test_construction_requires_token(self):
        with self.assertRaises(ValueError):
            ViberChannel("")


class TestWhatsAppChannel(unittest.TestCase):
    """Exercises WhatsAppChannel.parse_webhook, verify and construction."""

    SAMPLE = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA-ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": "15557654321",
                                    "id": "wamid.XYZ",
                                    "type": "text",
                                    "text": {"body": "hello whatsapp"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    def test_parse_webhook_returns_channel_message(self):
        ch = WhatsAppChannel("tok", "pnid")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_webhook_user_id_prefix(self):
        ch = WhatsAppChannel("tok", "pnid")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.user_id, "whatsapp:15557654321")

    def test_parse_webhook_target_and_text(self):
        ch = WhatsAppChannel("tok", "pnid")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.target, "15557654321")
        self.assertEqual(msg.text, "hello whatsapp")
        self.assertEqual(msg.channel, "whatsapp")

    def test_parse_webhook_empty_payload_returns_none(self):
        ch = WhatsAppChannel("tok", "pnid")
        self.assertIsNone(ch.parse_webhook({}))

    def test_parse_webhook_status_callback_returns_none(self):
        ch = WhatsAppChannel("tok", "pnid")
        payload = {"entry": [{"changes": [{"value": {
            "statuses": [{"status": "delivered"}]}}]}]}
        self.assertIsNone(ch.parse_webhook(payload))

    def test_verify_echoes_challenge(self):
        ch = WhatsAppChannel("tok", "pnid", "secret")
        result = ch.verify({
            "hub.mode": "subscribe",
            "hub.verify_token": "secret",
            "hub.challenge": "challenge-99",
        })
        self.assertEqual(result, {"hub.challenge": "challenge-99"})

    def test_verify_rejects_bad_token(self):
        ch = WhatsAppChannel("tok", "pnid", "secret")
        result = ch.verify({
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong",
            "hub.challenge": "challenge-99",
        })
        self.assertIsNone(result)

    def test_verify_ignores_unrelated_payload(self):
        ch = WhatsAppChannel("tok", "pnid", "secret")
        self.assertIsNone(ch.verify({"hello": "world"}))

    def test_construction_stores_config_without_connecting(self):
        ch = WhatsAppChannel("wa-token", "phone-123", "vtok")
        self.assertEqual(ch._token, "wa-token")
        self.assertEqual(ch._phone_number_id, "phone-123")
        self.assertEqual(ch._verify_token, "vtok")
        self.assertIn("phone-123/messages", ch._endpoint)
        self.assertEqual(ch.name, "whatsapp")
        self.assertFalse(ch._running)

    def test_construction_requires_token(self):
        with self.assertRaises(ValueError):
            WhatsAppChannel("", "pnid")

    def test_construction_requires_phone_number_id(self):
        with self.assertRaises(ValueError):
            WhatsAppChannel("tok", "")


class TestTwilioSMSChannel(unittest.TestCase):
    """Exercises TwilioSMSChannel.parse_webhook and construction."""

    SAMPLE = {
        "MessageSid": "SM0123456789",
        "From": "+15557654321",
        "To": "+15551234567",
        "Body": "hello sms",
        "NumMedia": "0",
    }

    def test_parse_webhook_returns_channel_message(self):
        ch = TwilioSMSChannel("AC123", "tok", "+15551234567")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_webhook_user_id_prefix(self):
        ch = TwilioSMSChannel("AC123", "tok", "+15551234567")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.user_id, "sms:+15557654321")

    def test_parse_webhook_target_and_text(self):
        ch = TwilioSMSChannel("AC123", "tok", "+15551234567")
        msg = ch.parse_webhook(self.SAMPLE)
        self.assertEqual(msg.target, "+15557654321")
        self.assertEqual(msg.text, "hello sms")
        self.assertEqual(msg.channel, "sms")

    def test_parse_webhook_empty_payload_returns_none(self):
        ch = TwilioSMSChannel("AC123", "tok", "+15551234567")
        self.assertIsNone(ch.parse_webhook({}))

    def test_parse_webhook_status_callback_returns_none(self):
        ch = TwilioSMSChannel("AC123", "tok", "+15551234567")
        # A delivery status callback carries no Body field.
        payload = {"MessageSid": "SM1", "MessageStatus": "delivered"}
        self.assertIsNone(ch.parse_webhook(payload))

    def test_construction_stores_config_without_connecting(self):
        ch = TwilioSMSChannel("AC999", "auth-tok", "+15550001111")
        self.assertEqual(ch._account_sid, "AC999")
        self.assertEqual(ch._auth_token, "auth-tok")
        self.assertEqual(ch._from_number, "+15550001111")
        self.assertIn("AC999/Messages.json", ch._endpoint)
        self.assertEqual(ch.name, "sms")
        self.assertFalse(ch._running)

    def test_construction_requires_account_sid(self):
        with self.assertRaises(ValueError):
            TwilioSMSChannel("", "tok", "+15551234567")

    def test_construction_requires_auth_token(self):
        with self.assertRaises(ValueError):
            TwilioSMSChannel("AC123", "", "+15551234567")

    def test_construction_requires_from_number(self):
        with self.assertRaises(ValueError):
            TwilioSMSChannel("AC123", "tok", "")


if __name__ == "__main__":
    unittest.main()
