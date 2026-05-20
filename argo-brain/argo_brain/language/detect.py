"""Fast language detection (heuristic).

Skeleton stage: a character-range and stop-word heuristic instead of an
external `langdetect`/`fasttext`. Central Asian languages get first-class
attention: Uzbek (uz), Kazakh (kk), Kyrgyz (ky), Tajik (tg), as well as
Russian (ru) and English (en).

In Sprint 3 this will be replaced with a real model — the `detect()`
signature stays the same.
"""

from __future__ import annotations

import re

# Stop-words for Latin-script languages
_UZ_WORDS = {
    "va", "bilan", "uchun", "men", "sen", "biz", "bu", "shu", "qanday",
    "salom", "rahmat", "qiladi", "bo'ldi", "boldi", "yaxshi", "kerak", "yoq",
}
_EN_WORDS = {
    "the", "and", "for", "you", "this", "that", "with", "what", "have",
    "hello", "thanks", "please", "good", "need", "is", "are",
}
# Stop-words for Cyrillic-script languages
_RU_WORDS = {
    "и", "не", "что", "это", "как", "привет", "спасибо", "хорошо",
    "нужно", "да", "нет", "вы", "мы",
}
_KK_WORDS = {"және", "бұл", "сәлем", "рахмет", "қалай", "керек", "жоқ", "иә"}
_KY_WORDS = {"жана", "бул", "салам", "рахмат", "кандай", "керек", "жок", "ооба"}
_TG_WORDS = {"ва", "ин", "салом", "ташаккур", "чӣ", "лозим", "не", "ҳа"}

# Characters unique to a specific language
_KK_CHARS = set("әғқңөұүһі")
_KY_CHARS = set("ңүөһ")
_TG_CHARS = set("ҷҳқғӯӣ")
_UZ_LATIN_MARKERS = ("o'", "g'", "oʻ", "gʻ", "o`", "g`")


def _has_cyrillic(text: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in text)


# Split words without punctuation (an apostrophe inside a word is kept)
_WORD_RE = re.compile(r"[^\W\d_]+(?:['ʻ`][^\W\d_]+)*", re.UNICODE)


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text))


def detect(text: str, default: str = "en") -> str:
    """Returns the ISO 639-1 code of the text's language (uz, ru, kk, ky, tg, en)."""
    if not text or not text.strip():
        return default

    low = text.lower()
    words = _tokenize(low)

    if _has_cyrillic(low):
        chars = set(low)
        # Central Asian Cyrillic languages — scored by unique characters
        scores = {
            "kk": len(chars & _KK_CHARS) * 3 + len(words & _KK_WORDS) * 2,
            "ky": len(chars & _KY_CHARS) * 3 + len(words & _KY_WORDS) * 2,
            "tg": len(chars & _TG_CHARS) * 3 + len(words & _TG_WORDS) * 2,
            "ru": len(words & _RU_WORDS) * 2,
        }
        best = max(scores, key=lambda k: scores[k])
        return best if scores[best] > 0 else "ru"

    # Latin script: Uzbek vs English
    uz_score = len(words & _UZ_WORDS) * 2
    uz_score += sum(low.count(m) for m in _UZ_LATIN_MARKERS) * 2
    en_score = len(words & _EN_WORDS) * 2

    if uz_score > en_score:
        return "uz"
    if en_score > 0:
        return "en"
    return default
