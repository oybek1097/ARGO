"""Fast smoke tests for the ARGO brain.

These tests are intentionally lightweight: they check that every top-level
subpackage imports cleanly, that the default tool registry is populated, and
that an `AgentCore` can be constructed and process a trivial message. They
use the no-network `MockProvider` and a temp database.
"""

from __future__ import annotations

import importlib
import tempfile
import unittest
from pathlib import Path

from argo_brain.config import Settings
from argo_brain.core import AgentCore, AgentRequest
from argo_brain.tools import build_default_registry

# Every top-level subpackage of `argo_brain` that should import cleanly.
_SUBPACKAGES = [
    "api", "cache", "channels", "checkpoint", "compliance", "context",
    "core", "cron", "handoff", "hub", "ipc", "language", "mcp", "memory",
    "multi_agent", "observability", "perf", "plugin", "providers", "rl",
    "security", "skills", "terminals", "tools", "tui",
]


class TestImports(unittest.TestCase):
    """Importing every subpackage of argo_brain must succeed."""

    def test_root_package_imports(self):
        mod = importlib.import_module("argo_brain")
        self.assertTrue(hasattr(mod, "__version__"))

    def test_all_subpackages_import(self):
        failures = []
        for name in _SUBPACKAGES:
            try:
                importlib.import_module(f"argo_brain.{name}")
            except Exception as exc:  # noqa: BLE001 - report any failure
                failures.append(f"{name}: {exc!r}")
        self.assertEqual(failures, [], f"subpackage import failures: {failures}")

    def test_core_exports(self):
        from argo_brain.core import AgentCore as AC, AgentRequest as AR
        self.assertTrue(callable(AC))
        self.assertTrue(callable(AR))

    def test_provider_factory_imports(self):
        from argo_brain.providers import MockProvider, get_provider
        self.assertIsInstance(get_provider("mock"), MockProvider)


class TestRegistrySmoke(unittest.TestCase):
    """The default tool registry must be richly populated."""

    def test_default_registry_has_many_tools(self):
        registry = build_default_registry()
        self.assertGreaterEqual(
            len(registry.all()), 50,
            f"expected 50+ tools, got {len(registry.all())}",
        )

    def test_registry_names_unique(self):
        registry = build_default_registry()
        names = registry.names()
        self.assertEqual(len(names), len(set(names)), "duplicate tool names")

    def test_registry_schemas_well_formed(self):
        registry = build_default_registry()
        for schema in registry.schemas():
            self.assertEqual(schema.get("type"), "function")
            self.assertIn("name", schema.get("function", {}))

    def test_core_tools_present(self):
        registry = build_default_registry()
        names = set(registry.names())
        for expected in ("calculate", "current_time"):
            self.assertIn(expected, names)


class TestAgentSmoke(unittest.IsolatedAsyncioTestCase):
    """AgentCore must construct and process a trivial message."""

    async def asyncSetUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.settings = Settings(
            data_dir=self._tmp.name,
            db_path=str(Path(self._tmp.name) / "smoke.db"),
        )
        self.agent = AgentCore(self.settings)

    async def asyncTearDown(self):
        self.agent.close()
        self._tmp.cleanup()

    async def test_agent_constructs_with_mock_provider(self):
        self.assertEqual(self.agent.provider.model, "mock")

    async def test_agent_processes_trivial_message(self):
        resp = await self.agent.process(
            AgentRequest(user_id="smoke", message="hello there")
        )
        self.assertTrue(resp.content)
        self.assertEqual(resp.iterations, 1)
        self.assertGreaterEqual(resp.duration_ms, 0)

    async def test_agent_uses_shared_registry(self):
        # The agent's registry should be the populated default registry.
        self.assertGreaterEqual(len(self.agent.registry.all()), 50)


if __name__ == "__main__":
    unittest.main()
