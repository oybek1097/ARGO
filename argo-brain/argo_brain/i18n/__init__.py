"""ARGO Agent i18n / localization subsystem.

Public API:
    Translator         -- catalogue-backed message lookup class
    t                  -- module-level convenience translation function
    available_locales  -- list of supported UI locales
    LANGUAGE_PACKS     -- metadata for the Central Asian language packs
"""

from __future__ import annotations

from argo_brain.i18n.translator import (
    LANGUAGE_PACKS,
    Translator,
    available_locales,
    t,
)

__all__ = ["Translator", "t", "available_locales", "LANGUAGE_PACKS"]
