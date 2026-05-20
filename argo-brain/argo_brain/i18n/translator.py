"""In-code translation catalogue for the ARGO Agent UI.

Provides a small, dependency-free i18n subsystem with a Central Asian
focus. The supported UI locales are:

    en  English
    ru  Russian
    uz  Uzbek
    kk  Kazakh
    ky  Kyrgyz
    tg  Tajik
    tr  Turkish

Lookups fall back to English, and then to the message key itself, so a
missing translation never raises.
"""

from __future__ import annotations

# Default locale used as the fallback for every lookup.
DEFAULT_LOCALE = "en"

# Message catalogue: message-key -> { locale -> string }.
# Every key is translated into all 7 supported locales. Strings may carry
# ``{name}`` style placeholders filled in by ``str.format``.
_CATALOGUE: dict[str, dict[str, str]] = {
    "greeting": {
        "en": "Hello, {name}!",
        "ru": "Здравствуйте, {name}!",
        "uz": "Salom, {name}!",
        "kk": "Сәлем, {name}!",
        "ky": "Салам, {name}!",
        "tg": "Салом, {name}!",
        "tr": "Merhaba, {name}!",
    },
    "farewell": {
        "en": "Goodbye!",
        "ru": "До свидания!",
        "uz": "Xayr!",
        "kk": "Сау болыңыз!",
        "ky": "Жакшы калыңыз!",
        "tg": "Хайр!",
        "tr": "Hoşça kalın!",
    },
    "yes": {
        "en": "Yes",
        "ru": "Да",
        "uz": "Ha",
        "kk": "Иә",
        "ky": "Ооба",
        "tg": "Ҳа",
        "tr": "Evet",
    },
    "no": {
        "en": "No",
        "ru": "Нет",
        "uz": "Yo'q",
        "kk": "Жоқ",
        "ky": "Жок",
        "tg": "Не",
        "tr": "Hayır",
    },
    "thanks": {
        "en": "Thank you",
        "ru": "Спасибо",
        "uz": "Rahmat",
        "kk": "Рахмет",
        "ky": "Рахмат",
        "tg": "Ташаккур",
        "tr": "Teşekkürler",
    },
    "error.not_found": {
        "en": "Not found: {item}",
        "ru": "Не найдено: {item}",
        "uz": "Topilmadi: {item}",
        "kk": "Табылмады: {item}",
        "ky": "Табылган жок: {item}",
        "tg": "Ёфт нашуд: {item}",
        "tr": "Bulunamadı: {item}",
    },
    "error.permission_denied": {
        "en": "Permission denied",
        "ru": "Доступ запрещён",
        "uz": "Ruxsat berilmadi",
        "kk": "Рұқсат жоқ",
        "ky": "Уруксат жок",
        "tg": "Иҷозат дода нашуд",
        "tr": "İzin reddedildi",
    },
    "error.timeout": {
        "en": "Operation timed out",
        "ru": "Время операции истекло",
        "uz": "Amal vaqti tugadi",
        "kk": "Операция уақыты бітті",
        "ky": "Операциянын убакыты бүттү",
        "tg": "Вақти амалиёт ба охир расид",
        "tr": "İşlem zaman aşımına uğradı",
    },
    "tool.running": {
        "en": "Running tool: {tool}",
        "ru": "Выполняется инструмент: {tool}",
        "uz": "Vosita ishlamoqda: {tool}",
        "kk": "Құрал орындалуда: {tool}",
        "ky": "Курал иштеп жатат: {tool}",
        "tg": "Абзор иҷро мешавад: {tool}",
        "tr": "Araç çalışıyor: {tool}",
    },
    "tool.done": {
        "en": "Tool finished: {tool}",
        "ru": "Инструмент завершён: {tool}",
        "uz": "Vosita tugadi: {tool}",
        "kk": "Құрал аяқталды: {tool}",
        "ky": "Курал бүттү: {tool}",
        "tg": "Абзор ба охир расид: {tool}",
        "tr": "Araç tamamlandı: {tool}",
    },
    "task.created": {
        "en": "Task created: {title}",
        "ru": "Задача создана: {title}",
        "uz": "Vazifa yaratildi: {title}",
        "kk": "Тапсырма жасалды: {title}",
        "ky": "Тапшырма түзүлдү: {title}",
        "tg": "Вазифа сохта шуд: {title}",
        "tr": "Görev oluşturuldu: {title}",
    },
    "confirm.prompt": {
        "en": "Are you sure?",
        "ru": "Вы уверены?",
        "uz": "Ishonchingiz komilmi?",
        "kk": "Сенімдісіз бе?",
        "ky": "Ишенесизби?",
        "tg": "Шумо боварӣ доред?",
        "tr": "Emin misiniz?",
    },
}

# Metadata describing the Central Asian language packs. The ``script``
# field records whether the language is written here in the Latin or
# Cyrillic alphabet.
LANGUAGE_PACKS: dict[str, dict[str, str]] = {
    "uz": {
        "name": "Uzbek",
        "native_name": "O'zbekcha",
        "script": "Latin",
        "iso": "uz",
    },
    "kk": {
        "name": "Kazakh",
        "native_name": "Қазақша",
        "script": "Cyrillic",
        "iso": "kk",
    },
    "ky": {
        "name": "Kyrgyz",
        "native_name": "Кыргызча",
        "script": "Cyrillic",
        "iso": "ky",
    },
    "tg": {
        "name": "Tajik",
        "native_name": "Тоҷикӣ",
        "script": "Cyrillic",
        "iso": "tg",
    },
    "tk": {
        "name": "Turkmen",
        "native_name": "Türkmençe",
        "script": "Latin",
        "iso": "tk",
    },
}


class Translator:
    """Looks up and formats UI messages from the in-code catalogue."""

    def __init__(self, catalogue: dict[str, dict[str, str]] | None = None) -> None:
        # A custom catalogue may be injected, mainly for testing.
        self._catalogue = catalogue if catalogue is not None else _CATALOGUE

    def get(self, key: str, locale: str = DEFAULT_LOCALE, **params: object) -> str:
        """Return the message ``key`` for ``locale``, formatted with ``params``.

        Resolution order:
          1. the requested locale,
          2. English (``DEFAULT_LOCALE``),
          3. the raw message key itself.

        Parameter formatting uses ``str.format``; missing placeholders are
        tolerated so a bad call never raises.
        """
        translations = self._catalogue.get(key)
        if translations is None:
            # Unknown key: return the key so the caller still sees something.
            return key

        # Prefer the requested locale, otherwise fall back to English.
        message = translations.get(locale)
        if message is None:
            message = translations.get(DEFAULT_LOCALE, key)

        if not params:
            return message
        try:
            return message.format(**params)
        except (KeyError, IndexError):
            # A placeholder had no matching param; return the unformatted text.
            return message

    def available_locales(self) -> list[str]:
        """Return the sorted list of locales present in the catalogue."""
        locales: set[str] = set()
        for translations in self._catalogue.values():
            locales.update(translations.keys())
        return sorted(locales)


# A shared default Translator instance backing the module-level helpers.
_DEFAULT_TRANSLATOR = Translator()


def t(key: str, locale: str = DEFAULT_LOCALE, **params: object) -> str:
    """Module-level convenience wrapper around ``Translator.get``."""
    return _DEFAULT_TRANSLATOR.get(key, locale, **params)


def available_locales() -> list[str]:
    """Return the sorted list of supported UI locales."""
    return _DEFAULT_TRANSLATOR.available_locales()
