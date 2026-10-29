"""Localization package for Stars Shop bot."""

from .uz import TEXTS as UZ
from .ru import TEXTS as RU
from .en import TEXTS as EN

LANGS: dict = {"uz": UZ, "ru": RU, "en": EN}
LANG_NAMES: dict = {
    "uz": "🇺🇿 O'zbek",
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
}
LANG_FLAGS: dict = {
    "uz": "🇺🇿",
    "ru": "🇷🇺",
    "en": "🇬🇧",
}


def t(lang: str, key: str, **kwargs) -> str:
    """Translate a key to the given language with optional format args."""
    text = LANGS.get(lang, UZ).get(key) or LANGS["uz"].get(key) or key
    if kwargs:
        if "amount" in kwargs and "amount_raw" not in kwargs:
            kwargs["amount_raw"] = kwargs["amount"]
        if "amount_raw" in kwargs and "amount" not in kwargs:
            kwargs["amount"] = kwargs["amount_raw"]
        if "card_number" in kwargs and "card_number_clean" not in kwargs:
            kwargs["card_number_clean"] = str(kwargs["card_number"]).replace(" ", "")
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
