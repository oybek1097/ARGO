"""Unit tests for the terminal UI slash-command router.

These tests exercise :class:`SlashCommandRouter` against a real
``AgentCore`` backed by the Mock provider on a temporary database.
"""

import tempfile
import unittest
from pathlib import Path

from argo_brain.config import Settings
from argo_brain.core import AgentCore
from argo_brain.tui import SlashCommandRouter, TUI
from argo_brain.tui.app import EXIT_SIGNAL


class TestSlashCommandRouter(unittest.TestCase):
    def setUp(self):
        # A real AgentCore on a temp DB with the default Mock provider.
        self._tmp = tempfile.TemporaryDirectory()
        settings = Settings(
            data_dir=self._tmp.name,
            db_path=str(Path(self._tmp.name) / "tui.db"),
        )
        self.agent = AgentCore(settings)
        self.router = SlashCommandRouter()

    def tearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    def test_help_returns_help_text(self):
        result = self.router.handle("/help", self.agent)
        self.assertIsNotNone(result)
        self.assertIn("Available commands", result)
        # Every documented command must appear in the help block.
        for name in SlashCommandRouter.COMMANDS:
            self.assertIn(name, result)

    def test_tools_lists_tools(self):
        result = self.router.handle("/tools", self.agent)
        self.assertIsNotNone(result)
        self.assertIn("Tools", result)
        # Each registered tool name must be listed.
        names = self.agent.registry.names()
        self.assertTrue(names, "expected the default registry to have tools")
        for name in names:
            self.assertIn(name, result)

    def test_model_shows_provider_model(self):
        result = self.router.handle("/model", self.agent)
        self.assertEqual(result, f"Model: {self.agent.provider.model}")

    def test_history_empty_then_populated(self):
        # With no entries the router reports an empty history.
        self.assertEqual(self.router.handle("/history", self.agent), "History is empty.")
        # After recording lines they show up in /history output.
        self.router.history.extend(["hello", "world"])
        result = self.router.handle("/history", self.agent)
        self.assertIn("hello", result)
        self.assertIn("world", result)

    def test_clear_empties_history(self):
        self.router.history.extend(["a", "b", "c"])
        result = self.router.handle("/clear", self.agent)
        self.assertEqual(result, "History cleared.")
        self.assertEqual(self.router.history, [])

    def test_exit_returns_exit_signal(self):
        self.assertEqual(self.router.handle("/exit", self.agent), EXIT_SIGNAL)
        # Aliases also terminate.
        self.assertEqual(self.router.handle("/quit", self.agent), EXIT_SIGNAL)
        self.assertEqual(self.router.handle("/q", self.agent), EXIT_SIGNAL)

    def test_unknown_command_handled(self):
        result = self.router.handle("/foo", self.agent)
        self.assertIsNotNone(result)
        self.assertIn("Unknown command", result)
        self.assertIn("/foo", result)

    def test_normal_line_returns_none(self):
        # A plain message is not a slash command -> None (treat as chat).
        self.assertIsNone(self.router.handle("hello argo", self.agent))
        self.assertIsNone(self.router.handle("  what is 2 + 2  ", self.agent))

    def test_command_is_case_insensitive_and_trimmed(self):
        # Leading whitespace and upper-case still resolve to the command.
        self.assertEqual(
            self.router.handle("  /HELP  ", self.agent),
            self.router.help_text(),
        )

    def test_command_with_extra_arguments(self):
        # Extra arguments after the command token are ignored gracefully.
        result = self.router.handle("/model extra args here", self.agent)
        self.assertEqual(result, f"Model: {self.agent.provider.model}")


class TestTUIHelpers(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        settings = Settings(
            data_dir=self._tmp.name,
            db_path=str(Path(self._tmp.name) / "tui.db"),
        )
        self.agent = AgentCore(settings)

    def tearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    def test_status_line_contains_model_and_counts(self):
        tui = TUI()
        line = tui.status_line(self.agent)
        self.assertIn(self.agent.provider.model, line)
        self.assertIn("messages: 0", line)

    def test_banner_mentions_provider(self):
        tui = TUI()
        banner = tui.banner(self.agent)
        self.assertIn("ARGO brain", banner)
        self.assertIn(self.agent.provider.model, banner)


if __name__ == "__main__":
    unittest.main()
