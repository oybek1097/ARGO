"""Security subsystem for the ARGO Agent.

Provides PII redaction and an append-only audit log
(spec sections 4.1, 4.14 and 10).
"""

from argo_brain.security.audit import AuditLog
from argo_brain.security.redaction import PIIRedactor

__all__ = ["PIIRedactor", "AuditLog"]
