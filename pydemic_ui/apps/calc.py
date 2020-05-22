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
import importlib
import os

from pydemic.diseases import covid19
from pydemic.models import SEAIR
from pydemic.utils import extract_keys
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


def sidebar(
    region="BR", disease=covid19, where=st.sidebar, secret_date=None, secret_function=None
):
    """
    Calculator sidebar element.

    It receives a region and a disease (defaults to Covid-19) and return a
    dictionary of parameters that might be useful to configure a simulation.
    """
    st = where
    st.logo()
    region = st.select_region(region, healthcare_regions=True)

    try:
        params = st.simulation_params(region, disease, secret_date=secret_date)
    except RuntimeError:
        st = globals()["st"]
        st.title(_("Secret area for beta testers"))
        secret_function()
        return

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


def easter_egg(disease=covid19):
    apps = {
        "scenarios_br": _("Hospital pressure in different epidemiological scenarios"),
        "projections_br": _("Projections for Brazilian epidemiological evolution"),
    }
    msg = _("Select the secret application")
    app = st.selectbox(msg, list(apps.keys()), format_func=apps.get)

    mod = importlib.import_module(f"pydemic_ui.apps.{app}")
    mod.main(embed=True, disease=disease)


def main(region="BR", disease=covid19):
    st.css()
    params = sidebar(
        region=region,
        disease=disease,
        secret_date=datetime.date(1904, 11, 10),
        secret_function=lambda: easter_egg(disease),
    )
    if params is None:  # Secret function was activated
        return

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


# Start main script
if __name__ == "__main__":
    main()
