import datetime
import os

import numpy as np
import pandas as pd
import streamlit as st

import mundi
from pydemic import cache
from pydemic import fitting as fit
from pydemic.diseases import covid19
from pydemic.utils import safe_int

TTL_DURATION = 2 * 60 * 60


def ttl_cache(
    fn=None,
    ttl=TTL_DURATION,
    force_streamlit=False,
    force_joblib=False,
    key="ui.info",
    **kwargs,
):
    """
    Default time-to-live cache logic.
    """
    if fn is None:
        return lambda f: ttl_cache(f, ttl, force_streamlit, force_joblib)

    if force_streamlit:
        return st.cache(ttl=ttl, **kwargs)(fn)
    elif force_joblib:
        return cache.ttl_cache(key, timeout=ttl, **kwargs)(fn)

    backend = os.environ.get("PYDEMIC_UI_CACHE_BACKEND", "joblib").lower()
    if backend == "joblib":
        return ttl_cache(fn, ttl, force_joblib=True)
    elif backend == "streamlit":
        return ttl_cache(fn, ttl, force_streamlit=True)
    else:
        raise ValueError(f"invalid cache backend: {backend!r}")


#
# Cache
#
@ttl_cache()
def get_R0_estimate_for_region(region, disease=covid19):
    # In the future we might infer R0 from epidemic curves
    return disease.R0()


@ttl_cache()
def get_cases_for_region(region, disease=covid19) -> pd.DataFrame:
    """
    A cached function that return a list of cases from region.
    """
    region = mundi.region(region)
    return region.pydemic.epidemic_curve(disease).fillna(method="bfill")


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
    region = mundi.region(region)
    df = region.pydemic.epidemic_curve(disease)
    return safe_int(df["cases"].diff().iloc[-7:].mean())


@ttl_cache()
def get_notification_estimate_for_region(region, disease=covid19) -> float:
    """
    Return an estimate on the notification rate for disease in the given
    region.
    """
    region = mundi.region(region)
    df = region.pydemic.epidemic_curve(disease)
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
    return ratio.item() if np.isfinite(ratio) else 0.1


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

        # We need to check if series number of deaths is sufficient to generate any
        # good statistics. Otherwise, the next best thing is to use the series of
        # cases.
        if len(deaths) < delay:
            bias = get_notification_estimate_for_region(region, disease)
            return get_seair_curves_for_region(
                region=region,
                disease=disease,
                notification_rate=bias * notification_rate,
                use_deaths=False,
            )

        # Obtain smoothed differences to avoid problems with datapoints in which
        # the daily number of new deaths is zero. We also force the accumulated
        # number of deaths to be the same in each case.
        daily_deaths = np.maximum(fit.smoothed_diff(deaths), 0.5)
        daily_deaths *= total_deaths / daily_deaths.sum()

        # Compute extrapolation and concatenate the series for deaths with
        # the extrapolation using data from the past 3 weeks
        delay = min(delay, len(deaths))
        growth_factor, growth_std = fit.growth_factor(daily_deaths[-30:])
        extrapolated = fit.exponential_extrapolation(daily_deaths[-30:], delay)
        extrapolated = np.add.accumulate(extrapolated) + total_deaths

        # Indexes
        index_delay = deaths.index - datetime.timedelta(days=delay)
        index = np.concatenate([index_delay, deaths.index[-delay:]])
        data = pd.Series(np.concatenate([deaths, extrapolated]), index=index)
        data /= params.CFR * CFR_bias * notification_rate
    else:
        data = cases["cases"] / notification_rate
    try:
        return fit.seair_curves(data, params, population=region.population)
    except ValueError:
        region = region.to_dict("country_code", "parent_id")
        st.write(locals())
        st.line_chart(data)
        st.write(data)
        raise ValueError(f"bad data: {data}")
