"""Tests for the ARGO web dashboard page (stdlib unittest)."""

import unittest

from argo_brain.api.dashboard import DASHBOARD_HTML, dashboard_page


class TestDashboard(unittest.TestCase):
    """Verify the dashboard HTML constant and accessor function."""

    def test_html_is_non_empty_string(self):
        """DASHBOARD_HTML should be a non-trivial string."""
        self.assertIsInstance(DASHBOARD_HTML, str)
        self.assertGreater(len(DASHBOARD_HTML), 100)

    def test_html_looks_like_html(self):
        """The page should contain core HTML structural tags."""
        self.assertIn("<html", DASHBOARD_HTML)
        self.assertIn("</html>", DASHBOARD_HTML)
        self.assertIn("<!DOCTYPE html>", DASHBOARD_HTML)

    def test_html_references_chat_endpoint(self):
        """The page must POST to /api/chat to talk to the agent."""
        self.assertIn("/api/chat", DASHBOARD_HTML)

    def test_html_references_health_endpoint(self):
        """The page must call /api/health to show the argo version."""
        self.assertIn("/api/health", DASHBOARD_HTML)

    def test_html_contains_script(self):
        """The page must include an inline <script> block."""
        self.assertIn("<script>", DASHBOARD_HTML)
        self.assertIn("</script>", DASHBOARD_HTML)

    def test_html_posts_expected_payload(self):
        """The chat request should use the web-user id and a message field."""
        self.assertIn("web-user", DASHBOARD_HTML)
        self.assertIn("message", DASHBOARD_HTML)

    def test_no_external_resources(self):
        """The page must be self-contained (no external libraries/CDN)."""
        self.assertNotIn("http://", DASHBOARD_HTML)
        self.assertNotIn("https://", DASHBOARD_HTML)

    def test_dashboard_page_returns_html(self):
        """dashboard_page() must return the DASHBOARD_HTML constant."""
        self.assertEqual(dashboard_page(), DASHBOARD_HTML)
        self.assertIsInstance(dashboard_page(), str)


if __name__ == "__main__":
    unittest.main()
