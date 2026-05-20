"""Offline tests for the REST-based channel adapters — spec section 4.5.

Covers `MattermostChannel` and `RocketChatChannel`. All tests are fully
offline: pure-function parsers are exercised with sample dicts, and the
constructors are checked to store config without opening any connection.
"""

import unittest

from argo_brain.channels.base import ChannelHealth, ChannelMessage
from argo_brain.channels.mattermost import MattermostChannel
from argo_brain.channels.rocketchat import RocketChatChannel


class TestMattermostParsePost(unittest.TestCase):
    """Exercises the static MattermostChannel.parse_post parser."""

    def test_parse_post_returns_channel_message(self):
        post = {"user_id": "u123", "channel_id": "c456",
                "message": "hello world"}
        msg = MattermostChannel.parse_post(post)
        self.assertIsInstance(msg, ChannelMessage)

    def test_parse_post_user_id_prefix(self):
        post = {"user_id": "u123", "channel_id": "c456", "message": "hi"}
        msg = MattermostChannel.parse_post(post)
        self.assertEqual(msg.user_id, "mattermost:u123")

    def test_parse_post_target_is_channel_id(self):
        post = {"user_id": "u123", "channel_id": "c456", "message": "hi"}
        msg = MattermostChannel.parse_post(post)
        self.assertEqual(msg.target, "c456")

    def test_parse_post_text_is_message(self):
        post = {"user_id": "u123", "channel_id": "c456", "message": "ping"}
        msg = MattermostChannel.parse_post(post)
        self.assertEqual(msg.text, "ping")
        self.assertEqual(msg.channel, "mattermost")

    def test_parse_post_empty_message_returns_none(self):
        post = {"user_id": "u123", "channel_id": "c456", "message": ""}
        self.assertIsNone(MattermostChannel.parse_post(post))

    def test_parse_post_missing_message_returns_none(self):
        post = {"user_id": "u123", "channel_id": "c456"}
        self.assertIsNone(MattermostChannel.parse_post(post))

    def test_parse_post_keeps_raw(self):
        post = {"user_id": "u123", "channel_id": "c456", "message": "x"}
        msg = MattermostChannel.parse_post(post)
        self.assertEqual(msg.raw, post)


class TestRocketChatParseMessage(unittest.TestCase):
    """Exercises the static RocketChatChannel.parse_message parser."""

    def test_parse_message_returns_channel_message(self):
        msg = {"rid": "room1", "msg": "hello", "u": {"_id": "user1"}}
        result = RocketChatChannel.parse_message(msg)
        self.assertIsInstance(result, ChannelMessage)

    def test_parse_message_user_id_prefix(self):
        msg = {"rid": "room1", "msg": "hello", "u": {"_id": "user1"}}
        result = RocketChatChannel.parse_message(msg)
        self.assertEqual(result.user_id, "rocketchat:user1")

    def test_parse_message_target_is_room_id(self):
        msg = {"rid": "room1", "msg": "hello", "u": {"_id": "user1"}}
        result = RocketChatChannel.parse_message(msg)
        self.assertEqual(result.target, "room1")

    def test_parse_message_text_is_msg(self):
        msg = {"rid": "room1", "msg": "pong", "u": {"_id": "user1"}}
        result = RocketChatChannel.parse_message(msg)
        self.assertEqual(result.text, "pong")
        self.assertEqual(result.channel, "rocketchat")

    def test_parse_message_empty_msg_returns_none(self):
        msg = {"rid": "room1", "msg": "", "u": {"_id": "user1"}}
        self.assertIsNone(RocketChatChannel.parse_message(msg))

    def test_parse_message_missing_msg_returns_none(self):
        msg = {"rid": "room1", "u": {"_id": "user1"}}
        self.assertIsNone(RocketChatChannel.parse_message(msg))

    def test_parse_message_keeps_raw(self):
        msg = {"rid": "room1", "msg": "x", "u": {"_id": "user1"}}
        result = RocketChatChannel.parse_message(msg)
        self.assertEqual(result.raw, msg)


class TestMattermostConstruction(unittest.TestCase):
    """Constructing a MattermostChannel stores config without connecting."""

    def test_stores_config(self):
        ch = MattermostChannel("https://mm.example.com/", "tok", "team1")
        # Trailing slash is normalized away.
        self.assertEqual(ch._server_url, "https://mm.example.com")
        self.assertEqual(ch._token, "tok")
        self.assertEqual(ch._team_id, "team1")

    def test_not_running_before_start(self):
        ch = MattermostChannel("https://mm.example.com", "tok")
        self.assertFalse(ch._running)

    def test_requires_server_url(self):
        with self.assertRaises(ValueError):
            MattermostChannel("", "tok")

    def test_requires_token(self):
        with self.assertRaises(ValueError):
            MattermostChannel("https://mm.example.com", "")

    def test_health_reports_stopped(self):
        ch = MattermostChannel("https://mm.example.com", "tok")
        health = ch.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertFalse(health.ok)
        self.assertEqual(health.detail, "stopped")

    def test_name_is_mattermost(self):
        ch = MattermostChannel("https://mm.example.com", "tok")
        self.assertEqual(ch.name, "mattermost")


class TestRocketChatConstruction(unittest.TestCase):
    """Constructing a RocketChatChannel stores config without connecting."""

    def test_stores_config(self):
        ch = RocketChatChannel("https://rc.example.com/", "uid", "atok")
        # Trailing slash is normalized away.
        self.assertEqual(ch._server_url, "https://rc.example.com")
        self.assertEqual(ch._user_id, "uid")
        self.assertEqual(ch._auth_token, "atok")

    def test_not_running_before_start(self):
        ch = RocketChatChannel("https://rc.example.com", "uid", "atok")
        self.assertFalse(ch._running)

    def test_requires_server_url(self):
        with self.assertRaises(ValueError):
            RocketChatChannel("", "uid", "atok")

    def test_requires_user_id(self):
        with self.assertRaises(ValueError):
            RocketChatChannel("https://rc.example.com", "", "atok")

    def test_requires_auth_token(self):
        with self.assertRaises(ValueError):
            RocketChatChannel("https://rc.example.com", "uid", "")

    def test_health_reports_stopped(self):
        ch = RocketChatChannel("https://rc.example.com", "uid", "atok")
        health = ch.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertFalse(health.ok)
        self.assertEqual(health.detail, "stopped")

    def test_name_is_rocketchat(self):
        ch = RocketChatChannel("https://rc.example.com", "uid", "atok")
        self.assertEqual(ch.name, "rocketchat")


if __name__ == "__main__":
    unittest.main()
