import streamlit as _st
from streamlit import *

from .patch import pydemic, patch as _patch


class _Sidebar:
    def __init__(self, sidebar):
        self._sidebar = sidebar

    def __getattr__(self, attr):
        try:
            value = getattr(self._sidebar, attr)
        except AttributeError:
            raise
        else:
            setattr(self, attr, value)
            return value


def __getattr__(name):
    return getattr(_st, name)


sidebar = _Sidebar(sidebar)
_patch(sidebar)
_patch(__qualname__)