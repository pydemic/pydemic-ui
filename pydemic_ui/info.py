import datetime
import os
from functools import lru_cache

import numpy as np
import pandas as pd
import streamlit as st

import mundi
import mundi_demography as mdm
import mundi_healthcare as mhc
from pydemic import cache
from pydemic import fitting as fit
from pydemic.diseases import covid19
from pydemic.utils import coalesce, safe_int

TTL_DURATION = 2 * 60 * 60


def ttl_cache(
    fn=None, ttl=TTL_DURATION, force_streamlit=False, force_joblib=False, key="ui.info"
):
    """
    Default time-to-live cache logic.
    """
    if fn is None:
        return lambda f: ttl_cache(f, ttl, force_streamlit, force_joblib)

    if force_streamlit:
        return st.cache(ttl=ttl)(fn)
    elif force_joblib:
        return cache.ttl_cache(key, timeout=ttl)(fn)

    backend = os.environ.get("PYDEMIC_UI_CACHE_BACKEND", "joblib").lower()
    if backend == "joblib":
        return ttl_cache(fn, ttl, force_joblib=True)
    elif backend == "streamlit":
        return ttl_cache(fn, ttl, force_streamlit=True)
    else:
        raise ValueError(f"invalid cache backend: {backend!r}")


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
    data.update(getattr(model, "extra_info", {}))
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
    R0 = get_R0_estimate_for_region(region, disease)

    # Cases and deaths
    cases_ts, deaths_ts = load_cases_deaths(region)

    out = locals()
    out.update()
    return {**disease.to_dict(age_distribution=age_distribution), **out}


def full_info(model, disease=None):
    """
    Construct full information dictionary
    """

    disease = coalesce(disease, model.disease, covid19)
    return {**region_info(model.region.id, disease=disease), **model_info(model)}


#
# Cache
#
def population(code):
    try:
        return int(mdm.population(code))
    except ValueError:
        return 1_000_000


@lru_cache(1024)
def load_cases_deaths(code):
    data = covid19.epidemic_curve(code).dropna().max()
    return data["cases"], data["deaths"]


@ttl_cache()
def get_R0_estimate_for_region(region, disease=covid19):
    # In the future we might infer R0 from epidemic curves
    return disease.R0()


@ttl_cache()
def get_cases_for_region(region, disease=covid19) -> pd.DataFrame:
    """
    A cached function that return a list of cases from region.
    """
    return disease.epidemic_curve(region)


@ttl_cache()
def get_confirmed_cases_for_region(region, disease=covid19):
    """
    List of confirmed cases for the given region.
    """
    cases = get_cases_for_region(region, disease)
    return safe_int(cases["cases"].max())


@ttl_cache()
def get_confirmed_deaths_for_region(region, disease) -> int:
    """
    List of confirmed deaths for region.
    """
    cases = get_cases_for_region(region, disease)
    return safe_int(cases["deaths"].max())


@ttl_cache()
def get_confirmed_daily_cases_for_region(region, disease=covid19) -> int:
    """
    Return the number of newly confirmed cases per day.
    """
    df = disease.epidemic_curve(region)
    return safe_int(df["cases"].diff().iloc[-7:].mean())


@ttl_cache()
def get_notification_estimate_for_region(region, disease=covid19) -> float:
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


@ttl_cache()
def get_seair_curves_for_region(
    region,
    disease=covid19,
    notification_rate=1.0,
    R0=None,
    use_deaths=False,
    CFR_bias=1.0,
) -> pd.DataFrame:
    """
    A cached function that returns SEAIR compartments from cases inferred from
    region.
    """
    region = mundi.region(region)
    cases = get_cases_for_region(region)
    params = disease.params(region=region)
    if use_deaths:
        delay = int(params.death_delay + params.symptom_delay)

        # Filter deaths time series
        deaths = cases["deaths"].dropna()
        deaths = deaths[deaths > 0]
        total_deaths = deaths.iloc[-1]

        # Obtain smoothed differences to avoid problems with datapoints in which
        # the daily number of new deaths is zero. We also force the accumulated
        # number of deaths to be the same in each case.
        daily_deaths = fit.smoothed_diff(deaths)
        daily_deaths *= total_deaths / daily_deaths.sum()

        # Compute extrapolation and concatenate the series for deaths with
        # the extrapolation using data from the past 3 weeks
        extrapolated = fit.exponential_extrapolation(daily_deaths[-21:], delay)
        extrapolated = np.add.accumulate(extrapolated) + total_deaths
        data = pd.Series(
            np.concatenate([deaths, extrapolated]),
            index=np.concatenate(
                [deaths.index - datetime.timedelta(days=delay), deaths.index[-delay:]]
            ),
        )
        data /= params.CFR * CFR_bias * notification_rate
    else:
        data = cases["cases"] / notification_rate

    return fit.seair_curves(data, params, population=region.population, R0=R0)
