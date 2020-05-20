import streamlit as st

import pydemic_ui.pyplot as plt
from pydemic.diseases import covid19
from pydemic.utils import fmt
from .base import main_component
from .generic import cards
from .. import info
from ..i18n import _


# noinspection PyIncorrectDocstring
@main_component()
def cases_and_deaths_plot(
    cases, *, n_cases=None, n_deaths=None, _plt_data=None, **kwargs
):
    """
    Display a nice chart with the list of cases and deaths.

    Args:
        cases:
            A Dataframe with at least a "cases" and "deaths" columns.
        n_cases:
            Explicit number of cases (overrides value in dataframe)
        n_deaths:
            Explicit number of deaths (overrides value in dataframe)

    Notes:
        This function has a cached version that uses a region as input
    """
    n_cases = n_cases if n_cases is not None else cases.iloc[-1]["cases"]
    n_deaths = n_deaths if n_deaths is not None else cases.iloc[-1]["deaths"]

    st.header(_("Observed daily cases and deaths"))
    cards({_("Cases"): fmt(n_cases), _("Deaths"): fmt(n_deaths)}, color="st-gray-900")

    if not _plt_data:
        ax = plt.pydemic.cases_and_deaths(cases, **kwargs)
        figure = ax.get_figure()
        st.pyplot(figure, clear_figure=True)
    else:
        st.pyplot(_plt_data)


# Helper functions
def from_region(region, disease=covid19, **kwargs):
    """
    A cached version of cases_chart_section that use region instead of a cases
    dataframe as input.
    """
    n_cases, n_deaths, plot = cases_and_deaths_plot_from_region(region, disease, **kwargs)
    cases_and_deaths_plot(..., n_cases=n_cases, n_deaths=n_deaths, _plt_data=plot)


# @st.cache(ttl=info.TTL_DURATION)
@info.ttl_cache(key="ui.pyplot", force_joblib=True)
def cases_and_deaths_plot_from_region(region, disease, **kwargs):
    cases = info.get_cases_for_region(region, disease=disease)
    ax = plt.pydemic.cases_and_deaths(cases, **kwargs)
    n_cases = cases.iloc[-1]["cases"]
    n_deaths = cases.iloc[-1]["deaths"]
    return n_cases, n_deaths, ax.get_figure()


cases_and_deaths_plot.from_region = from_region
