__package__ = 'pydemic_ui.ui'

import datetime

import streamlit as st

import mundi
from pydemic.diseases import covid19
from pydemic.utils import fmt, safe_int
from .. import runner
from ..components import html
from ..i18n import _
from ..info import confirmed_daily_cases, notification_estimate

DAY = datetime.timedelta(days=1)

INTERVENTION_TEXT = _("""
This intervention simulates a situation in which everyone reduces
the average number of encounters throughout the day. Small reductions (~15%) are
possible through small behavioral changes. Larger reductions require implementation
of many non-pharmacological measures.
""")
OCCUPANCY_MSG = _("""
The Brazilian occupancy rate is traditionally above {occupancyglobal}{pc}. At {occupancy}{pc} occupancy,
your location has <strong>{n}</strong> available beds.
""")


def simulation_params(region, disease=covid19, title=_("Simulation options"),
                      where=st) -> dict:
    """
    Return a dictionary with basic simulation parameters from user input.

    Returns:
          period (int): Simulation period in days.
          start_date (date): Initial date.
          daily_cases (int): Expected number of new cases per day.
    """

    st = where
    if title:
        st.header(title)
    region = mundi.region(region)

    # Durations
    period = st.slider(_("Duration (weeks)"), 1, 30, value=10) * 7
    start_date = st.date_input(_("Simulation date"))

    # Seed
    st.subheader(_('Cases'))
    msg = _("Average new confirmed COVID-19 cases per day")
    cases = confirmed_daily_cases(region, disease) or 1
    cases = st.number_input(msg, 1, int(region.population), value=cases)

    msg = _("Notification rate (%)")
    notification = notification_estimate(region, disease)
    notification = 0.01 * st.slider(msg, 1.0, 100.0, max(1.0, 100.0 * notification))

    return {
        "period": period, "date": start_date, "daily_cases": cases / notification
    }


def healthcare_params(region, title=_("Hospital capacity"), occupancy=0.75, where=st):
    """
    Return a dictionary with hospital and icu capacities from user input.

    Returns:
        icu_capacity (float): surge system capacity of ICUs
        icu_full_capacity (float): total system capacity of ICUs
        hospital_capacity (float): surge system capacity of regular beds
        hospital_full_capacity (float): total system capacity of regular beds
    """

    region = mundi.region(region)
    where.header(title)

    def get(title, capacity, rate, key=None):
        where.subheader(title)

        total = where.number_input(
            _("Total capacity"),
            min_value=0,
            value=int(capacity),
            key=key + "_total",
        )
        rate = where.slider(
            _("Occupancy rate"),
            min_value=0,
            max_value=100,
            value=int(100 * rate),
            key=key + "_rate",
        )
        result = int(total * (100 - rate) / 100)
        msg = OCCUPANCY_MSG.format(
            n=fmt(result),
            occupancy=fmt(rate),
            occupancyglobal=fmt(100 * occupancy),
            pc="%",
        )
        html(f'<span style="font-size: smaller;">{msg}</span>', where=where)
        return result

    h_cap = safe_int(region.hospital_capacity)
    icu_cap = safe_int(region.icu_capacity)

    return {
        "icu_full_capacity": icu_cap,
        "hospital_full_capacity": h_cap,
        "icu_capacity": get(_("ICU beds"), icu_cap, occupancy, key="icu"),
        "hospital_capacity": get(_("Clinical beds"), h_cap, occupancy, key="hospital"),
    }


def select_intervention(duration, title=_("Intervention"), where=st) -> runner.Runner:
    """
    Return a dictionary with intervention parameters.

    Returns:
        runner, hospital_capacity (float): maximum system capacity
    """

    where.header(title)

    baseline, social_distance = interventions = [_("None"), _("Social distancing")]
    intervention = where.selectbox(_("Scenario"), interventions)

    if intervention == baseline:
        return runner.simple_runner()

    elif intervention == social_distance:
        step = 1
        html(f'<span style="font-size: smaller;">{INTERVENTION_TEXT}</span>', where=where)

        days_msg = _("Duration of intervention")
        rate_msg = _("Social isolation (0% represents no isolation)")
        msg_info = _('Intervention starts at day {} of simulation')

        where.subheader(_('First intervention'))

        # Read first intervention
        start = where.slider(_("Days before enacting"), 0, duration)
        duration -= start
        stages = [(start, 1)] if start else []

        size = where.slider(days_msg, 1, duration, duration)
        duration -= size

        rate = where.slider(rate_msg, value=15, step=step)
        stages.append((size, 1 - rate / 100))

        idx = 1
        key = None
        while duration > 0 and where.checkbox(_('Add more stages'), key=key):
            idx += 1
            key = f'intervention-{idx}'

            # header = where.empty()
            msg = _('Intervention {n}')
            where.subheader(msg.format(n=idx))

            size = where.slider(days_msg, 1, duration, min(7, duration), key='T-' + key)
            rate = where.slider(rate_msg, value=50, step=step, key='R-' + key)
            where.info(msg_info.format(start + size))

            stages.append((size, 1 - rate / 100))
            duration -= size
            start += size

        if duration > 0:
            stages.append((duration, 1.0))
        return runner.stage_runner(stages)

    else:
        raise RuntimeError


if __name__ == "__main__":
    import streamlit as st

    st.write(simulation_params("BR"))
    st.write(healthcare_params("BR"))
    st.write(select_intervention(120))
