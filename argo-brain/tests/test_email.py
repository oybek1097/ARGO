"""Offline tests for the Email channel adapter — spec section 4.5.

These tests never touch a real IMAP/SMTP server. They exercise the static
`EmailChannel.parse_email` parser with locally-built RFC822 bytes, and
verify that constructing an `EmailChannel` only stores config.
"""

import unittest
from email.message import EmailMessage

from argo_brain.channels.base import ChannelHealth, ChannelMessage
from argo_brain.channels.email_channel import EmailChannel


def _build_plain_email(
    from_addr: str = "Alice Example <alice@example.com>",
    to_addr: str = "bot@argo.example",
    subject: str = "Hello ARGO",
    body: str = "This is the plain text body.",
) -> bytes:
    """Builds a simple plain-text email and returns its raw bytes."""
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    return msg.as_bytes()


class ParseEmailTests(unittest.TestCase):
    """Tests for the offline `EmailChannel.parse_email` static method."""

    def test_plain_email_parsed(self):
        raw = _build_plain_email(body="Please summarize my notes.")
        result = EmailChannel.parse_email(raw)
        self.assertIsInstance(result, ChannelMessage)
        self.assertEqual(result.channel, "email")
        self.assertTrue(result.user_id.startswith("email:"))
        self.assertIn("Please summarize my notes.", result.text)

    def test_user_id_and_target_use_bare_address(self):
        # Display name must be stripped from From: header.
        raw = _build_plain_email(from_addr="Alice Example <alice@example.com>")
        result = EmailChannel.parse_email(raw)
        self.assertEqual(result.user_id, "email:alice@example.com")
        # target is the sender address so replies route back.
        self.assertEqual(result.target, "alice@example.com")

    def test_subject_captured_in_raw(self):
        raw = _build_plain_email(subject="Quarterly report")
        result = EmailChannel.parse_email(raw)
        self.assertEqual(result.raw["subject"], "Quarterly report")

    def test_multipart_extracts_plain_part(self):
        msg = EmailMessage()
        msg["From"] = "bob@example.com"
        msg["To"] = "bot@argo.example"
        msg["Subject"] = "Multipart message"
        msg.set_content("PLAIN BODY HERE")
        msg.add_alternative(
            "<html><body><p>HTML BODY HERE</p></body></html>",
            subtype="html",
        )
        result = EmailChannel.parse_email(msg.as_bytes())
        self.assertIsInstance(result, ChannelMessage)
        self.assertIn("PLAIN BODY HERE", result.text)
        self.assertNotIn("<html>", result.text)

    def test_no_text_body_returns_none(self):
        # An HTML-only email carries no usable plain-text body.
        msg = EmailMessage()
        msg["From"] = "carol@example.com"
        msg["To"] = "bot@argo.example"
        msg["Subject"] = "HTML only"
        msg.set_content("<p>only html</p>", subtype="html")
        self.assertIsNone(EmailChannel.parse_email(msg.as_bytes()))

    def test_empty_body_returns_none(self):
        raw = _build_plain_email(body="   \n  \n")
        self.assertIsNone(EmailChannel.parse_email(raw))

    def test_missing_from_returns_none(self):
        msg = EmailMessage()
        msg["To"] = "bot@argo.example"
        msg["Subject"] = "No sender"
        msg.set_content("body text")
        self.assertIsNone(EmailChannel.parse_email(msg.as_bytes()))

    def test_non_ascii_body_decoded(self):
        raw = _build_plain_email(body="Schöne Grüße — café")
        result = EmailChannel.parse_email(raw)
        self.assertIn("Grüße", result.text)


class EmailChannelConstructionTests(unittest.TestCase):
    """Tests that constructing the channel does not connect to a server."""

    def test_construction_stores_config_without_connecting(self):
        # If this connected, it would fail (no such host) — it must not.
        channel = EmailChannel(
            imap_host="imap.invalid.example",
            smtp_host="smtp.invalid.example",
            username="bot@argo.example",
            password="secret",
        )
        self.assertEqual(channel.name, "email")
        self.assertEqual(channel._imap_port, 993)
        self.assertEqual(channel._smtp_port, 587)
        self.assertEqual(channel._poll_interval, 30)

    def test_health_reports_stopped_before_start(self):
        channel = EmailChannel(
            imap_host="imap.invalid.example",
            smtp_host="smtp.invalid.example",
            username="bot@argo.example",
            password="secret",
        )
        health = channel.health()
        self.assertIsInstance(health, ChannelHealth)
        self.assertFalse(health.ok)
        self.assertEqual(health.detail, "stopped")

    def test_missing_hosts_rejected(self):
        with self.assertRaises(ValueError):
            EmailChannel(
                imap_host="",
                smtp_host="smtp.example",
                username="bot@argo.example",
                password="secret",
            )


if __name__ == "__main__":
    unittest.main()
