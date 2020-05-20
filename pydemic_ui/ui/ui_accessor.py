from functools import partial, wraps

import sidekick as sk
import streamlit as st

from . import output_charts as charts
from . import output_components as components

ui = sk.import_later("pydemic_ui.ui")
BLACKLIST = {None}


def ui_prop(fn, bind=st):
    func = fn.bind(bind)

    @property
    @wraps(fn)
    def prop(self):
        return lambda *args, **kwargs: func(self.model, *args, **kwargs)

    return prop


class UI:
    """
    implements the model.ui accessor
    """

    # Charts
    population_info_chart = ui_prop(charts.population_info_chart)
    hospitalizations_chart = ui_prop(charts.hospitalizations_chart)
    available_beds_chart = ui_prop(charts.available_beds_chart)
    deaths_chart = ui_prop(charts.deaths_chart)

    # Components
    ui_prop(components.epidemiological_parameters)
    # ui_prop(components.healthcare_parameters)
    ui_prop(components.summary_cards)
    ui_prop(components.ppe_demand)

    @property
    def sidebar(self):
        return UISidebar(self.model)

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


class UISidebar:
    def __init__(self, model):
        self.model = model
