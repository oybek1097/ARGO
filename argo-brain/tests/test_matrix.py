"""Offline tests for the Matrix channel adapter — spec section 4.5.

These tests never touch the network. They exercise `parse_sync` against
hand-built Matrix /sync response dicts and verify that constructing a
`MatrixChannel` only stores config without connecting.

Run: python3 -m unittest tests.test_matrix -v
"""

from __future__ import annotations

import unittest

from argo_brain.channels.base import ChannelHealth, ChannelMessage
from argo_brain.channels.matrix import MatrixChannel


def _text_event(sender: str, body: str) -> dict:
    """Builds a minimal m.room.message text event."""
    return {
        "type": "m.room.message",
        "sender": sender,
        "event_id": f"$evt-{body}",
        "content": {"msgtype": "m.text", "body": body},
    }


def _sync_with_rooms(rooms: dict) -> dict:
    """Wraps {room_id: [events]} into a /sync response shape."""
    return {
        "next_batch": "s_token_1",
        "rooms": {
            "join": {
                room_id: {"timeline": {"events": events}}
                for room_id, events in rooms.items()
            }
        },
    }


class TestParseSync(unittest.TestCase):
    """parse_sync extracts the right ChannelMessages, offline."""

    def test_single_text_message(self):
        sync = _sync_with_rooms(
            {"!room1:hs.org": [_text_event("@alice:hs.org", "hello")]}
        )
        msgs = MatrixChannel.parse_sync(sync)
        self.assertEqual(len(msgs), 1)
        msg = msgs[0]
        self.assertIsInstance(msg, ChannelMessage)
        self.assertEqual(msg.channel, "matrix")
        self.assertEqual(msg.user_id, "matrix:@alice:hs.org")
        self.assertEqual(msg.target, "!room1:hs.org")
        self.assertEqual(msg.text, "hello")

    def test_empty_sync(self):
        # A /sync with no rooms key at all yields nothing.
        self.assertEqual(MatrixChannel.parse_sync({}), [])
        # A /sync with an empty join map also yields nothing.
        self.assertEqual(
            MatrixChannel.parse_sync({"rooms": {"join": {}}}), []
        )

    def test_non_text_events_ignored(self):
        # Membership, images and reactions must not become ChannelMessages.
        events = [
            {"type": "m.room.member", "sender": "@bob:hs.org",
             "content": {"membership": "join"}},
            {"type": "m.room.message", "sender": "@bob:hs.org",
             "content": {"msgtype": "m.image", "body": "pic.png"}},
            {"type": "m.reaction", "sender": "@bob:hs.org",
             "content": {"m.relates_to": {"key": "thumbsup"}}},
            _text_event("@bob:hs.org", "the only real message"),
        ]
        sync = _sync_with_rooms({"!room1:hs.org": events})
        msgs = MatrixChannel.parse_sync(sync)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].text, "the only real message")

    def test_multiple_rooms(self):
        sync = _sync_with_rooms({
            "!alpha:hs.org": [
                _text_event("@alice:hs.org", "from alpha"),
            ],
            "!beta:hs.org": [
                _text_event("@bob:hs.org", "from beta one"),
                _text_event("@carol:hs.org", "from beta two"),
            ],
        })
        msgs = MatrixChannel.parse_sync(sync)
        self.assertEqual(len(msgs), 3)
        targets = {m.target for m in msgs}
        self.assertEqual(targets, {"!alpha:hs.org", "!beta:hs.org"})
        texts = {m.text for m in msgs}
        self.assertEqual(
            texts, {"from alpha", "from beta one", "from beta two"}
        )

    def test_event_missing_body_skipped(self):
        # A text event with an empty/missing body is not usable.
        events = [
            {"type": "m.room.message", "sender": "@a:hs.org",
             "content": {"msgtype": "m.text", "body": ""}},
            {"type": "m.room.message", "sender": "@a:hs.org",
             "content": {"msgtype": "m.text"}},
        ]
        sync = _sync_with_rooms({"!room1:hs.org": events})
        self.assertEqual(MatrixChannel.parse_sync(sync), [])

    def test_event_missing_sender_skipped(self):
        # Without a sender we cannot build a namespaced user_id.
        events = [{
            "type": "m.room.message",
            "content": {"msgtype": "m.text", "body": "no sender"},
        }]
        sync = _sync_with_rooms({"!room1:hs.org": events})
        self.assertEqual(MatrixChannel.parse_sync(sync), [])

    def test_raw_event_preserved(self):
        evt = _text_event("@alice:hs.org", "keep raw")
        sync = _sync_with_rooms({"!room1:hs.org": [evt]})
        msgs = MatrixChannel.parse_sync(sync)
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].raw, evt)
        self.assertEqual(msgs[0].raw["event_id"], "$evt-keep raw")


class TestMatrixChannelConstruction(unittest.TestCase):
    """Constructing a MatrixChannel stores config without connecting."""

    def test_construction_stores_config(self):
        ch = MatrixChannel(
            homeserver="https://hs.org",
            access_token="secret-token",
            user_id="@argo:hs.org",
        )
        self.assertEqual(ch.name, "matrix")
        self.assertEqual(ch._homeserver, "https://hs.org")
        self.assertEqual(ch._access_token, "secret-token")
        self.assertEqual(ch._user_id, "@argo:hs.org")
        # No connection happened: not running, no stream position yet.
        self.assertFalse(ch._running)
        self.assertIsNone(ch._since)

    def test_homeserver_trailing_slash_normalized(self):
        ch = MatrixChannel("https://hs.org/", "tok", "@argo:hs.org")
        self.assertEqual(ch._homeserver, "https://hs.org")
        self.assertTrue(ch._base.startswith("https://hs.org/_matrix/"))

    def test_missing_config_rejected(self):
        with self.assertRaises(ValueError):
            MatrixChannel("", "tok", "@argo:hs.org")
        with self.assertRaises(ValueError):
            MatrixChannel("https://hs.org", "", "@argo:hs.org")
        with self.assertRaises(ValueError):
            MatrixChannel("https://hs.org", "tok", "")

    def test_health_reports_stopped_then_running(self):
        ch = MatrixChannel("https://hs.org", "tok", "@argo:hs.org")
        health = ch.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertFalse(health.ok)
        self.assertEqual(health.detail, "stopped")
        # Flip the running flag the way start() would (still offline).
        ch._running = True
        running = ch.health()
        self.assertTrue(running.ok)
        self.assertEqual(running.detail, "syncing")


if __name__ == "__main__":
    unittest.main()
