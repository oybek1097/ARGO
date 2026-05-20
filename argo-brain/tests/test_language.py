"""Language detection tests."""

import unittest

from argo_brain.language import detect


class TestLanguageDetect(unittest.TestCase):
    def test_uzbek_latin(self):
        self.assertEqual(detect("Salom, men bilan ishlash uchun"), "uz")

    def test_uzbek_markers(self):
        self.assertEqual(detect("oʻzbek tili gʻoyat goʻzal"), "uz")

    def test_english(self):
        self.assertEqual(detect("hello, what is this for you"), "en")

    def test_russian(self):
        self.assertEqual(detect("привет, что это такое"), "ru")

    def test_kazakh(self):
        self.assertEqual(detect("сәлем, бұл қалай және керек"), "kk")

    def test_empty_returns_default(self):
        self.assertEqual(detect(""), "en")
        self.assertEqual(detect("   ", default="uz"), "uz")


if __name__ == "__main__":
    unittest.main()
