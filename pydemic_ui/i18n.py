from gettext import gettext
from pathlib import Path

import sidekick as sk

LOCALEDIR = Path(__file__).parent / "locale"


def set_i18n(lang, language=None):
    """
    Set locale and translations.

    Examples:
        set_i18n('pt_BR.UTF-8') -> set locale to pt_BR.UTF-8 and language to pt_BR.
    """
    import gettext
    import locale
    import warnings
    import os

    try:
        locale.setlocale(locale.LC_ALL, lang)
        locale.setlocale(locale.LC_MESSAGES, language or lang)
        os.environ["LANG"] = lang
        os.environ["LANGUAGE"] = language or lang.split(".")[0]
    except locale.Error:
        warnings.warn(f"locale is not supported: {lang}")
    gettext.bindtextdomain("messages", localedir=LOCALEDIR)


def run():
    import os

    lang = os.environ.get("PYDEMIC_LANG") or os.environ.get("LANG")
    set_i18n(lang)


def gettext_lazy(st):
    return sk.deferred(gettext, st)


_ = gettext
__ = gettext_lazy
