"""Tests for the compliance subsystem (spec section 4.14)."""

from __future__ import annotations

import unittest

from argo_brain.compliance import (
    CNPIPL,
    GDPR,
    RU152,
    UZ152,
    ComplianceModule,
    available_modules,
    get_module,
)


class TestUZ152(unittest.TestCase):
    """Tests for the Uzbekistan Personal Data Law module."""

    def test_data_residency_and_retention(self):
        module = UZ152()
        self.assertEqual(module.data_residency, "uz")
        # Five years expressed in days.
        self.assertEqual(module.audit_retention_days, 1825)

    def test_check_data_residency_accepts_uz(self):
        module = UZ152()
        self.assertTrue(module.check_data_residency("uz"))
        # Comparison is case-insensitive.
        self.assertTrue(module.check_data_residency("UZ"))

    def test_check_data_residency_rejects_others(self):
        module = UZ152()
        self.assertFalse(module.check_data_residency("ru"))
        self.assertFalse(module.check_data_residency("eu"))
        self.assertFalse(module.check_data_residency(""))

    def test_summary(self):
        summary = UZ152().summary()
        self.assertEqual(summary["name"], "UZ-152")
        self.assertEqual(summary["data_residency"], "uz")
        self.assertEqual(summary["audit_retention_days"], 1825)
        self.assertIn("description", summary)


class TestRU152(unittest.TestCase):
    """Tests for the Russia 152-FZ module."""

    def test_data_residency_and_retention(self):
        module = RU152()
        self.assertEqual(module.data_residency, "ru")
        self.assertEqual(module.audit_retention_days, 1825)

    def test_check_data_residency(self):
        module = RU152()
        self.assertTrue(module.check_data_residency("ru"))
        self.assertFalse(module.check_data_residency("uz"))
        self.assertFalse(module.check_data_residency("cn"))

    def test_summary(self):
        summary = RU152().summary()
        self.assertEqual(summary["data_residency"], "ru")
        self.assertEqual(summary["audit_retention_days"], 1825)


class TestGDPR(unittest.TestCase):
    """Tests for the EU GDPR module."""

    def test_data_residency(self):
        module = GDPR()
        self.assertEqual(module.data_residency, "eu")

    def test_extra_flags(self):
        module = GDPR()
        # GDPR-specific data-subject rights.
        self.assertTrue(module.right_to_erasure)
        self.assertTrue(module.data_portability)

    def test_check_data_residency(self):
        module = GDPR()
        self.assertTrue(module.check_data_residency("eu"))
        self.assertFalse(module.check_data_residency("us"))

    def test_summary_includes_flags(self):
        summary = GDPR().summary()
        self.assertEqual(summary["data_residency"], "eu")
        self.assertTrue(summary["right_to_erasure"])
        self.assertTrue(summary["data_portability"])


class TestCNPIPL(unittest.TestCase):
    """Tests for the China PIPL module."""

    def test_data_residency(self):
        module = CNPIPL()
        self.assertEqual(module.data_residency, "cn")

    def test_check_data_residency(self):
        module = CNPIPL()
        self.assertTrue(module.check_data_residency("cn"))
        self.assertFalse(module.check_data_residency("eu"))

    def test_summary(self):
        summary = CNPIPL().summary()
        self.assertEqual(summary["name"], "CN-PIPL")
        self.assertEqual(summary["data_residency"], "cn")
        self.assertGreater(summary["audit_retention_days"], 0)


class TestRegistry(unittest.TestCase):
    """Tests for the get_module registry lookup."""

    def test_get_module_returns_right_class(self):
        self.assertIsInstance(get_module("UZ-152"), UZ152)
        self.assertIsInstance(get_module("RU-152-FZ"), RU152)
        self.assertIsInstance(get_module("GDPR"), GDPR)
        self.assertIsInstance(get_module("CN-PIPL"), CNPIPL)

    def test_get_module_is_case_and_punctuation_insensitive(self):
        # All of these should resolve to the UZ-152 module.
        for alias in ("uz152", "uz_152", "UZ152", "uz-152"):
            self.assertIsInstance(get_module(alias), UZ152)

    def test_get_module_unknown_raises_keyerror(self):
        with self.assertRaises(KeyError):
            get_module("does-not-exist")
        with self.assertRaises(KeyError):
            get_module("")

    def test_available_modules(self):
        names = available_modules()
        self.assertIn("UZ-152", names)
        self.assertIn("GDPR", names)
        self.assertEqual(len(names), 4)


class TestBase(unittest.TestCase):
    """Tests for the ComplianceModule base behavior."""

    def test_all_modules_subclass_base(self):
        for cls in (UZ152, RU152, GDPR, CNPIPL):
            self.assertTrue(issubclass(cls, ComplianceModule))
            self.assertIsInstance(cls(), ComplianceModule)

    def test_summary_returns_dict_with_core_fields(self):
        for cls in (UZ152, RU152, GDPR, CNPIPL):
            summary = cls().summary()
            self.assertIsInstance(summary, dict)
            for key in ("name", "data_residency", "audit_retention_days",
                        "description"):
                self.assertIn(key, summary)


if __name__ == "__main__":
    unittest.main()
