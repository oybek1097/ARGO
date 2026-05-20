"""Offline tests for the Discord channel adapter — spec section 4.5.

These tests never touch the network. They exercise:

* the pure `DiscordChannel.parse_message` against hand-built
  `MESSAGE_CREATE` payloads;
* the pure WebSocket frame codec (`encode_frame` / `decode_frame`) round
  trip and the RFC 6455 handshake-key helpers in `argo_brain.channels._ws`;
* that constructing a `DiscordChannel` only stores config and does not
  open any connection.

Run: python3 -m unittest tests.test_discord -v
"""

from __future__ import annotations

import unittest

from argo_brain.channels._ws import (
    OPCODE_PING,
    OPCODE_TEXT,
    decode_frame,
    encode_frame,
    expected_accept,
    make_ws_key,
)
from argo_brain.channels.base import AuthMode, ChannelDirection, ChannelMessage
from argo_brain.channels.discord import DiscordChannel


def _message_create(author_id: str, content: str,
                     is_bot: bool = False,
                     channel_id: str = "999000111") -> dict:
    """Builds a realistic MESSAGE_CREATE `d` payload."""
    return {
        "id": "1100000000000000001",
        "channel_id": channel_id,
        "content": content,
        "timestamp": "2026-05-20T12:00:00.000000+00:00",
        "author": {
            "id": author_id,
            "username": "alice",
            "discriminator": "0",
            "bot": is_bot,
        },
        "mentions": [],
        "attachments": [],
        "embeds": [],
    }


class ParseMessageTests(unittest.TestCase):
    """Tests for the pure `parse_message` helper."""

    def test_parses_realistic_payload(self) -> None:
        event = _message_create("123456789", "hello argo")
        msg = DiscordChannel.parse_message(event)
        self.assertIsInstance(msg, ChannelMessage)
        assert msg is not None
        self.assertEqual(msg.channel, "discord")
        self.assertEqual(msg.user_id, "discord:123456789")
        self.assertEqual(msg.target, "999000111")
        self.assertEqual(msg.text, "hello argo")
        self.assertEqual(msg.raw, event)

    def test_bot_author_ignored(self) -> None:
        event = _message_create("222", "I am a bot", is_bot=True)
        self.assertIsNone(DiscordChannel.parse_message(event))

    def test_empty_content_ignored(self) -> None:
        event = _message_create("333", "")
        self.assertIsNone(DiscordChannel.parse_message(event))

    def test_missing_content_ignored(self) -> None:
        event = _message_create("333", "x")
        del event["content"]
        self.assertIsNone(DiscordChannel.parse_message(event))

    def test_empty_event_ignored(self) -> None:
        self.assertIsNone(DiscordChannel.parse_message({}))

    def test_missing_channel_id_ignored(self) -> None:
        event = _message_create("444", "no channel")
        del event["channel_id"]
        self.assertIsNone(DiscordChannel.parse_message(event))

    def test_missing_author_ignored(self) -> None:
        event = _message_create("555", "no author")
        del event["author"]
        self.assertIsNone(DiscordChannel.parse_message(event))

    def test_channel_id_coerced_to_string(self) -> None:
        # Discord sends snowflakes as strings, but be robust to ints too.
        event = _message_create("666", "numeric chan")
        event["channel_id"] = 777888999
        msg = DiscordChannel.parse_message(event)
        assert msg is not None
        self.assertEqual(msg.target, "777888999")
        self.assertIsInstance(msg.target, str)


