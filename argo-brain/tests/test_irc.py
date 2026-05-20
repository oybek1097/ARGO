"""Offline tests for the IRC channel adapter — spec section 4.5.

These tests never open a real socket: they exercise the static protocol
parsers (`parse_line`, `is_ping`, `pong_reply`) and plain construction.
"""

import unittest

from argo_brain.channels.base import ChannelHealth, ChannelMessage
from argo_brain.channels.irc import IRCChannel


class TestParseLine(unittest.TestCase):
    """`IRCChannel.parse_line` protocol parsing."""

    def test_privmsg_returns_channel_message(self) -> None:
        line = ":alice!user@host PRIVMSG #room :hello there"
        msg = IRCChannel.parse_line(line)
        self.assertIsInstance(msg, ChannelMessage)
        assert msg is not None  # narrow for type-checkers
        self.assertEqual(msg.channel, "irc")
        self.assertEqual(msg.user_id, "irc:alice")
        self.assertEqual(msg.target, "#room")
        self.assertEqual(msg.text, "hello there")

    def test_ping_line_returns_none(self) -> None:
        self.assertIsNone(IRCChannel.parse_line("PING :irc.example.org"))

    def test_join_line_returns_none(self) -> None:
        # A JOIN line carries a prefix but is not a PRIVMSG.
        self.assertIsNone(
            IRCChannel.parse_line(":bob!user@host JOIN #room")
        )

    def test_server_notice_returns_none(self) -> None:
        # Numeric server replies are not user messages.
        line = ":irc.example.org 001 argo :Welcome to the network"
        self.assertIsNone(IRCChannel.parse_line(line))

    def test_body_with_colon_is_parsed_fully(self) -> None:
        # Everything after the first " :" is the body, colons included.
        line = ":carol!u@h PRIVMSG #room :see http://x.y/z :note: done"
        msg = IRCChannel.parse_line(line)
        assert msg is not None
        self.assertEqual(msg.text, "see http://x.y/z :note: done")
        self.assertEqual(msg.user_id, "irc:carol")

    def test_private_query_target_is_a_nick(self) -> None:
        # A PRIVMSG aimed at the bot directly: target is a nick, not a channel.
        line = ":dave!u@h PRIVMSG argo :ping"
        msg = IRCChannel.parse_line(line)
        assert msg is not None
        self.assertEqual(msg.target, "argo")
        self.assertEqual(msg.text, "ping")

    def test_crlf_is_stripped(self) -> None:
        line = ":eve!u@h PRIVMSG #room :trailing\r\n"
        msg = IRCChannel.parse_line(line)
        assert msg is not None
        self.assertEqual(msg.text, "trailing")


class TestPing(unittest.TestCase):
    """PING/PONG keepalive handling."""

    def test_is_ping_detects_ping(self) -> None:
        self.assertTrue(IRCChannel.is_ping("PING :irc.example.org"))

    def test_is_ping_rejects_privmsg(self) -> None:
        self.assertFalse(
            IRCChannel.is_ping(":a!u@h PRIVMSG #room :hi")
        )

    def test_pong_reply_matches_ping(self) -> None:
        self.assertEqual(
            IRCChannel.pong_reply("PING :irc.example.org"),
            "PONG :irc.example.org",
        )


class TestConstruction(unittest.TestCase):
    """Constructing an `IRCChannel` must not touch the network."""

    def test_construction_stores_config(self) -> None:
        ch = IRCChannel("irc.example.org", port=6667, nick="argo",
                         channel="#argo")
        self.assertEqual(ch.name, "irc")
        self.assertEqual(ch._host, "irc.example.org")
        self.assertEqual(ch._port, 6667)
        self.assertEqual(ch._nick, "argo")
        self.assertEqual(ch._channel, "#argo")
        self.assertFalse(ch._running)

    def test_default_port(self) -> None:
        ch = IRCChannel("irc.example.org", nick="argo", channel="#argo")
        self.assertEqual(ch._port, 6667)

    def test_health_before_start(self) -> None:
        ch = IRCChannel("irc.example.org", nick="argo", channel="#argo")
        health = ch.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertFalse(health.ok)
        self.assertEqual(health.detail, "stopped")

    def test_missing_host_raises(self) -> None:
        with self.assertRaises(ValueError):
            IRCChannel("", nick="argo", channel="#argo")


if __name__ == "__main__":
    unittest.main()
