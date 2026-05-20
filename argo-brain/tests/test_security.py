"""Tests for the security subsystem: PII redaction and the audit log."""

import os
import tempfile
import unittest

from argo_brain.security import AuditLog, PIIRedactor


class TestPIIRedactor(unittest.TestCase):
    """Tests for the PIIRedactor class."""

    def setUp(self):
        self.redactor = PIIRedactor()

    def test_redacts_email(self):
        out = self.redactor.redact("Contact me at john.doe@example.com please")
        self.assertIn("[EMAIL]", out)
        self.assertNotIn("john.doe@example.com", out)

    def test_redacts_phone(self):
        out = self.redactor.redact("Call +1 (555) 123-4567 tomorrow")
        self.assertIn("[PHONE]", out)
        self.assertNotIn("555", out)

    def test_redacts_card(self):
        out = self.redactor.redact("Card 4111 1111 1111 1111 expires soon")
        self.assertIn("[CARD]", out)
        self.assertNotIn("4111", out)

    def test_redacts_ipv4(self):
        out = self.redactor.redact("Server at 192.168.0.1 is down")
        self.assertIn("[IP]", out)
        self.assertNotIn("192.168.0.1", out)

    def test_redacts_iban(self):
        out = self.redactor.redact("Pay to DE89370400440532013000 now")
        self.assertIn("[IBAN]", out)
        self.assertNotIn("DE89370400440532013000", out)

    def test_leaves_normal_text_intact(self):
        text = "The quick brown fox jumps over the lazy dog."
        self.assertEqual(self.redactor.redact(text), text)

    def test_empty_text(self):
        self.assertEqual(self.redactor.redact(""), "")

    def test_count_pii(self):
        text = (
            "Emails a@b.com and c@d.org, ip 10.0.0.1, "
            "card 4111111111111111"
        )
        counts = self.redactor.count_pii(text)
        self.assertEqual(counts["email"], 2)
        self.assertEqual(counts["ip"], 1)
        self.assertEqual(counts["card"], 1)

    def test_count_pii_empty(self):
        counts = self.redactor.count_pii("")
        self.assertEqual(sum(counts.values()), 0)

    def test_custom_placeholders(self):
        redactor = PIIRedactor(placeholders={"email": "<<EMAIL HIDDEN>>"})
        out = redactor.redact("Mail x@y.com here")
        self.assertIn("<<EMAIL HIDDEN>>", out)
        # Unspecified types still fall back to defaults.
        out2 = redactor.redact("IP 8.8.8.8")
        self.assertIn("[IP]", out2)

    def test_redacts_multiple_types_at_once(self):
        text = "Reach a@b.com or 10.1.2.3 fast"
        out = self.redactor.redact(text)
        self.assertIn("[EMAIL]", out)
        self.assertIn("[IP]", out)


class TestAuditLog(unittest.TestCase):
    """Tests for the AuditLog class."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "audit.db")
        self.log = AuditLog(self.db_path)

    def tearDown(self):
        self.log.close()
        self.tmpdir.cleanup()

    def test_log_and_recent_newest_first(self):
        self.log.log("alice", "login")
        self.log.log("bob", "logout")
        self.log.log("carol", "delete")
        rows = self.log.recent()
        self.assertEqual(len(rows), 3)
        # Newest entry must come first.
        self.assertEqual(rows[0]["user_id"], "carol")
        self.assertEqual(rows[2]["user_id"], "alice")

    def test_recent_respects_limit(self):
        for i in range(10):
            self.log.log("u", f"action{i}")
        rows = self.log.recent(limit=4)
        self.assertEqual(len(rows), 4)

    def test_by_user_filters(self):
        self.log.log("alice", "a1")
        self.log.log("bob", "b1")
        self.log.log("alice", "a2")
        rows = self.log.by_user("alice")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["user_id"] == "alice" for r in rows))

    def test_by_severity_filters(self):
        self.log.log("alice", "ok", severity="info")
        self.log.log("bob", "bad", severity="error")
        self.log.log("carol", "worse", severity="error")
        rows = self.log.by_severity("error")
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["severity"] == "error" for r in rows))

    def test_log_stores_all_fields(self):
        self.log.log("dave", "run", tool="shell", detail="ls -la",
                     severity="warning")
        row = self.log.recent()[0]
        self.assertEqual(row["user_id"], "dave")
        self.assertEqual(row["action"], "run")
        self.assertEqual(row["tool"], "shell")
        self.assertEqual(row["detail"], "ls -la")
        self.assertEqual(row["severity"], "warning")
        self.assertIsNotNone(row["ts"])

    def test_log_returns_row_id(self):
        first = self.log.log("u", "a")
        second = self.log.log("u", "b")
        self.assertEqual(second, first + 1)

    def test_append_only_no_mutation_methods(self):
        # The audit log must not expose update/delete operations.
        self.assertFalse(hasattr(self.log, "update"))
        self.assertFalse(hasattr(self.log, "delete"))

    def test_persists_across_connections(self):
        self.log.log("alice", "login")
        self.log.close()
        reopened = AuditLog(self.db_path)
        try:
            self.assertEqual(len(reopened.recent()), 1)
        finally:
            reopened.close()


if __name__ == "__main__":
    unittest.main()
