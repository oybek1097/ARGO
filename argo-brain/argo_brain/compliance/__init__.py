"""Compliance subsystem (spec section 4.14).

Exposes the `ComplianceModule` base class, the four concrete regulatory
regimes (UZ-152, RU 152-FZ, GDPR, China PIPL) and the `get_module`
registry lookup helper.
"""

from __future__ import annotations

from .base import ComplianceModule, available_modules, get_module
from .cn_pipl import CNPIPL
from .gdpr import GDPR
from .ru_152 import RU152
from .uz_152 import UZ152

__all__ = [
    "ComplianceModule",
    "UZ152",
    "RU152",
    "GDPR",
    "CNPIPL",
    "get_module",
    "available_modules",
]
