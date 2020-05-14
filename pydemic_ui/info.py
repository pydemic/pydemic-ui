from functools import lru_cache

import numpy as np
import streamlit as st

import mundi_demography as mdm
import mundi_healthcare as mhc
from pydemic.diseases import covid19
from pydemic.utils import coalesce, safe_int


def model_info(model) -> dict:
    """
    Extract a dictionary of information about the model.
    """

    # Simple parameters
    deaths = model["deaths:final"]
    hospitalizations = model["hospitalized_cases:final"]
    icu_overflow_date = model["icu-overflow:peak-date"]
    hospital_overflow_date = model["hospital-overflow:peak-date"]
    extra_icu = model["icu-overflow:max"]
    extra_hospitals = model["hospital-overflow:max"]

    # Time series
    icu_ts = model["critical:dates"]
    hospitalized_ts = model["severe:dates"]
    death_rate_ts = model["death_rate:dates"]
    deaths_ts = model["deaths:dates"]

    # Healthcare and parameters
    icu_capacity = model.icu_surge_capacity
    hospital_capacity = model.hospital_surge_capacity
    prob_symptoms = model.prob_symptoms

    # Epidemiological
    R0 = model["R0:final"]
    mortality = model["deaths:final:pp"]
    fatality = model["empirical-CFR:final"]
    infected = model["infected:final:pp"]

    # Create result from locals()
    data = locals()
    del data["model"]
    data.update(getattr(model, 'extra_info', {}))
    return data


@lru_cache(4096)
def region_info(region: str, disease=covid19) -> dict:
    """
    Information about region and region-bound epidemiological parameters from
    region code.
    """
    assert isinstance(region, str)

    # Demography
    age_pyramid = mdm.age_pyramid(region, infer=True)
    age_distribution = age_pyramid.sum(1)

    population = int(age_distribution.sum())
    seniors_population = int(age_distribution.loc[60:].sum())

    # Hospital capacity
    icu_capacity = safe_int(mhc.icu_capacity(region))
    hospital_capacity = safe_int(mhc.hospital_capacity(region))

    # Epidemiology
    R0 = R0_from_region(region, disease)

    # Cases and deaths
    cases_ts, deaths_ts = load_cases_deaths(region)

    out = locals()
    out.update()
    return {
        **disease.to_dict(age_distribution=age_distribution),
        **out,
    }


def full_info(model, disease=None):
    """
    Construct full information dictionary
    """

    disease = coalesce(disease, model.disease, covid19)
    return {
        **region_info(model.region.id, disease=disease),
        **model_info(model),
    }


#
# Cache
#
@lru_cache(1024)
def load_seed(code):
    """
    Load seed from code regional code.
    """
    try:
        cases, deaths = load_cases_deaths(code)
        if np.isnan(cases):
            raise ValueError
    except (LookupError, ValueError):
        prevalence = 1 / 10_000
        pop_size = population(code)
        return int(pop_size * prevalence)
    else:
        CFR = max(covid19.CFR(age_distribution=mdm.age_distribution(code)), 0.012)
        return int(max(cases, deaths / CFR))


@lru_cache(1024)
def load_deaths(code):
    """
    Load deaths from code region code.
    """
    try:
        curve = covid19.epidemic_curve(code).dropna().max()
        if np.isnan(curve["cases"]):
            raise ValueError

    except (LookupError, ValueError):
        prevalence = 1 / 1_000
        pop_size = population(code)
        return int(pop_size * prevalence)
    else:
        CFR = max(covid19.CFR(age_distribution=mdm.age_distribution(code)), 0.012)
        return int(max(curve["cases"], curve["deaths"] / CFR))


@lru_cache(1024)
def load_cases_deaths(code):
    data = covid19.epidemic_curve(code).dropna().max()
    return data['cases'], data['deaths']


def population(code):
    try:
        return int(mdm.population(code))
    except ValueError:
        return 1_000_000


@lru_cache(1024)
def R0_from_region(region, disease):
    # In the future we might infer R0 from epidemic curves
    return disease.R0()


@st.cache(ttl=4 * 3600)
def confirmed_cases(region, disease):
    """
    List of confirmed cases for the given region.
    """
    return safe_int(disease.epidemic_curve(region)["cases"].max())


@st.cache(ttl=4 * 3600)
def confirmed_deaths(region, disease):
    """
    List of confirmed deaths for region.
    """
    return safe_int(disease.epidemic_curve(region)["deaths"].max())


@st.cache
def confirmed_daily_cases(region, disease) -> int:
    """
    Return the number of newly confirmed cases per day.
    """
    df = disease.epidemic_curve(region)
    return safe_int(df["cases"].diff().iloc[-7:].mean())


@st.cache
def notification_estimate(region, disease) -> float:
    """
    Return an estimate on the notification rate for disease in the given
    region.
    """
    df = disease.epidemic_curve(region)
    deaths = df["deaths"].diff().iloc[-7:].mean()

    IFR = disease.IFR(region=region)
    expected_cases = deaths / IFR
    cases = df["cases"].diff().iloc[-7:].mean()

    # This correction is still just a wild guess. If the sub-notification when
    # comparing with the expected death rate is too high, we assume some kind of
    # failure in the healthcare system. This should increase the IFR by some
    # unknown amount. As simple way to penalize is to raise to some power smaller
    # than one: very small ratios increase by a larger amount than values closer
    # to unity.
    #
    # It is very unlikely that any region has a notification rate higher than
    # 0.75, hence we also put a cap on the value.
    ratio = min((cases / expected_cases) ** 0.8, 0.75)
    return ratio if np.isfinite(ratio) else 0.1
