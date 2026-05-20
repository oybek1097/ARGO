"""Channel adapter tests (offline — no Telegram network calls)."""

import unittest

from argo_brain.channels import ChannelMessage, TelegramChannel

_TEXT_UPDATE = {
    "update_id": 42,
    "message": {
        "message_id": 7,
        "from": {"id": 12345, "username": "akbar"},
        "chat": {"id": 99999, "type": "private"},
        "text": "Salom ARGO",
    },
}
_EDITED_UPDATE = {
    "update_id": 43,
    "edited_message": {
        "from": {"id": 12345},
        "chat": {"id": 99999},
        "text": "tahrirlangan matn",
    },
}
_PHOTO_UPDATE = {  # message without text
    "update_id": 44,
    "message": {"from": {"id": 1}, "chat": {"id": 2}, "photo": []},
}
_JOIN_UPDATE = {"update_id": 45, "my_chat_member": {}}  # no message at all


class TestTelegramParsing(unittest.TestCase):
    def test_parse_text_message(self):
        msg = TelegramChannel.parse_update(_TEXT_UPDATE)
        self.assertIsInstance(msg, ChannelMessage)
        self.assertEqual(msg.channel, "telegram")
        self.assertEqual(msg.user_id, "telegram:12345")
        self.assertEqual(msg.target, "99999")
        self.assertEqual(msg.text, "Salom ARGO")

    def test_parse_edited_message(self):
        msg = TelegramChannel.parse_update(_EDITED_UPDATE)
        self.assertIsNotNone(msg)
        self.assertEqual(msg.text, "tahrirlangan matn")

    def test_non_text_message_ignored(self):
        self.assertIsNone(TelegramChannel.parse_update(_PHOTO_UPDATE))

    def test_non_message_update_ignored(self):
        self.assertIsNone(TelegramChannel.parse_update(_JOIN_UPDATE))

    def test_empty_token_rejected(self):
        with self.assertRaises(ValueError):
            TelegramChannel("")

    def test_long_text_chunked(self):
        chunks = TelegramChannel._chunks("x" * 9000)
        self.assertEqual(len(chunks), 3)  # 4096 + 4096 + 808
        self.assertTrue(all(len(c) <= 4096 for c in chunks))

    def test_short_text_single_chunk(self):
        self.assertEqual(TelegramChannel._chunks("hello"), ["hello"])

    def test_health_reports_stopped_initially(self):
        ch = TelegramChannel("dummy-token")
        self.assertFalse(ch.health().ok)


if __name__ == "__main__":
    unittest.main()
