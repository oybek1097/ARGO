"""China Personal Information Protection Law module (spec section 4.14).

Implements the data-protection requirements of the People's Republic of
China Personal Information Protection Law (PIPL), effective 2021. PIPL
requires that personal information collected and generated within China
be stored domestically, with cross-border transfers subject to a
security assessment.
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ComplianceModule

# PIPL and the related Cybersecurity Law require personal-information
# processing logs to be retained for at least three years; expressed
# here in days (3 * 365).
_RETENTION_DAYS = 1095


@dataclass
class CNPIPL(ComplianceModule):
    """China Personal Information Protection Law (PIPL) compliance module.

    Personal information must reside in China ("cn") and processing logs
    are retained for three years.
    """

    name: str = "CN-PIPL"
    data_residency: str = "cn"
    audit_retention_days: int = _RETENTION_DAYS
    description: str = (
        "China Personal Information Protection Law (PIPL): personal "
        "information collected within China must be stored domestically, "
        "and cross-border transfers require a security assessment."
    )
