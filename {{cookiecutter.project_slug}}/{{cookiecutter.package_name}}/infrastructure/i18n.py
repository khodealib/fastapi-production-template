"""Minimal gettext-based i18n (mirrors Django's i18n machinery).

Compile catalogs with ``make messages`` (needs Babel). Uncompiled locales
fall back to ``gettext.NullTranslations``, so the app runs safely either way.
"""

from __future__ import annotations

import gettext
from contextvars import ContextVar
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent.parent / "locales"

current_locale: ContextVar[str] = ContextVar("current_locale", default="en")

_translations: dict[str, gettext.NullTranslations] = {}


def _get_translations(locale: str) -> gettext.NullTranslations:
    if locale not in _translations:
        try:
            _translations[locale] = gettext.translation(
                "messages",
                localedir=str(LOCALES_DIR),
                languages=[locale],
                fallback=False,
            )
        except FileNotFoundError:
            _translations[locale] = gettext.NullTranslations()
    return _translations[locale]


def set_locale(locale: str) -> None:
    current_locale.set(locale)


def tr(message: str) -> str:
    """Translate ``message`` for the request-bound locale."""
    return _get_translations(current_locale.get()).gettext(message)


def pick_locale(accepted: str, default: str) -> str:
    """Resolve an Accept-Language header against compiled locales."""
    for lang in accepted.split(","):  # e.g. "fr-FR,fr;q=0.9,en;q=0.8"
        code = lang.split(";")[0].strip().split("-")[0].lower()
        if (LOCALES_DIR / code / "LC_MESSAGES" / "messages.mo").exists():
            return code
    return default
