"""Compliance module base class and registry (spec section 4.14).

A `ComplianceModule` captures the data-protection requirements of a
particular jurisdiction or regulatory regime: where personal data may be
stored (data residency) and how long audit records must be retained.
Concrete regimes (UZ-152, RU 152-FZ, GDPR, China PIPL) subclass this base
class and supply their specific settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass
class ComplianceModule:
    """Base description of a data-protection compliance regime.

    Attributes:
        name: Short identifier of the regime (e.g. "UZ-152").
        data_residency: Region code where personal data must reside
            (e.g. "uz", "ru", "eu", "cn").
        audit_retention_days: Number of days audit records must be kept.
        description: Human-readable description of the regime.
    """

    name: str
    data_residency: str
    audit_retention_days: int
    description: str = ""

    def check_data_residency(self, region: str) -> bool:
        """Return whether `region` satisfies this regime's residency rule.

        The comparison is case-insensitive so callers may pass region
        codes in any casing.

        Args:
            region: Region code to validate (e.g. "uz", "EU").

        Returns:
            True if `region` matches the required `data_residency`,
            False otherwise.
        """
        if not region:
            return False
        return region.strip().lower() == self.data_residency.lower()

    def summary(self) -> dict:
        """Return a serializable summary of this compliance module.

        Returns:
            A dictionary of every dataclass field, suitable for logging
            or inclusion in an API response.
        """
        return {f.name: getattr(self, f.name) for f in fields(self)}


# Registry of known compliance modules. Populated lazily by `get_module`
# to avoid import cycles between this module and the concrete regimes.
_REGISTRY: dict[str, type[ComplianceModule]] = {}


def _build_registry() -> dict[str, type[ComplianceModule]]:
    """Build (and memoize) the name -> module-class registry.

    Imports of the concrete regimes are deferred to here so that
    `base.py` itself stays free of circular imports.
    """
    if _REGISTRY:
        return _REGISTRY

    from .cn_pipl import CNPIPL
    from .gdpr import GDPR
    from .ru_152 import RU152
    from .uz_152 import UZ152

    for cls in (UZ152, RU152, GDPR, CNPIPL):
        instance = cls()
        # Register under the canonical name and a normalized alias so
        # lookups tolerate hyphen/space/case variations.
        _REGISTRY[instance.name] = cls
        _REGISTRY[_normalize(instance.name)] = cls
    return _REGISTRY


def _normalize(name: str) -> str:
    """Normalize a module name for case/punctuation-insensitive lookup."""
    return name.strip().lower().replace("-", "").replace("_", "").replace(" ", "")


def get_module(name: str) -> ComplianceModule:
    """Return an instance of the compliance module identified by `name`.

    Lookup is tolerant of casing and of hyphen/underscore/space
    differences, so "UZ-152", "uz152" and "uz_152" all resolve to the
    same module.

    Args:
        name: Identifier of the desired compliance module.

    Returns:
        A freshly constructed `ComplianceModule` subclass instance.

    Raises:
        KeyError: If no module matches `name`.
    """
    registry = _build_registry()
    if name in registry:
        return registry[name]()
    key = _normalize(name or "")
    if key in registry:
        return registry[key]()
    raise KeyError(f"Unknown compliance module: {name!r}")


def available_modules() -> list[str]:
    """Return the canonical names of all registered compliance modules."""
    registry = _build_registry()
    # Filter out the normalized aliases by keeping names that contain a
    # hyphen or an uppercase letter (i.e. the canonical spellings).
    seen: list[str] = []
    for cls in dict.fromkeys(registry.values()):
        seen.append(cls().name)
    return seen
