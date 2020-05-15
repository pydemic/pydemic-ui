import inspect
from functools import wraps, lru_cache
from pathlib import Path
from types import SimpleNamespace

import sidekick as sk
import streamlit as st


_fake_mod = SimpleNamespace(markdown=lambda x, **kwargs: x, write=lambda x, **kwargs: x)

BASE_PATH = Path(__file__).parent.parent / "assets"


def _mod(where):
    return where or _fake_mod


def twin_component():
    """
    Decorates components that can live in both the sidebar and the main window.
    """

    def decorator(fn):
        def bind(where):
            if not (is_streamlit_main(where) or is_streamlit_sidebar(where)):
                raise ValueError(f"cannot bind component to {where}")

            @wraps(fn)
            def bound(*args, **kwargs):
                if "where" in kwargs:
                    raise TypeError("cannot bind bound component!")
                return fn(*args, where=where, **kwargs)

            return bound

        fn.is_sidebar_component = True
        fn.is_main_component = True
        fn.is_twin_component = True
        fn.bind = bind
        return fn

    return decorator


def main_component():
    """
    Decorates components exclusive of the main window.
    """

    def decorator(fn):
        def bind(where):
            if is_streamlit_main(where):
                return fn
            else:
                raise ValueError(f"cannot bind component to {where}")

        fn.is_sidebar_component = False
        fn.is_main_component = True
        fn.is_twin_component = False
        fn.bind = bind
        return fn

    return decorator


def sidebar_component():
    """
    Decorates components exclusive of the sidebar.
    """

    def decorator(fn):
        def bind(where):
            if is_streamlit_sidebar(where):
                return fn
            else:
                raise ValueError(f"cannot bind component to {where}")

        fn.is_sidebar_component = True
        fn.is_main_component = False
        fn.is_twin_component = False
        fn.bind = bind
        return fn

    return decorator


def info_component(kind=None):
    """
    Mark component with a uniform API that accepts arguments to be passed either
    as keyword arguments or as a dictionary-like object single positional
    argument.
    """

    def decorator(fn):
        keywords = set()

        @wraps(fn)
        def decorated(*args, **kwargs):
            if args:
                if len(args) == 1 and isinstance(args[0], (dict, sk.record)):
                    (arg,) = args
                    if isinstance(arg, sk.record):
                        default = {k: v for k, v in arg if k in keywords}
                    else:
                        default = {k: arg[k] for k in keywords.intersection(arg)}
                    kwargs = {**default, **kwargs}
                    args = ()

            return func(*args, **kwargs)

        # Obtain list of keywords from signature
        sig = inspect.signature(fn)
        keywords.update(sig.parameters)

        # Transform function as a UI component
        if kind == "main":
            decorate = main_component()
        elif kind == "twin":
            decorate = twin_component()
        elif kind in ("none", None):
            decorate = lambda x: x
        else:
            raise ValueError(f"Invalid component kind: {kind!r}")
        func = decorate(fn)

        return decorated

    return decorator


@lru_cache(256)
def asset(name, mode="r"):
    """
    Read asset from the assets directory
    """
    path = BASE_PATH / name
    with path.open(mode) as fd:
        return fd.read()


def is_streamlit_main(mod):
    return mod is st


def is_streamlit_sidebar(mod):
    return mod is st.sidebar
