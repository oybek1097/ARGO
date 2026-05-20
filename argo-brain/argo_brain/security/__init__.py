"""Security subsystem for the ARGO Agent.

Provides PII redaction, an append-only audit log, an RBAC engine and
authentication primitives (spec sections 4.1, 4.14 and 10).
"""

from argo_brain.security.audit import AuditLog
from argo_brain.security.auth import (
    AuthError,
    generate_api_key,
    hash_api_key,
    jwt_decode,
    jwt_encode,
    verify_api_key,
)
from argo_brain.security.rbac import (
    DEFAULT_ROLES,
    DEFAULT_TOOL_RULES,
    RBAC,
    Permission,
    Role,
    ToolRule,
)
from argo_brain.security.redaction import PIIRedactor

__all__ = [
    "PIIRedactor",
    "AuditLog",
    "RBAC",
    "Role",
    "Permission",
    "ToolRule",
    "DEFAULT_ROLES",
    "DEFAULT_TOOL_RULES",
    "AuthError",
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "jwt_encode",
    "jwt_decode",
]
