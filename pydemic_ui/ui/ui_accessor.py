from functools import partial

import sidekick as sk
import streamlit as st

ui = sk.import_later("pydemic_ui.ui")
BLACKLIST = {None}


class UI:
    """
    implements the model.ui accessor
    """

    def __init__(self, model):
        self.model = model

    def __getattr__(self, item):
        if item in BLACKLIST:
            value = None
        else:
            value = getattr(ui, item)

        if getattr(value, "is_twin_component", False):
            pass
        elif getattr(value, "is_main_component", False):
            value = value.bind(st)
        elif getattr(value, "is_sidebar_component", False):
            value = value.bind(st.sidebar)
        else:
            raise AttributeError(f"model.ui has no {item!r} attribute")

        value = partial(value, self.model)
        setattr(self, item, value)
        return value
