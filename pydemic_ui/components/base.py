import inspect
from functools import wraps, lru_cache
from pathlib import Path
from types import SimpleNamespace

import sidekick as sk
import streamlit as st

import pydemic_ui

_fake_mod = SimpleNamespace(markdown=lambda x, **kwargs: x, write=lambda x, **kwargs: x)

BASE_PATH = Path(pydemic_ui.__file__).parent / "assets"


def _mod(where):
    return where or _fake_mod


def twin_component():
    """
    Decorates components that can live in both the sidebar and the main window.
    """

    def decorator(fn):
        @wraps(fn)
        def decorated(*args, where=st, **kwargs):
            if where == "main":
                where = st
            elif where == "sidebar":
                where = st.sidebar
            else:
                where = _mod(where)
            return fn(*args, where=where, **kwargs)

        return decorated

    return decorator


def main_component():
    """
    Decorates components exclusive of the main window.
    """

    def decorator(fn):
        @wraps(fn)
        def decorated(*args, where=st, **kwargs):
            if where == "main":
                where = st
            elif where == "sidebar" or where == st.sidebar:
                raise RuntimeError("Cannot be placed in the sidebar")
            else:
                where = _mod(where)
            return fn(*args, where=where, **kwargs)

        return decorated

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
                    arg, = args
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
        if kind == 'main':
            decorate = main_component()
        elif kind == 'twin':
            decorate = twin_component()
        elif kind in ('none', None):
            decorate = lambda x: x
        else:
            raise ValueError(f'Invalid component kind: {kind!r}')
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
