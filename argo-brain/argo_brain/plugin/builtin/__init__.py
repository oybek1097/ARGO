"""Built-in ARGO plugins — spec section 4.6.

Exposes the three ship-by-default general plugins and a `builtin_plugins`
factory that instantiates a fresh set of them.
"""

from __future__ import annotations

from argo_brain.plugin.api import ArgoPlugin
from argo_brain.plugin.builtin.audit import SecurityAuditPlugin
from argo_brain.plugin.builtin.language_enforcer import LanguageEnforcerPlugin
from argo_brain.plugin.builtin.pii_redactor import PIIRedactorPlugin

__all__ = [
    "SecurityAuditPlugin",
    "LanguageEnforcerPlugin",
    "PIIRedactorPlugin",
    "builtin_plugins",
]


def builtin_plugins() -> list[ArgoPlugin]:
    """Return a fresh list of the built-in plugin instances."""
    return [
        SecurityAuditPlugin(),
        LanguageEnforcerPlugin(),
        PIIRedactorPlugin(),
    ]
