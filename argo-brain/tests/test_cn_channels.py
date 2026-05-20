"""Offline tests for the Chinese-platform channel adapters — spec section 4.5.

Covers the Feishu/Lark, DingTalk and WeCom (WeChat Work) webhook adapters.
Every test is OFFLINE: no network is touched. Constructors must merely
store configuration; `parse_webhook()` / `verify()` are pure functions.
"""

from __future__ import annotations

import json
import unittest

from argo_brain.channels.base import ChannelHealth, ChannelMessage
from argo_brain.channels.dingtalk import DingTalkChannel
from argo_brain.channels.feishu import FeishuChannel
from argo_brain.channels.wecom import WeComChannel


def _feishu_message_payload() -> dict:
    """A realistic Feishu v2 event-callback for a text message."""
    return {
        "schema": "2.0",
        "header": {"event_type": "im.message.receive_v1"},
        "event": {
            "sender": {
                "sender_id": {"open_id": "ou_abc123", "user_id": "u_42"},
                "sender_type": "user",
            },
            "message": {
                "message_id": "om_xyz",
                "chat_id": "oc_chat789",
                "message_type": "text",
                "content": json.dumps({"text": "hello from feishu"}),
            },
        },
    }


def _dingtalk_message_payload() -> dict:
    """A realistic DingTalk bot text callback."""
    return {
        "msgtype": "text",
        "text": {"content": "  hello from dingtalk "},
        "senderId": "user_dt_99",
        "senderNick": "Akbar",
        "conversationId": "cid_conv321",
        "conversationType": "1",
    }


def _wecom_message_payload() -> dict:
    """A realistic (decrypted) WeCom text callback."""
    return {
        "ToUserName": "wwcorp",
        "FromUserName": "wecom_user_7",
        "CreateTime": "1700000000",
        "MsgType": "text",
        "Content": "  hello from wecom ",
        "MsgId": "1234567890",
        "AgentID": "1000002",
    }


class FeishuChannelTests(unittest.TestCase):
    """Tests for `FeishuChannel`."""

    def test_constructor_stores_config_without_connecting(self) -> None:
        ch = FeishuChannel("t-access-token")
        self.assertEqual(ch.name, "feishu")
        self.assertEqual(ch._token, "t-access-token")

    def test_constructor_rejects_empty_token(self) -> None:
        with self.assertRaises(ValueError):
            FeishuChannel("")

    def test_parse_webhook_extracts_text_message(self) -> None:
        msg = FeishuChannel("tok").parse_webhook(_feishu_message_payload())
        self.assertIsInstance(msg, ChannelMessage)
        assert msg is not None
        self.assertEqual(msg.channel, "feishu")
        self.assertEqual(msg.user_id, "feishu:ou_abc123")
        self.assertEqual(msg.target, "oc_chat789")
        self.assertEqual(msg.text, "hello from feishu")

    def test_parse_webhook_empty_payload_returns_none(self) -> None:
        self.assertIsNone(FeishuChannel("tok").parse_webhook({}))

    def test_parse_webhook_non_message_event_returns_none(self) -> None:
        payload = {"event": {"sender": {}}}  # no message block
        self.assertIsNone(FeishuChannel("tok").parse_webhook(payload))

    def test_parse_webhook_non_text_message_returns_none(self) -> None:
        payload = _feishu_message_payload()
        payload["event"]["message"]["message_type"] = "image"
        self.assertIsNone(FeishuChannel("tok").parse_webhook(payload))

    def test_verify_returns_challenge(self) -> None:
        out = FeishuChannel("tok").verify(
            {"challenge": "chl-9988", "type": "url_verification"}
        )
        self.assertEqual(out, {"challenge": "chl-9988"})

    def test_verify_ignores_non_challenge_payload(self) -> None:
        self.assertIsNone(FeishuChannel("tok").verify(_feishu_message_payload()))

    def test_challenge_payload_is_not_parsed_as_message(self) -> None:
        self.assertIsNone(
            FeishuChannel("tok").parse_webhook({"challenge": "abc"})
        )

    def test_health_ok(self) -> None:
        health = FeishuChannel("tok").health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertTrue(health.ok)


