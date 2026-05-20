"""Tests for the built-in plugins — spec section 4.6."""

from __future__ import annotations

import unittest

from argo_brain.plugin.builtin import (
    LanguageEnforcerPlugin,
    PIIRedactorPlugin,
    SecurityAuditPlugin,
    builtin_plugins,
)
from argo_brain.plugin.builtin.audit import AuditEvent
from argo_brain.plugin.registry import PluginRegistry
from argo_brain.tools.base import ToolCall, ToolResult


def _call(name: str, **args: object) -> ToolCall:
    """Build a ToolCall with a deterministic id for tests."""
    return ToolCall(id=f"id-{name}", name=name, arguments=dict(args))


class SecurityAuditPluginTests(unittest.IsolatedAsyncioTestCase):
    """SecurityAuditPlugin records and flags tool calls."""

    async def test_records_each_call(self) -> None:
        plugin = SecurityAuditPlugin()
        await plugin.pre_tool_call(_call("read_file"), "u1")
        await plugin.pre_tool_call(_call("search"), "u1")
        self.assertEqual(len(plugin.events), 2)

    async def test_event_captures_user_and_args(self) -> None:
        plugin = SecurityAuditPlugin()
        await plugin.pre_tool_call(_call("read_file", path="/etc"), "alice")
        event = plugin.events[0]
        self.assertIsInstance(event, AuditEvent)
        self.assertEqual(event.user_id, "alice")
        self.assertEqual(event.arguments, {"path": "/etc"})

    async def test_call_passes_through_unchanged(self) -> None:
        plugin = SecurityAuditPlugin()
        call = _call("read_file")
        result = await plugin.pre_tool_call(call, "u1")
        self.assertIs(result, call)

    async def test_dangerous_tool_is_flagged(self) -> None:
        plugin = SecurityAuditPlugin()
        await plugin.pre_tool_call(_call("shell_exec"), "u1")
        await plugin.pre_tool_call(_call("terraform_apply"), "u1")
        await plugin.pre_tool_call(_call("write_file"), "u1")
        self.assertEqual(len(plugin.dangerous_events()), 3)

    async def test_safe_tool_not_flagged(self) -> None:
        plugin = SecurityAuditPlugin()
        await plugin.pre_tool_call(_call("read_file"), "u1")
        self.assertEqual(plugin.dangerous_events(), [])
        self.assertFalse(plugin.events[0].dangerous)

    def test_is_dangerous_is_case_insensitive(self) -> None:
        self.assertTrue(SecurityAuditPlugin.is_dangerous("Git_Commit"))
        self.assertTrue(SecurityAuditPlugin.is_dangerous("ZIP_EXTRACT"))
        self.assertFalse(SecurityAuditPlugin.is_dangerous("list_dir"))

    async def test_clear_drops_events(self) -> None:
        plugin = SecurityAuditPlugin()
        await plugin.pre_tool_call(_call("read_file"), "u1")
        plugin.clear()
        self.assertEqual(plugin.events, [])


class LanguageEnforcerPluginTests(unittest.IsolatedAsyncioTestCase):
    """LanguageEnforcerPlugin records and checks response language."""

    async def test_records_responses(self) -> None:
        plugin = LanguageEnforcerPlugin("english")
        await plugin.on_response("u1", "Hello there", "model-x")
        await plugin.on_response("u1", "Goodbye now", "model-x")
        self.assertEqual(len(plugin.records), 2)

    async def test_detects_matching_target_language(self) -> None:
        plugin = LanguageEnforcerPlugin("english")
        await plugin.on_response("u1", "This is plain English text", "m")
        self.assertTrue(plugin.records[0].matched)
        self.assertEqual(plugin.mismatches(), [])

    async def test_detects_mismatch(self) -> None:
        plugin = LanguageEnforcerPlugin("english")
        await plugin.on_response("u1", "Это русский текст", "m")
        self.assertEqual(len(plugin.mismatches()), 1)
        self.assertFalse(plugin.records[0].matched)

    async def test_cyrillic_target_matches_cyrillic(self) -> None:
        plugin = LanguageEnforcerPlugin("russian")
        await plugin.on_response("u1", "Привет мир", "m")
        self.assertTrue(plugin.records[0].matched)

    def test_detect_script_heuristic(self) -> None:
        self.assertEqual(
            LanguageEnforcerPlugin.detect_script("hello world"), "latin"
        )
        self.assertEqual(
            LanguageEnforcerPlugin.detect_script("привет"), "cyrillic"
        )
        self.assertEqual(LanguageEnforcerPlugin.detect_script("12345"), "unknown")

    async def test_clear_drops_records(self) -> None:
        plugin = LanguageEnforcerPlugin("english")
        await plugin.on_response("u1", "Hello", "m")
        plugin.clear()
        self.assertEqual(plugin.records, [])


