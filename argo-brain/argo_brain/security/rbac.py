"""Role-based access control engine (spec section 10).

Implements the RBAC model described in the ARGO Agent v3.0 technical
specification: a fixed set of default roles (admin / user / read_only /
service), hierarchical permission strings with wildcard support and a
table of per-tool permission rules.

Permissions are colon-separated hierarchical strings, e.g. ``memory:read``
or ``tools:safe``. The wildcard ``*`` grants everything; a prefix wildcard
such as ``memory:*`` grants every permission under that namespace.

This module depends only on the Python 3.12 standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class Permission:
    """Helpers for matching hierarchical permission strings.

    A permission is a colon-separated path (``memory:read``). A granted
    permission matches a requested permission when:

    * it is the global wildcard ``*``; or
    * it equals the requested permission exactly; or
    * it is a prefix wildcard (``memory:*``) covering the request; or
    * it is a parent namespace of the request (``memory`` covers
      ``memory:read``).
    """

    WILDCARD = "*"
    SEP = ":"

    @staticmethod
    def matches(granted: str, requested: str) -> bool:
        """Return ``True`` if ``granted`` authorizes ``requested``.

        Args:
            granted: A permission held by the role.
            requested: The permission being checked.

        Returns:
            Whether the granted permission covers the requested one.
        """
        if granted == Permission.WILDCARD:
            return True
        if granted == requested:
            return True

        granted_parts = granted.split(Permission.SEP)
        requested_parts = requested.split(Permission.SEP)

        # A granted permission can never cover a shorter request than
        # itself (e.g. "memory:read" does not cover "memory").
        if len(granted_parts) > len(requested_parts):
            return False

        for g, r in zip(granted_parts, requested_parts):
            if g == Permission.WILDCARD:
                # Trailing wildcard: covers everything deeper.
                return True
            if g != r:
                return False

        # Every granted segment matched a requested segment. If the
        # request is deeper, the granted permission acts as a parent
        # namespace and still covers it.
        return True


@dataclass(frozen=True)
class Role:
    """A named role holding a set of permission strings.

    Attributes:
        name: Human-readable role name.
        permissions: The permission strings granted to this role.
    """

    name: str
    permissions: frozenset[str] = field(default_factory=frozenset)

    def grants(self, permission: str) -> bool:
        """Return ``True`` if any held permission covers ``permission``."""
        return any(
            Permission.matches(granted, permission)
            for granted in self.permissions
        )


# Default role definitions, taken verbatim from spec section 10.
DEFAULT_ROLES: dict[str, Role] = {
    "admin": Role("admin", frozenset({"*"})),
    "user": Role(
        "user",
        frozenset(
            {
                "chat",
                "memory:read",
                "memory:write",
                "skills:read",
                "tools:safe",
            }
        ),
    ),
    "read_only": Role(
        "read_only",
        frozenset({"chat", "memory:read", "skills:read"}),
    ),
    "service": Role("service", frozenset({"api:webhook"})),
}


@dataclass(frozen=True)
class ToolRule:
    """Permission rule for a single tool (spec section 10).

    Attributes:
        requires_role: Roles permitted to invoke the tool. An empty set
            means any known role may invoke it.
        confirmation: Whether the tool requires explicit user
            confirmation before execution.
    """

    requires_role: frozenset[str] = field(default_factory=frozenset)
    confirmation: bool = False


# Default per-tool rules. Mirrors the ``tools:`` block of spec section 10.
# Note: the spec lists a "devops" role for kubectl; it is not one of the
# four default roles, but tool rules are matched by name so a deployment
# that defines a custom "devops" role works without code changes.
DEFAULT_TOOL_RULES: dict[str, ToolRule] = {
    "kubectl": ToolRule(frozenset({"admin", "devops"}), confirmation=True),
    "shell_exec": ToolRule(frozenset({"user", "admin"}), confirmation=True),
}


class RBAC:
    """Role-based access control engine.

    Combines a role table with a per-tool rule table and answers two
    questions: whether a role holds a permission, and whether a role may
    invoke a named tool.
    """

    def __init__(
        self,
        roles: dict[str, Role] | None = None,
        tool_rules: dict[str, ToolRule] | None = None,
    ) -> None:
        """Build an RBAC engine.

        Args:
            roles: Role table. Defaults to a copy of ``DEFAULT_ROLES``.
            tool_rules: Per-tool rules. Defaults to a copy of
                ``DEFAULT_TOOL_RULES``.
        """
        self.roles: dict[str, Role] = (
            dict(DEFAULT_ROLES) if roles is None else dict(roles)
        )
        self.tool_rules: dict[str, ToolRule] = (
            dict(DEFAULT_TOOL_RULES)
            if tool_rules is None
            else dict(tool_rules)
        )

    def add_role(self, role: Role) -> None:
        """Register or replace a role in the engine."""
        self.roles[role.name] = role

    def set_tool_rule(self, tool_name: str, rule: ToolRule) -> None:
        """Register or replace the rule for a tool."""
        self.tool_rules[tool_name] = rule

    def can(self, role: str, permission: str) -> bool:
        """Return ``True`` if ``role`` holds ``permission``.

        Args:
            role: Name of the role to check.
            permission: The hierarchical permission string requested.

        Returns:
            Whether the role is known and grants the permission.
        """
        role_obj = self.roles.get(role)
        if role_obj is None:
            return False
        return role_obj.grants(permission)

    def tool_allowed(self, role: str, tool_name: str) -> bool:
        """Return ``True`` if ``role`` may invoke ``tool_name``.

        A tool with a rule is allowed only when the role appears in the
        rule's ``requires_role`` set (or that set is empty). A tool with
        no rule is allowed for any known role.

        Args:
            role: Name of the role to check.
            tool_name: Name of the tool being invoked.

        Returns:
            Whether the role may invoke the tool.
        """
        if role not in self.roles:
            return False
        rule = self.tool_rules.get(tool_name)
        if rule is None:
            # Unrestricted tool: any known role may use it.
            return True
        if not rule.requires_role:
            return True
        return role in rule.requires_role

    def tool_needs_confirmation(self, tool_name: str) -> bool:
        """Return ``True`` if invoking ``tool_name`` requires confirmation."""
        rule = self.tool_rules.get(tool_name)
        return bool(rule and rule.confirmation)


__all__ = [
    "Permission",
    "Role",
    "ToolRule",
    "RBAC",
    "DEFAULT_ROLES",
    "DEFAULT_TOOL_RULES",
]
