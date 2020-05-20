"""
Pydemic Calc Application
========================

This is the main application in the Pydemic UI package. It consists of an
epidemic calculator that allows user to choose some region and configure basic
epidemiological parameters to make scenarios about how the epidemic spreads
in the near future.

This app uses components from the Pydemic UI package.
"""
import datetime
import os

import numpy as np
import pandas as pd

import mundi
from pydemic.diseases import covid19
from pydemic.models import SEAIR
from pydemic.utils import extract_keys, pc
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui import ui
from pydemic_ui.i18n import _

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "on", "1")

DEATH_DISTRIBUTION_COLUMNS = [
    "natural_deaths:dates",
    "icu_overflow_deaths:dates",
    "hospital_overflow_deaths:dates",
]

DEATH_DISTRIBUTION_COL_NAMES = {
    "natural_deaths": _("Natural"),
    "icu_overflow_deaths": _("Lack of hospital beds"),
    "hospital_overflow_deaths": _("Lack of ICUs"),
}

PARAMS = [
    "region",
    "R0",
    "infectious_period",
    "incubation_period",
    "prob_symptoms",
    "date",
    "daily_cases",
    "runner",
    "period",
]

CLINICAL = [
    "hospitalization_period",
    "icu_period",
    "hospital_capacity",
    "icu_capacity",
    "prob_severe",
    "prob_critical",
]

CAPACITY = ["hospital_full_capacity", "icu_full_capacity"]


def sidebar(region="BR", disease=covid19, where=st.sidebar):
    """
    Calculator sidebar element.

    It receives a region and a disease (defaults to Covid-19) and return a
    dictionary of parameters that might be useful to configure a simulation.
    """
    st = where
    st.logo()
    region = st.select_region(region, healthcare_regions=True)
    params = st.simulation_params(region, disease)
    return {
        "region": region,
        **params,
        **st.healthcare_params(region),
        **st.epidemiological_params(region, disease),
        **{"runner": st.select_intervention(params["period"])},
    }


def output(model, info, title=_("Hospital pressure calculator")):
    """
    Create default output from model.
    """
    if title:
        st.title(title)

    model.ui.summary_cards()

    st.pause()
    model.ui.hospitalizations_chart()

    st.pause()
    model.ui.available_beds_chart()

    st.line()
    ui.population_info_chart(info["age_pyramid"])

    st.pause()
    model.ui.deaths_chart()

    st.line()
    ui.healthcare_parameters(info)

    st.pause()
    model.ui.ppe_demand()

    st.pause()
    model.ui.epidemiological_parameters()

    st.pause()
    st.footnotes()


# @tle_cache('ui.app.calc')
def model(*, daily_cases, runner, period, disease, **kwargs):
    """
    Return model from parameters
    """
    m = SEAIR(disease=disease, **kwargs)

    R = 0.0
    E = daily_cases * m.incubation_period
    I = daily_cases * m.infectious_period * m.Qs
    A = daily_cases * m.infectious_period * (1 - m.Qs)
    S = m.population - E - A - I - R

    m.set_ic(state=(S, E, A, I, R))
    m = runner(m, period)
    return m


def main(region="BR", disease=covid19):
    st.css()
    params = sidebar(region=region, disease=disease)
    debug = False

    if DEBUG and st.checkbox(_("Enable debug")):
        st.info(_("Running in debug mode!"))
        st.html(
            """
        <ul>
            <li><a href="#debug">{}</a></li>
        </ul>""".format(
                _("Debug section!")
            )
        )
        debug = True

    if params["date"] == datetime.date(1904, 11, 10):
        st.title(_("Secret area for beta testers"))
        return secret(params)

    epidemiology = extract_keys(PARAMS, params)
    clinical = extract_keys(CLINICAL, params)

    # Run infections model
    m = cm = results = None
    try:
        m = model(disease=disease, **epidemiology)
        cm = m.clinical.overflow_model(icu_occupancy=0, hospital_occupancy=0, **clinical)
        cm.extra_info = params
        results = info.full_info(cm)
        results["model"] = cm
        output(cm, results)

    finally:
        if debug:
            if results:
                st.html('<div style="height: 15rem"></div>')
            st.html('<h2 id="debug">{}</h2>'.format(_("Debug information")))

            st.subheader(_("Generic parameters"))
            st.write(params)

            st.subheader(_("Epidemiological parameters"))
            st.write(epidemiology)

            st.subheader(_("Clinical parameters"))
            st.write(clinical)

            st.subheader(_("Output"))
            st.write(results)

            if m:
                st.line_chart(m.data)

            if cm:
                st.line_chart(cm[["infectious", "severe", "critical"]])

                st.subheader(_("Distribution of deaths"))
                df = cm[DEATH_DISTRIBUTION_COLUMNS]
                df.columns = [DEATH_DISTRIBUTION_COL_NAMES[k] for k in df.columns]
                st.area_chart(df)


def secret(params, disease=covid19):
    states = mundi.regions("BR", type="state")
    region = st.selectbox(_("Select state"), states.index)

    msg = _("Isolation scores")
    scores = [n / 10 for n in range(1, 10)]
    isolation = st.multiselect(msg, scores, default=[0.3, 0.5, 0.7], format_func=pc)
    rates = 1 - np.array(isolation)

    duration = st.number_input(_("Duration"), 1, value=60)

    daily_cases = info.get_confirmed_daily_cases_for_region(region, disease)
    daily_cases /= max(info.get_notification_estimate_for_region(region, disease), 1e-2)

    def run_model(daily_cases, rate=1.0):
        m = SEAIR(region=region, disease=disease)
        m.R0 *= rate

        R = 0.0
        E = daily_cases * m.incubation_period
        I = daily_cases * m.infectious_period * m.Qs
        A = daily_cases * m.infectious_period * (1 - m.Qs)
        S = m.population - E - A - I - R
        m.set_ic(state=(S, E, A, I, R))

        m.run(duration)
        cm = m.clinical.overflow_model()
        cm.score = f"Isolation {pc(1 - rate)}"
        return cm

    def dataframe(models, col, attr):
        return pd.DataFrame({getattr(m, attr): m[col] for m in models})

    cms = [run_model(daily_cases, r) for r in rates]

    st.subheader(_("ICU beds"))
    st.line_chart(dataframe(cms, "critical", "score"))

    st.subheader(_("Hospital beds"))
    st.line_chart(dataframe(cms, "severe", "score"))

    st.subheader(_("Cases"))
    st.line_chart(dataframe(cms, "cases", "score"))

    st.subheader(_("Deaths"))
    st.line_chart(dataframe(cms, "deaths", "score"))


# Start main script
if __name__ == "__main__":
    main()
