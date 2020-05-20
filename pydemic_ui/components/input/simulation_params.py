__package__ = "pydemic_ui.components.input"

import streamlit as st
from markdown import markdown

import mundi
from pydemic.diseases import covid19
from pydemic.utils import fmt, safe_int, pc
from ..base import twin_component
from ..generic import html
from ...i18n import _, __
from ...info import (
    get_confirmed_daily_cases_for_region,
    get_notification_estimate_for_region,
)

OCCUPANCY_MSG = __(
    """
   The Brazilian occupancy rate is traditionally above **{globalrate}**. The input
   parameters assume a **{rate}** occupancy rate and **{n}** available beds.
   """
)


@twin_component()
def simulation_params(
    region, disease=covid19, title=__("Simulation options"), where=st
) -> dict:
    """
    Return a dictionary with basic simulation parameters from user input.

    Returns:
          period (int): Simulation period in days.
          start_date (date): Initial date.
          daily_cases (int): Expected number of new cases per day.
    """

    st = where
    if title:
        st.header(str(title))
    region = mundi.region(region)

    # Durations
    period = st.slider(_("Duration (weeks)"), 1, 30, value=10) * 7
    start_date = st.date_input(_("Simulation date"))

    # Seed
    st.subheader(_("Cases"))
    msg = _("Average new confirmed COVID-19 cases per day")
    cases = get_confirmed_daily_cases_for_region(region, disease) or 1
    cases = st.number_input(msg, 1, int(region.population), value=cases)

    msg = _("Notification rate (%)")
    notification = get_notification_estimate_for_region(region, disease)
    notification = 0.01 * st.slider(msg, 1.0, 100.0, max(1.0, 100.0 * notification))

    return {"period": period, "date": start_date, "daily_cases": cases / notification}


@twin_component()
def healthcare_params(region, title=__("Hospital capacity"), occupancy=0.75, where=st):
    """
    Return a dictionary with hospital and icu capacities from user input.

    Returns:
        icu_capacity (float): surge system capacity of ICUs
        icu_full_capacity (float): total system capacity of ICUs
        hospital_capacity (float): surge system capacity of regular beds
        hospital_full_capacity (float): total system capacity of regular beds
    """

    region = mundi.region(region)
    where.header(str(title))

    def get(title, capacity, rate, key=None):
        where.subheader(title)

        total = where.number_input(
            _("Total capacity"), min_value=0, value=int(capacity), key=key + "_total"
        )
        result = where.number_input(
            _("Occupied"),
            min_value=0,
            max_value=total,
            value=int(total * rate),
            key=key + "_rate",
        )
        msg = markdown(
            OCCUPANCY_MSG.format(
                n=fmt(total - result), rate=pc(result / total), globalrate=pc(rate)
            )
        )
        html(f'<span style="font-size: smaller;">{msg}</span>', where=where)
        return total - result

    h_cap = safe_int(region.hospital_capacity)
    icu_cap = safe_int(region.icu_capacity)

    return {
        "icu_full_capacity": icu_cap,
        "hospital_full_capacity": h_cap,
        "icu_capacity": get(_("ICU beds"), icu_cap, occupancy, key="icu"),
        "hospital_capacity": get(_("Clinical beds"), h_cap, occupancy, key="hospital"),
    }


if __name__ == "__main__":
    import streamlit as st

    region = st.text_input("Region", value="BR")
    st.write(simulation_params(region))
    st.write(healthcare_params(region))
