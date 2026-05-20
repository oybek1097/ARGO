"""Tests for the RBAC engine (spec section 10)."""

import unittest

from argo_brain.security.rbac import (
    DEFAULT_ROLES,
    DEFAULT_TOOL_RULES,
    RBAC,
    Permission,
    Role,
    ToolRule,
)


class TestPermission(unittest.TestCase):
    """Tests for hierarchical permission matching."""

    def test_global_wildcard_matches_everything(self):
        self.assertTrue(Permission.matches("*", "memory:read"))
        self.assertTrue(Permission.matches("*", "anything"))

    def test_exact_match(self):
        self.assertTrue(Permission.matches("memory:read", "memory:read"))

    def test_no_match_on_different_permission(self):
        self.assertFalse(Permission.matches("memory:read", "memory:write"))

    def test_prefix_wildcard_matches_namespace(self):
        self.assertTrue(Permission.matches("memory:*", "memory:read"))
        self.assertTrue(Permission.matches("memory:*", "memory:write"))

    def test_prefix_wildcard_does_not_cross_namespace(self):
        self.assertFalse(Permission.matches("memory:*", "skills:read"))

    def test_parent_namespace_covers_child(self):
        self.assertTrue(Permission.matches("memory", "memory:read"))

    def test_child_does_not_cover_parent(self):
        self.assertFalse(Permission.matches("memory:read", "memory"))

    def test_deep_hierarchy(self):
        self.assertTrue(Permission.matches("tools:*", "tools:safe:list"))
        self.assertFalse(
            Permission.matches("tools:safe", "tools:unsafe:run")
        )


class TestRole(unittest.TestCase):
    """Tests for the Role dataclass."""

    def test_role_grants_held_permission(self):
        role = Role("custom", frozenset({"chat", "memory:read"}))
        self.assertTrue(role.grants("chat"))
        self.assertTrue(role.grants("memory:read"))

    def test_role_denies_unheld_permission(self):
        role = Role("custom", frozenset({"chat"}))
        self.assertFalse(role.grants("memory:write"))

    def test_role_with_wildcard_grants_all(self):
        role = Role("super", frozenset({"*"}))
        self.assertTrue(role.grants("memory:write"))

    def test_role_is_hashable(self):
        # Frozen dataclass should be usable in sets / as dict keys.
        roles = {Role("a", frozenset()), Role("b", frozenset())}
        self.assertEqual(len(roles), 2)


class TestDefaultRoles(unittest.TestCase):
    """Tests verifying the default roles match spec section 10."""

    def test_admin_has_wildcard(self):
        self.assertEqual(DEFAULT_ROLES["admin"].permissions, frozenset({"*"}))

    def test_user_permissions_exact(self):
        self.assertEqual(
            DEFAULT_ROLES["user"].permissions,
            frozenset(
                {
                    "chat",
                    "memory:read",
                    "memory:write",
                    "skills:read",
                    "tools:safe",
                }
            ),
        )

    def test_read_only_permissions_exact(self):
        self.assertEqual(
            DEFAULT_ROLES["read_only"].permissions,
            frozenset({"chat", "memory:read", "skills:read"}),
        )

    def test_service_permissions_exact(self):
        self.assertEqual(
            DEFAULT_ROLES["service"].permissions,
            frozenset({"api:webhook"}),
        )

    def test_all_four_roles_present(self):
        self.assertEqual(
            set(DEFAULT_ROLES),
            {"admin", "user", "read_only", "service"},
        )


class TestRBACCan(unittest.TestCase):
    """Tests for RBAC.can permission checks."""

    def setUp(self):
        self.rbac = RBAC()

    def test_admin_can_do_anything(self):
        self.assertTrue(self.rbac.can("admin", "memory:write"))
        self.assertTrue(self.rbac.can("admin", "some:obscure:permission"))

    def test_user_can_read_and_write_memory(self):
        self.assertTrue(self.rbac.can("user", "memory:read"))
        self.assertTrue(self.rbac.can("user", "memory:write"))

    def test_read_only_cannot_write_memory(self):
        self.assertTrue(self.rbac.can("read_only", "memory:read"))
        self.assertFalse(self.rbac.can("read_only", "memory:write"))

    def test_service_only_has_webhook(self):
        self.assertTrue(self.rbac.can("service", "api:webhook"))
        self.assertFalse(self.rbac.can("service", "chat"))

    def test_unknown_role_denied(self):
        self.assertFalse(self.rbac.can("ghost", "chat"))

    def test_user_cannot_use_unsafe_tools_permission(self):
        # "tools:safe" must not authorize "tools:unsafe".
        self.assertFalse(self.rbac.can("user", "tools:unsafe"))


