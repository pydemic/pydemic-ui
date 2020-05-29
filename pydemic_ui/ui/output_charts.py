__package__ = "pydemic_ui.ui"

import numpy as np
import pandas as pd
import streamlit as st

from pydemic.utils import fmt, pc
from ..components import cards, pause, pyramid_chart, main_component, html
from ..i18n import _


@main_component()
def population_info_chart(age_pyramid, where=st):
    """
    Write additional information about the model.
    """

    st = where
    if not isinstance(age_pyramid, pd.DataFrame):
        age_pyramid = age_pyramid.age_pyramid

    population = age_pyramid.values.sum()
    seniors_population = age_pyramid.loc[60:].values.sum()

    # Cards
    st.header(_("Population"))

    entries = {
        _("Total"): fmt(population),
        _(
            "Age 60+"
        ): f"{fmt(seniors_population)} ({pc(seniors_population / population)})",
    }
    cards(entries, where=st)

    # Pyramid chart
    pause(where=st)
    st.subheader(_("Population pyramid") + "*")

    # Reindex age_pyramid to 10yrs groups
    ages = list(map(list, zip(age_pyramid.index[:-3:2], age_pyramid.index[1::2])))
    ages[-1] = [80, 85, 90, 95, 100]
    rows = []
    for r in ages:
        rows.append(age_pyramid.loc[r].sum())
    data = pd.DataFrame(rows, index=age_pyramid.index[:-3:2])

    # Change index to show ranges
    ends = [*(f"-{n}" for n in (np.array(data.index) - 1)[1:]), "+"]
    age_ranges = [f"{a}{b}" for a, b, in zip(data.index, ends)]
    data.index = age_ranges

    data = data.rename({"female": "left", "male": "right"}, axis=1)
    pyramid_chart(data, _("Female"), _("Male"), where=st)

    source = _(
        """
FREIRE, F.H.M.A; GONZAGA, M.R; QUEIROZ, B.L. Projeção populacional municipal
com estimadores bayesianos, Brasil 2010 - 2030, 2019
"""
    )
    label = _("Source")
    html(
        f'<div style="font-size: smaller; text-align: right;">* '
        f"<strong>{label}</strong>:{source}</div>"
    )
