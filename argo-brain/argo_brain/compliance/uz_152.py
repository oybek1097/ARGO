"""Uzbekistan Personal Data Law compliance module (spec section 4.14).

Implements the requirements of Uzbekistan's Law "On Personal Data"
(No. ZRU-547), commonly referred to as UZ-152. The law requires that
personal data of Uzbek citizens be stored and processed on databases
physically located inside Uzbekistan.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ComplianceModule

# Audit retention period mandated for personal-data processing records:
# five years, expressed in days (5 * 365).
_RETENTION_DAYS = 1825


@dataclass
class UZ152(ComplianceModule):
    """Uzbekistan Personal Data Law (UZ-152) compliance module.

    Personal data must reside in Uzbekistan ("uz") and audit records are
    retained for five years.
    """

    name: str = "UZ-152"
    data_residency: str = "uz"
    audit_retention_days: int = _RETENTION_DAYS
    description: str = (
        "Uzbekistan Personal Data Law (ZRU-547): personal data of Uzbek "
        "citizens must be stored on servers located within Uzbekistan."
    )