class WSFrameCodecTests(unittest.TestCase):
    """Tests for the pure RFC 6455 frame codec."""

    def test_text_round_trip_short(self) -> None:
        opcode, text = decode_frame(encode_frame("hello"))
        self.assertEqual(opcode, OPCODE_TEXT)
        self.assertEqual(text, "hello")

    def test_round_trip_unicode(self) -> None:
        original = "héllo 世界 \U0001f600"
        opcode, text = decode_frame(encode_frame(original))
        self.assertEqual(opcode, OPCODE_TEXT)
        self.assertEqual(text, original)

    def test_round_trip_medium_16bit_length(self) -> None:
        # Length 126..65535 uses the 16-bit extended length field.
        original = "a" * 5000
        opcode, text = decode_frame(encode_frame(original))
        self.assertEqual(opcode, OPCODE_TEXT)
        self.assertEqual(text, original)
        self.assertEqual(len(text), 5000)

    def test_round_trip_large_64bit_length(self) -> None:
        # Length >= 65536 uses the 64-bit extended length field.
        original = "z" * 70000
        opcode, text = decode_frame(encode_frame(original))
        self.assertEqual(text, original)
        self.assertEqual(len(text), 70000)

    def test_round_trip_empty(self) -> None:
        opcode, text = decode_frame(encode_frame(""))
        self.assertEqual(opcode, OPCODE_TEXT)
        self.assertEqual(text, "")

    def test_client_frame_is_masked(self) -> None:
        # RFC 6455 5.3: client frames MUST set the mask bit (0x80).
        frame = encode_frame("masked?")
        self.assertTrue(frame[1] & 0x80)

    def test_ping_opcode_preserved(self) -> None:
        opcode, text = decode_frame(encode_frame("pingdata", OPCODE_PING))
        self.assertEqual(opcode, OPCODE_PING)
        self.assertEqual(text, "pingdata")

    def test_decode_rejects_truncated_frame(self) -> None:
        with self.assertRaises(ValueError):
            decode_frame(b"\x81")


class WSHandshakeTests(unittest.TestCase):
    """Tests for the RFC 6455 handshake-key helpers."""

    def test_make_ws_key_decodes_to_16_bytes(self) -> None:
        import base64
        key = make_ws_key()
        self.assertEqual(len(base64.b64decode(key)), 16)

    def test_make_ws_key_is_random(self) -> None:
        self.assertNotEqual(make_ws_key(), make_ws_key())

    def test_expected_accept_known_vector(self) -> None:
        # The canonical example from RFC 6455 section 1.3.
        self.assertEqual(
            expected_accept("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        )

    def test_expected_accept_deterministic(self) -> None:
        key = make_ws_key()
        self.assertEqual(expected_accept(key), expected_accept(key))


class DiscordChannelConstructionTests(unittest.TestCase):
    """Tests that construction stores config without connecting."""

    def test_stores_token(self) -> None:
        ch = DiscordChannel("my-secret-bot-token")
        self.assertEqual(ch._token, "my-secret-bot-token")

    def test_empty_token_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DiscordChannel("")

    def test_channel_metadata(self) -> None:
        ch = DiscordChannel("tok")
        self.assertEqual(ch.name, "discord")
        self.assertEqual(ch.direction, ChannelDirection.BIDIRECTIONAL)
        self.assertEqual(ch.auth, AuthMode.TOKEN)

    def test_starts_not_running(self) -> None:
        ch = DiscordChannel("tok")
        self.assertFalse(ch._running)
        self.assertIsNone(ch._seq)
        self.assertIsNone(ch._ws)

    def test_health_reports_stopped_before_start(self) -> None:
        ch = DiscordChannel("tok")
        health = ch.health()
        self.assertFalse(health.ok)
        self.assertEqual(health.detail, "stopped")

    def test_chunks_splits_long_text(self) -> None:
        # Discord caps messages at 2000 chars; long text must be chunked.
        chunks = DiscordChannel._chunks("x" * 4500)
        self.assertEqual(len(chunks), 3)
        self.assertEqual([len(c) for c in chunks], [2000, 2000, 500])
        self.assertEqual("".join(chunks), "x" * 4500)

    def test_identify_payload_shape(self) -> None:
        import json
        ch = DiscordChannel("tok")
        payload = json.loads(ch._identify_payload())
        self.assertEqual(payload["op"], 2)
        self.assertEqual(payload["d"]["token"], "tok")
        self.assertIn("intents", payload["d"])

    def test_heartbeat_payload_carries_sequence(self) -> None:
        import json
        ch = DiscordChannel("tok")
        ch._seq = 42
        payload = json.loads(ch._heartbeat_payload())
        self.assertEqual(payload["op"], 1)
        self.assertEqual(payload["d"], 42)


if __name__ == "__main__":
    unittest.main()
