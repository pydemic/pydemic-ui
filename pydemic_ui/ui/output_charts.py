__package__ = "pydemic_ui.ui"

import numpy as np
import pandas as pd
import streamlit as st

from pydemic.utils import fmt, pc
from ..components import cards, pause, pyramid_chart, main_component, html
from ..i18n import _, __


@main_component()
def hospitalizations_chart(model, title=__("Hospital demand")):
    """
    Write plot of hospitalization pressure information.
    """
    if title:
        st.header(str(title))

    icu_ts = model["critical:dates"]
    hospitalized_ts = model["severe:dates"]
    deaths_ts = model["deaths:dates"]

    st.line_chart(
        pd.DataFrame(
            {
                _("Deaths"): deaths_ts,
                _("Required hospital beds"): hospitalized_ts.astype(int),
                _("Required ICU beds"): icu_ts.astype(int),
            }
        )
    )


@main_component()
def available_beds_chart(model, title=__("Available hospital beds")):
    """
    Write plot of available beds.
    """

    if title:
        st.header(str(title))

    icu_ts = model["critical:dates"]
    hospitalized_ts = model["severe:dates"]

    available_beds_ts = model.hospital_surge_capacity - hospitalized_ts
    available_icu_ts = model.icu_surge_capacity - icu_ts

    available_beds_ts[available_beds_ts < 0] = 0
    available_icu_ts[available_icu_ts < 0] = 0

    st.line_chart(
        pd.DataFrame({_("Regular"): available_beds_ts, _("ICU"): available_icu_ts})
    )


@main_component()
def deaths_chart(model, where=st):
    """
    Age-stratified deaths.

    Stratification is inferred from age distribution if deaths is a scalar.
    """

    deaths = model["deaths:final"]
    age_distribution = model.age_distribution
    disease = model.disease

    where.header(_("Anticipated age distribution of COVID deaths by age"))

    mortality = disease.mortality_table()
    idxs = [*zip(range(0, 80, 10), range(5, 80, 10)), (80, 85, 90, 95, 100)]
    age_distribution = np.array([age_distribution.loc[list(idx)].sum() for idx in idxs])

    death_distribution = mortality["IFR"] * age_distribution
    death_distribution = death_distribution / death_distribution.sum()

    total = (death_distribution * deaths).astype(int)
    mortality = (1e5 * mortality["IFR"]).astype(int)

    data = pd.DataFrame([total, mortality]).T
    data.columns = ["", ""]
    data.index = [*(f"{x}-{x + 9}" for x in data.index[:-1]), "80+"]

    where.markdown(_("**Total cases**"))
    where.bar_chart(data.iloc[:, 0])

    where.markdown(_("**Mortality per 100k**"))
    where.bar_chart(data.iloc[:, 1])


@main_component()
def population_info_chart(age_pyramid):
    """
    Write additional information about the model.
    """

    # Info
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


if __name__ == "__main__":
    from ..examples import seir_info, seir
    from ..components import css

    css()

    model = seir()
    info = seir_info()
    hospitalizations_chart(model)
    deaths_chart(model)
    population_info_chart(model)
    # available_beds_chart(info)
