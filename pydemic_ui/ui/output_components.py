__package__ = "pydemic_ui.ui"

import pandas as pd
import streamlit as st
from babel.dates import format_date

from pydemic.utils import fmt
from ..components import info_component, md_description
from ..i18n import _, __

#
# Messages
#
NO_ICU_MESSAGE = __(
    """
The location does not have any ICU beds. At peak demand, it needs to reserve {n}
beds from neighboring cities.
"""
)

ICU_OVERFLOW_MESSAGE = __(
    """
The location will **run out of ICU beds at {date}**. At peak demand, it will need **{n}
new ICUs**. This demand corresponds to **{surge} times** the number of beds dedicated
to COVID-19 and {total} of the total number of ICU beds.
"""
)

GOOD_CAPACITY_MESSAGE = __(
    """
The number of ICU beds is sufficient for the expected demand in this scenario.
"""
)


@info_component("main")
def healthcare_parameters(
    icu_capacity,
    hospital_capacity,
    icu_full_capacity,
    icu_overflow_date,
    extra_icu,
    where=st,
):
    """
    Write base healthcare parameters.
    """
    where.header(_("Healthcare system"))

    md_description(
        {
            _("COVID/SARI ICUs"): fmt(int(icu_capacity)),
            _("COVID/SARI hospital beds"): fmt(int(hospital_capacity)),
        },
        where=where,
    )

    if icu_full_capacity == 0:
        msg = NO_ICU_MESSAGE.format(n=fmt(extra_icu))
    elif icu_overflow_date:
        peak_icu = extra_icu + icu_capacity
        msg = ICU_OVERFLOW_MESSAGE.format(
            date=natural_date(icu_overflow_date),
            n=fmt(int(peak_icu - icu_capacity)),
            surge=fmt(peak_icu / icu_capacity),
            total=fmt(peak_icu / icu_full_capacity),
        )
    else:
        msg = str(GOOD_CAPACITY_MESSAGE)

    where.markdown(msg)


def healthcare_equipment_resources(hospital_days, icu_days):
    """
    Return the recommended usage of protection equipment by healthcare staff
    from the number of hospitalization x days and ICU x days.
    """

    columns = [_("Quantity"), _("Total")]
    tuples = zip([_("Patients/day"), ""], columns)

    N = int(hospital_days + icu_days)
    a = 1  # / 5
    b = 1  # / 15
    df = pd.DataFrame(
        [
            [_("Cirurgical masks"), 25, 25 * N],
            [_("N95 mask"), a, a * N],
            [_("Waterproof apron"), 25, 25 * N],
            [_("Non-sterile glove"), 50, 50 * N],
            [_("Faceshield"), b, b * N],
        ]
    ).set_index(0)

    df.index.name = _("Name")
    df.columns = pd.MultiIndex.from_tuples(tuples)
    return df


def natural_date(x):
    """
    Friendly representation of dates.

    String inputs are returned as-is.
    """
    if isinstance(x, str):
        return x
    elif x is None:
        return _("Not soon...")
    else:
        return format_date(x, format="short")
