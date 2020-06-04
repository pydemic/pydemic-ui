import gettext
import importlib
import locale
import os
import sys
import time
from functools import lru_cache
from gettext import gettext as _
from pathlib import Path

import streamlit as st

LOCALEDIR = Path(__file__).parent.parent / "locale"
BASEDIR = Path(__file__).parent.parent
PYDEMIC_MODULES = ("pydemic_ui", "pydemic")


@lru_cache(1)
def APP_LIST():
    return {
        None: _("Do not run anything"),
        "calc": _("Main epidemic calculator"),
        "api_explorer": _("Pydemic-UI API explorer"),
        "projections": _("Epidemic projections and forecast"),
        "scenarios1": _("Epidemic scenarios (I)"),
        "scenarios2": _("Epidemic scenarios (II)"),
        "model_info": _("Model info"),
        "forecast": _("Forecast"),
        "playground": _("Playground"),
    }


def select_app(where=st, exclude=(), force_reload=False, **kwargs):
    """
    A simple menu that selects the desired app and run it.
    """

    apps = APP_LIST()
    if exclude:
        apps = {k: v for k, v in apps.items() if k not in exclude}
    if force_reload:
        apps["force_reload"] = _("Force reload of all python modules")

    msg = _("Which app do you want to run?")
    app = where.selectbox(msg, list(apps), format_func=apps.get)

    if app == "force_reload":
        for mod in PYDEMIC_MODULES:
            clear_module(mod, verbose=True)
        where.info(_("Done!"))
    elif app:
        mod_path = f"pydemic_ui.apps.{app}"
        if force_reload:
            sys.modules.pop(mod_path, None)
            if st.button(_("Force reload")):
                for mod in PYDEMIC_MODULES:
                    clear_module(mod, True)

        mod = importlib.import_module(mod_path)
        main = getattr(mod, "main")
        main(**kwargs)

    else:
        silly_animation(_("Doing nothing..."))


def silly_animation(text):
    """
    A silly progressbar animation.
    """

    step = 10
    bar = st.progress(0)
    i = 0
    incr = step
    st.title(text)

    while True:
        time.sleep(0.1)
        i = i + incr
        if i >= 100:
            incr = -step // 2
        if i <= 0:
            incr = step
        bar.progress(i)


def clear_module(mod: str, verbose=False):
    """
    Remove references to module from sys.modules.
    """

    empty = st.empty() if verbose else None
    if verbose:
        empty.info(_("Unloading module: {mod}").format(mod=mod))
        time.sleep(0.1)

    prefix = mod + "."
    i = 0

    for name in list(sys.modules):
        if name == mod or name.startswith(prefix):
            i += 1
            del sys.modules[name]
            if verbose and i % 5 == 0:
                empty.info(name)
                time.sleep(0.01)

    if verbose:
        empty.empty()


def configure_i18n():
    """
    Configure locale and translations.
    """

    lang = os.environ.get("PYDEMIC_LANG") or os.environ.get("LANG")
    locale.setlocale(locale.LC_ALL, lang)
    locale.setlocale(locale.LC_MESSAGES, lang)
    os.environ["LANG"] = lang
    os.environ["LANGUAGE"] = lang.split(".")[0]
    gettext.bindtextdomain("messages", localedir=LOCALEDIR)


def patch_builtins():
    """
    Add some helper functions to builtins for quick and dirt debugging and app
    development.
    """

    with open(BASEDIR / "builtins.py") as fd:
        code = fd.read()
        ns = {"__name__": "builtins_patch"}
        exec(code, ns)
        ns["main"]()


if __name__ == "__main__":
    configure_i18n()
    patch_builtins()
    select_app(force_reload=True)
