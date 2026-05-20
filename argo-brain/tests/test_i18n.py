"""Unit tests for the ARGO Agent i18n subsystem."""

from __future__ import annotations

import unittest

from argo_brain.i18n import LANGUAGE_PACKS, Translator, available_locales, t

_SUPPORTED = {"en", "ru", "uz", "kk", "ky", "tg", "tr"}


class TestTranslatorGet(unittest.TestCase):
    def setUp(self) -> None:
        self.tr = Translator()

    def test_get_returns_locale_string(self) -> None:
        self.assertEqual(self.tr.get("yes", "ru"), "Да")
        self.assertEqual(self.tr.get("yes", "uz"), "Ha")
        self.assertEqual(self.tr.get("yes", "tr"), "Evet")

    def test_get_english_default(self) -> None:
        self.assertEqual(self.tr.get("thanks"), "Thank you")

    def test_param_formatting(self) -> None:
        self.assertEqual(
            self.tr.get("greeting", "en", name="Akbar"), "Hello, Akbar!"
        )
        self.assertEqual(
            self.tr.get("greeting", "uz", name="Akbar"), "Salom, Akbar!"
        )

    def test_param_formatting_in_cyrillic_locale(self) -> None:
        self.assertEqual(
            self.tr.get("error.not_found", "ru", item="файл"),
            "Не найдено: файл",
        )

    def test_unknown_locale_falls_back_to_english(self) -> None:
        # 'de' is not a supported locale; should yield the English string.
        self.assertEqual(self.tr.get("farewell", "de"), "Goodbye!")
        self.assertEqual(
            self.tr.get("greeting", "zz", name="X"), "Hello, X!"
        )

    def test_unknown_key_falls_back_to_key(self) -> None:
        self.assertEqual(self.tr.get("no.such.key", "ru"), "no.such.key")

    def test_missing_param_does_not_raise(self) -> None:
        # No 'name' passed -> returns the unformatted message rather than error.
        result = self.tr.get("greeting", "en")
        self.assertIn("{name}", result)

    def test_all_keys_translated_into_all_locales(self) -> None:
        for key in [
            "greeting", "farewell", "yes", "no", "thanks",
            "error.not_found", "tool.running", "task.created",
        ]:
            for loc in _SUPPORTED:
                msg = self.tr.get(key, loc)
                self.assertTrue(msg)
                self.assertNotEqual(msg, key, f"{key}/{loc} missing")


class TestConvenienceHelpers(unittest.TestCase):
    def test_t_convenience(self) -> None:
        self.assertEqual(t("yes", "kk"), "Иә")
        self.assertEqual(t("greeting", "tr", name="Aziz"), "Merhaba, Aziz!")

    def test_t_default_locale_english(self) -> None:
        self.assertEqual(t("no"), "No")

    def test_available_locales_lists_all(self) -> None:
        locales = available_locales()
        self.assertEqual(set(locales), _SUPPORTED)
        self.assertEqual(locales, sorted(locales))

    def test_available_locales_count(self) -> None:
        self.assertEqual(len(available_locales()), 7)


class TestLanguagePacks(unittest.TestCase):
    def test_has_five_central_asian_languages(self) -> None:
        self.assertEqual(set(LANGUAGE_PACKS), {"uz", "kk", "ky", "tg", "tk"})

    def test_metadata_fields_present(self) -> None:
        for code, pack in LANGUAGE_PACKS.items():
            for field in ("name", "native_name", "script", "iso"):
                self.assertIn(field, pack, f"{code} missing {field}")
            self.assertEqual(pack["iso"], code)

    def test_uzbek_metadata(self) -> None:
        uz = LANGUAGE_PACKS["uz"]
        self.assertEqual(uz["name"], "Uzbek")
        self.assertEqual(uz["script"], "Latin")
        self.assertEqual(uz["native_name"], "O'zbekcha")

    def test_kazakh_is_cyrillic(self) -> None:
        self.assertEqual(LANGUAGE_PACKS["kk"]["script"], "Cyrillic")
        self.assertEqual(LANGUAGE_PACKS["kk"]["native_name"], "Қазақша")

    def test_scripts_are_valid(self) -> None:
        for pack in LANGUAGE_PACKS.values():
            self.assertIn(pack["script"], ("Latin", "Cyrillic"))


if __name__ == "__main__":
    unittest.main()