class TestRBACToolAllowed(unittest.TestCase):
    """Tests for RBAC.tool_allowed."""

    def setUp(self):
        self.rbac = RBAC()

    def test_kubectl_allowed_for_admin(self):
        self.assertTrue(self.rbac.tool_allowed("admin", "kubectl"))

    def test_kubectl_denied_for_user(self):
        self.assertFalse(self.rbac.tool_allowed("user", "kubectl"))

    def test_kubectl_allowed_for_custom_devops_role(self):
        rbac = RBAC()
        rbac.add_role(Role("devops", frozenset({"tools:safe"})))
        self.assertTrue(rbac.tool_allowed("devops", "kubectl"))

    def test_shell_exec_allowed_for_user(self):
        self.assertTrue(self.rbac.tool_allowed("user", "shell_exec"))

    def test_shell_exec_denied_for_read_only(self):
        self.assertFalse(self.rbac.tool_allowed("read_only", "shell_exec"))

    def test_unrestricted_tool_allowed_for_any_known_role(self):
        self.assertTrue(self.rbac.tool_allowed("read_only", "calculator"))

    def test_unrestricted_tool_denied_for_unknown_role(self):
        self.assertFalse(self.rbac.tool_allowed("ghost", "calculator"))

    def test_empty_requires_role_allows_any_known_role(self):
        rbac = RBAC()
        rbac.set_tool_rule("open_tool", ToolRule(frozenset()))
        self.assertTrue(rbac.tool_allowed("read_only", "open_tool"))
        self.assertFalse(rbac.tool_allowed("ghost", "open_tool"))


class TestRBACConfirmation(unittest.TestCase):
    """Tests for tool confirmation flags."""

    def setUp(self):
        self.rbac = RBAC()

    def test_kubectl_needs_confirmation(self):
        self.assertTrue(self.rbac.tool_needs_confirmation("kubectl"))

    def test_shell_exec_needs_confirmation(self):
        self.assertTrue(self.rbac.tool_needs_confirmation("shell_exec"))

    def test_unknown_tool_no_confirmation(self):
        self.assertFalse(self.rbac.tool_needs_confirmation("calculator"))


class TestRBACCustomConfig(unittest.TestCase):
    """Tests for customizing the RBAC engine."""

    def test_custom_role_table(self):
        roles = {"guest": Role("guest", frozenset({"chat"}))}
        rbac = RBAC(roles=roles)
        self.assertTrue(rbac.can("guest", "chat"))
        # Default roles are absent when a custom table is supplied.
        self.assertFalse(rbac.can("admin", "chat"))

    def test_add_role_then_check(self):
        rbac = RBAC()
        rbac.add_role(Role("auditor", frozenset({"audit:read"})))
        self.assertTrue(rbac.can("auditor", "audit:read"))

    def test_set_tool_rule_overrides_default(self):
        rbac = RBAC()
        rbac.set_tool_rule("kubectl", ToolRule(frozenset({"user"})))
        self.assertTrue(rbac.tool_allowed("user", "kubectl"))
        self.assertFalse(rbac.tool_allowed("admin", "kubectl"))

    def test_defaults_not_mutated_by_instance(self):
        rbac = RBAC()
        rbac.add_role(Role("temp", frozenset()))
        # Module-level DEFAULT_ROLES must stay untouched.
        self.assertNotIn("temp", DEFAULT_ROLES)
        self.assertEqual(set(DEFAULT_TOOL_RULES), {"kubectl", "shell_exec"})


if __name__ == "__main__":
    unittest.main()
