"""Russia Federal Law 152-FZ compliance module (spec section 4.14).

Implements the requirements of the Russian Federal Law No. 152-FZ
"On Personal Data". The law requires that the personal data of Russian
citizens be recorded, stored and processed using databases located
within the Russian Federation (the "data localization" requirement).
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ComplianceModule

# 152-FZ obliges operators to retain processing/audit records for the
# duration of processing; the implementing regulations set a five-year
# minimum retention, expressed here in days (5 * 365).
_RETENTION_DAYS = 1825


@dataclass
class RU152(ComplianceModule):
    """Russia 152-FZ ("On Personal Data") compliance module.

    Personal data must reside in Russia ("ru") and audit records are
    retained for five years per the implementing regulations.
    """

    name: str = "RU-152-FZ"
    data_residency: str = "ru"
    audit_retention_days: int = _RETENTION_DAYS
    description: str = (
        "Russian Federal Law 152-FZ 'On Personal Data': personal data of "
        "Russian citizens must be stored and processed on databases "
        "located within the Russian Federation."
    )
