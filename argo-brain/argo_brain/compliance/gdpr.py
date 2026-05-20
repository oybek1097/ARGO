"""EU General Data Protection Regulation module (spec section 4.14).

Implements the data-protection requirements of Regulation (EU) 2016/679
(GDPR). In addition to the common compliance fields, GDPR introduces two
data-subject rights tracked explicitly here: the right to erasure
("right to be forgotten", Article 17) and the right to data portability
(Article 20).
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import ComplianceModule

# GDPR does not fix a single universal retention period; processing
# records and audit trails are commonly retained for six years to cover
# limitation periods. Expressed here in days (6 * 365).
_RETENTION_DAYS = 2190


@dataclass
class GDPR(ComplianceModule):
    """EU General Data Protection Regulation compliance module.

    Personal data resides within the EU ("eu"). The two extra flags
    record that the data-subject rights to erasure and portability are
    supported by this regime.

    Attributes:
        right_to_erasure: Whether the GDPR right to erasure (Art. 17) is
            honored.
        data_portability: Whether the GDPR right to data portability
            (Art. 20) is honored.
    """

    name: str = "GDPR"
    data_residency: str = "eu"
    audit_retention_days: int = _RETENTION_DAYS
    description: str = (
        "EU General Data Protection Regulation (Regulation (EU) 2016/679): "
        "protects the personal data of individuals within the EU/EEA."
    )
    right_to_erasure: bool = True
    data_portability: bool = True
