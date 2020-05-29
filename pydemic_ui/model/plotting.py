import numpy as np
import pandas as pd

from .. import st
from ..decorators import title
from ..i18n import _, __


@title(__("Hospital demand"))
def hospitalizations_chart(model, where=st):
    """
    Write plot of hospitalization pressure information.
    """

    icu_ts = model["critical:dates"]
    hospitalized_ts = model["severe:dates"]
    deaths_ts = model["deaths:dates"]

    where.line_chart(
        pd.DataFrame(
            {
                _("Deaths"): deaths_ts,
                _("Required hospital beds"): hospitalized_ts.astype(int),
                _("Required ICU beds"): icu_ts.astype(int),
            }
        )
    )


@title(__("Available hospital beds"))
def available_beds_chart(model, where=st):
    """
    Write plot of available beds.
    """

    icu_ts = model["critical:dates"]
    hospitalized_ts = model["severe:dates"]

    available_beds_ts = model.hospital_surge_capacity - hospitalized_ts
    available_icu_ts = model.icu_surge_capacity - icu_ts

    available_beds_ts[available_beds_ts < 0] = 0
    available_icu_ts[available_icu_ts < 0] = 0

    where.line_chart(
        pd.DataFrame({_("Regular"): available_beds_ts, _("ICU"): available_icu_ts})
    )


@title(__("Anticipated age distribution of COVID deaths by age"))
def deaths_chart(model, where=st):
    """
    Age-stratified deaths.

    Stratification is inferred from age distribution if deaths is a scalar.
    """

    st = where

    deaths = model["deaths:final"]
    age_distribution = model.age_distribution
    disease = model.disease

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

    st.markdown(_("**Total cases**"))
    st.bar_chart(data.iloc[:, 0])

    st.markdown(_("**Mortality per 100k**"))
    st.bar_chart(data.iloc[:, 1])