class PIIRedactorPluginTests(unittest.IsolatedAsyncioTestCase):
    """PIIRedactorPlugin scrubs PII from tool results."""

    async def test_redacts_email(self) -> None:
        plugin = PIIRedactorPlugin()
        result = ToolResult(content="Contact bob@example.com please")
        out = await plugin.transform_tool_result(_call("t"), result, "u1")
        self.assertNotIn("bob@example.com", out.content)
        self.assertIn("[EMAIL]", out.content)

    async def test_redacts_phone(self) -> None:
        plugin = PIIRedactorPlugin()
        result = ToolResult(content="Call +1 415 555 0123 now")
        out = await plugin.transform_tool_result(_call("t"), result, "u1")
        self.assertIn("[PHONE]", out.content)

    async def test_returns_new_result_object(self) -> None:
        plugin = PIIRedactorPlugin()
        result = ToolResult(content="email me at a@b.com")
        out = await plugin.transform_tool_result(_call("t"), result, "u1")
        self.assertIsNot(out, result)
        self.assertEqual(result.content, "email me at a@b.com")

    async def test_preserves_other_fields(self) -> None:
        plugin = PIIRedactorPlugin()
        result = ToolResult(
            content="a@b.com", success=False, duration_ms=42,
            metadata={"k": "v"},
        )
        out = await plugin.transform_tool_result(_call("t"), result, "u1")
        self.assertFalse(out.success)
        self.assertEqual(out.duration_ms, 42)
        self.assertEqual(out.metadata, {"k": "v"})

    async def test_tracks_redaction_counts(self) -> None:
        plugin = PIIRedactorPlugin()
        result = ToolResult(content="a@b.com and c@d.com")
        await plugin.transform_tool_result(_call("t"), result, "u1")
        self.assertEqual(plugin.redaction_counts.get("email"), 2)

    async def test_clean_content_unchanged(self) -> None:
        plugin = PIIRedactorPlugin()
        result = ToolResult(content="nothing sensitive here")
        out = await plugin.transform_tool_result(_call("t"), result, "u1")
        self.assertEqual(out.content, "nothing sensitive here")


class BuiltinFactoryTests(unittest.IsolatedAsyncioTestCase):
    """builtin_plugins() factory and registry integration."""

    def test_factory_returns_three_plugins(self) -> None:
        plugins = builtin_plugins()
        self.assertEqual(len(plugins), 3)

    def test_factory_returns_expected_types(self) -> None:
        types = {type(p) for p in builtin_plugins()}
        self.assertEqual(
            types,
            {SecurityAuditPlugin, LanguageEnforcerPlugin, PIIRedactorPlugin},
        )

    def test_factory_returns_fresh_instances(self) -> None:
        first = builtin_plugins()
        second = builtin_plugins()
        self.assertIsNot(first[0], second[0])

    async def test_audit_plugin_through_registry(self) -> None:
        registry = PluginRegistry()
        audit = SecurityAuditPlugin()
        await registry.register(audit)
        allowed = await registry.run_pre_tool(
            [_call("shell_exec"), _call("read_file")], "u1"
        )
        self.assertEqual(len(allowed), 2)
        self.assertEqual(len(audit.events), 2)
        self.assertEqual(len(audit.dangerous_events()), 1)

    async def test_pii_plugin_through_registry(self) -> None:
        registry = PluginRegistry()
        await registry.register(PIIRedactorPlugin())
        result = await registry.run_post_tool(
            _call("t"), ToolResult(content="mail x@y.com"), "u1"
        )
        self.assertIn("[EMAIL]", result.content)


if __name__ == "__main__":
    unittest.main()
