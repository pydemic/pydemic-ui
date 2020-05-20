__package__ = "pydemic_ui.components.input"

import streamlit as st

import mundi
from pydemic.diseases import covid19
from ..base import twin_component
from ...i18n import _, __


@twin_component()
def epidemiological_params(
    region, disease=covid19, R0_max=5.0, title=__("Epidemiology"), where=st
):
    """
    Return a dictionary with additional simulation parameters from user input.
    Those parameters are related to basic epidemiology assumptions such as
    the value of R0, incubation period, etc.
    """

    region = mundi.region(region)

    # Choose scenario
    where.header(str(title))

    opts = [_("Standard"), _("Advanced")]
    std, custom = scenarios = opts
    scenario = where.selectbox(_("Scenario"), scenarios)

    # Return simple scenarios
    if scenario == std:
        return {}

    params = disease.params(region=region)

    # Custom epidemiology
    where.subheader(_("Epidemiological parameters"))
    msg = _("Basic reproduction number (R0)")
    R0 = where.slider(msg, min_value=0.0, max_value=R0_max, value=params.R0)

    msg = _("Virus incubation period")
    Tinc = where.slider(
        msg, min_value=0.1, max_value=10.0, value=params.incubation_period
    )

    msg = _("Infectious period")
    Tinf = where.slider(
        msg, min_value=0.1, max_value=14.0, value=params.infectious_period
    )

    msg = _("Fraction of symptomatic cases")
    Qs = 100 * params.prob_symptoms
    Qs = 0.01 * where.slider(msg, min_value=0.1, max_value=100.0, value=Qs)

    # Clinical parameters
    where.subheader(_("Clinical parameters"))

    msg = _("Fraction of hospitalized cases")
    Qsv = 100 * params.prob_severe
    Qsv = 0.01 * where.slider(msg, min_value=0.1, max_value=100.0, value=Qsv)

    msg = _("Need for ICU in hospitalized cases")
    Qcr = 100 * params.prob_critical / (params.prob_severe + 1e-6)
    Qcr = 0.01 * where.slider(msg, min_value=0.1, max_value=100.0, value=Qcr)
    Qcr *= Qsv

    msg = _("Hospitalization period (days)")
    Th = where.slider(
        msg, min_value=0.1, max_value=30.0, value=params.hospitalization_period
    )

    msg = _("Hospitalization period for ICU patients (days)")
    Tc = where.slider(msg, min_value=0.1, max_value=30.0, value=params.icu_period)

    return {
        "R0": R0,
        "incubation_period": Tinc,
        "infectious_period": Tinf,
        "hospitalization_period": Th,
        "icu_period": Tc,
        "prob_symptoms": Qs,
        "prob_severe": Qsv,
        "prob_critical": Qcr,
    }


if __name__ == "__main__":
    st.header("Params")
    st.write(epidemiological_params("BR"))
