"""Tests for the extended DevOps toolset — spec section 4.4.

Vault, SSH, Ansible and Terraform CLIs are NOT installed in the test
environment, so every tool must fail gracefully (``success is False`` with a
"not installed" message) rather than raising. If a CLI happens to be present,
the call may succeed — in either case it must not raise.
"""

import asyncio
import unittest

from argo_brain.tools.base import Tool, ToolResult
from argo_brain.tools.builtin.devops_extra import (
    AnsiblePlaybookTool,
    SSHExecTool,
    TerraformApplyTool,
    TerraformPlanTool,
    VaultGetTool,
    VaultPutTool,
    devops_extra_tools,
)


def _run(coro):
    """Runs a coroutine to completion on a fresh event loop."""
    return asyncio.run(coro)


class DevopsExtraGracefulFailureTests(unittest.TestCase):
    """Each tool must not raise; it either succeeds or reports "not installed"."""

    def _assert_graceful(self, result: ToolResult, expect_not_installed=True):
        """A graceful result never raises; on failure it carries a clear message.

        When the CLI is genuinely absent the message says "not installed".
        Some CLIs (e.g. ``ssh``) may be present in the environment, in which
        case the call can fail for another clean reason (timeout, connection
        refused) or even succeed — all acceptable, none may raise.
        """
        self.assertIsInstance(result, ToolResult)
        if not result.success:
            self.assertTrue(result.content.strip(), "failure needs a message")
            if expect_not_installed:
                self.assertIn("not installed", result.content.lower())

    def test_vault_get_graceful(self):
        result = _run(VaultGetTool()(user_id="u", path="secret/data/app"))
        self._assert_graceful(result)

    def test_vault_put_graceful(self):
        result = _run(VaultPutTool()(
            user_id="u", path="secret/data/app", data={"key": "value"}
        ))
        self._assert_graceful(result)

    def test_ssh_exec_graceful(self):
        # ssh is commonly installed; a missing host fails cleanly without a CLI
        # call, which keeps this test fast and deterministic.
        result = _run(SSHExecTool()(user_id="u", host="", command="uptime"))
        self._assert_graceful(result, expect_not_installed=False)

    def test_ansible_playbook_graceful(self):
        result = _run(AnsiblePlaybookTool()(user_id="u", playbook="site.yml"))
        self._assert_graceful(result)

    def test_terraform_plan_graceful(self):
        result = _run(TerraformPlanTool()(user_id="u", directory="."))
        self._assert_graceful(result)

    def test_terraform_apply_graceful(self):
        result = _run(TerraformApplyTool()(user_id="u", directory="."))
        self._assert_graceful(result)


class DevopsExtraValidationTests(unittest.TestCase):
    """Missing required arguments are rejected cleanly, without raising."""

    def test_vault_get_requires_path(self):
        result = _run(VaultGetTool()(user_id="u", path=""))
        self.assertFalse(result.success)

    def test_vault_put_requires_data(self):
        result = _run(VaultPutTool()(user_id="u", path="secret/x", data={}))
        self.assertFalse(result.success)

    def test_ssh_exec_requires_host_and_command(self):
        result = _run(SSHExecTool()(user_id="u", host="", command="ls"))
        self.assertFalse(result.success)

    def test_ansible_playbook_requires_playbook(self):
        result = _run(AnsiblePlaybookTool()(user_id="u", playbook=""))
        self.assertFalse(result.success)


class DevopsExtraDangerousFlagTests(unittest.TestCase):
    """Mutating tools must be marked dangerous; read-only tools must not be."""

    def test_dangerous_tools_flagged(self):
        for tool in (VaultPutTool(), SSHExecTool(),
                     AnsiblePlaybookTool(), TerraformApplyTool()):
            self.assertTrue(tool.dangerous, f"{tool.name} should be dangerous")

    def test_readonly_tools_not_flagged(self):
        for tool in (VaultGetTool(), TerraformPlanTool()):
            self.assertFalse(tool.dangerous, f"{tool.name} should not be dangerous")


class DevopsExtraRegistryTests(unittest.TestCase):
    """`devops_extra_tools()` exposes all six tools with the expected names."""

    def test_returns_six_tools(self):
        tools = devops_extra_tools()
        self.assertEqual(len(tools), 6)
        for tool in tools:
            self.assertIsInstance(tool, Tool)

    def test_expected_names(self):
        names = {tool.name for tool in devops_extra_tools()}
        self.assertEqual(
            names,
            {"vault_get", "vault_put", "ssh_exec",
             "ansible_playbook", "terraform_plan", "terraform_apply"},
        )

    def test_tools_have_schemas(self):
        for tool in devops_extra_tools():
            schema = tool.schema()
            self.assertEqual(schema["type"], "function")
            self.assertEqual(schema["function"]["name"], tool.name)


if __name__ == "__main__":
    unittest.main()
