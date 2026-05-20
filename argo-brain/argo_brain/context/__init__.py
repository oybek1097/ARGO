"""Context-file subsystem (spec section 4.2 - context files and @ references).

Provides discovery and assembly of ARGO context files (MEMORY.md, USER.md,
AGENTS.md, .argo.md) and expansion of ``@`` references embedded in text.
"""

from argo_brain.context.loader import ContextLoader, expand_refs

__all__ = ["ContextLoader", "expand_refs"]