class DingTalkChannelTests(unittest.TestCase):
    """Tests for `DingTalkChannel`."""

    def test_constructor_stores_config_without_connecting(self) -> None:
        ch = DingTalkChannel("https://oapi.dingtalk.com/robot/send?x=1")
        self.assertEqual(ch.name, "dingtalk")
        self.assertEqual(
            ch._webhook_url, "https://oapi.dingtalk.com/robot/send?x=1"
        )

    def test_constructor_rejects_empty_url(self) -> None:
        with self.assertRaises(ValueError):
            DingTalkChannel("")

    def test_parse_webhook_extracts_text_message(self) -> None:
        msg = DingTalkChannel("https://w").parse_webhook(
            _dingtalk_message_payload()
        )
        self.assertIsInstance(msg, ChannelMessage)
        assert msg is not None
        self.assertEqual(msg.channel, "dingtalk")
        self.assertEqual(msg.user_id, "dingtalk:user_dt_99")
        self.assertEqual(msg.target, "cid_conv321")
        self.assertEqual(msg.text, "hello from dingtalk")  # stripped

    def test_parse_webhook_empty_payload_returns_none(self) -> None:
        self.assertIsNone(DingTalkChannel("https://w").parse_webhook({}))

    def test_parse_webhook_non_text_msgtype_returns_none(self) -> None:
        payload = _dingtalk_message_payload()
        payload["msgtype"] = "image"
        self.assertIsNone(DingTalkChannel("https://w").parse_webhook(payload))

    def test_parse_webhook_blank_content_returns_none(self) -> None:
        payload = _dingtalk_message_payload()
        payload["text"] = {"content": "   "}
        self.assertIsNone(DingTalkChannel("https://w").parse_webhook(payload))

    def test_health_ok(self) -> None:
        self.assertTrue(DingTalkChannel("https://w").health().ok)


class WeComChannelTests(unittest.TestCase):
    """Tests for `WeComChannel`."""

    def test_constructor_stores_config_without_connecting(self) -> None:
        ch = WeComChannel("access-tok", "1000002")
        self.assertEqual(ch.name, "wecom")
        self.assertEqual(ch._access_token, "access-tok")
        self.assertEqual(ch._agent_id, "1000002")

    def test_constructor_rejects_empty_token(self) -> None:
        with self.assertRaises(ValueError):
            WeComChannel("", "1000002")

    def test_constructor_rejects_empty_agent_id(self) -> None:
        with self.assertRaises(ValueError):
            WeComChannel("access-tok", "")

    def test_parse_webhook_extracts_text_message(self) -> None:
        msg = WeComChannel("tok", "1000002").parse_webhook(
            _wecom_message_payload()
        )
        self.assertIsInstance(msg, ChannelMessage)
        assert msg is not None
        self.assertEqual(msg.channel, "wecom")
        self.assertEqual(msg.user_id, "wecom:wecom_user_7")
        self.assertEqual(msg.target, "wecom_user_7")
        self.assertEqual(msg.text, "hello from wecom")  # stripped

    def test_parse_webhook_empty_payload_returns_none(self) -> None:
        self.assertIsNone(WeComChannel("tok", "1").parse_webhook({}))

    def test_parse_webhook_non_text_msgtype_returns_none(self) -> None:
        payload = _wecom_message_payload()
        payload["MsgType"] = "event"
        self.assertIsNone(WeComChannel("tok", "1").parse_webhook(payload))

    def test_parse_webhook_blank_content_returns_none(self) -> None:
        payload = _wecom_message_payload()
        payload["Content"] = "  "
        self.assertIsNone(WeComChannel("tok", "1").parse_webhook(payload))

    def test_health_ok(self) -> None:
        self.assertTrue(WeComChannel("tok", "1").health().ok)


if __name__ == "__main__":
    unittest.main()
