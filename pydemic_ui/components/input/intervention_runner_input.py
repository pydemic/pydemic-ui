__package__ = "pydemic_ui.components.input"

import datetime

import streamlit as st

from ..base import twin_component
from ..generic import html
from ... import runner
from ...i18n import _, __

DAY = datetime.timedelta(days=1)
INTERVENTION_TEXT = __(
    """
This intervention simulates a situation in which everyone reduces
the average number of contacts throughout the day. Small reductions (~15%) are
possible through small behavioral changes. Larger reductions require implementation
of many non-pharmacological measures.
"""
)


@twin_component()
def intervention_runner_input(
    duration, title=__("Intervention"), where=st
) -> runner.Runner:
    """
    Return a dictionary with intervention parameters.

    Returns:
        runner, hospital_capacity (float): maximum system capacity
    """

    where.header(str(title))

    opts = {"baseline": _("None"), "distancing": _("Social distancing")}
    intervention = where.selectbox(_("Scenario"), list(opts), format_func=opts.get)

    if intervention == "baseline":
        return runner.simple_runner()

    elif intervention == "distancing":
        step = 1
        html(f'<span style="font-size: smaller;">{INTERVENTION_TEXT}</span>', where=where)

        days_msg = _("Duration of intervention (days)")
        msg_info = _("Intervention starts at day {} of simulation")
        rate_msg = _("Expected social isolation (0{pc} represents no isolation)")
        rate_msg_now = _("Initial social isolation (0{pc} represents no isolation)")

        # Error in pybabel extracting strings with % signs?
        rate_msg = rate_msg.format(pc="%")
        rate_msg_now = rate_msg_now.format(pc="%")

        where.subheader(_("First intervention"))

        # Read first intervention
        if not where.checkbox(_("Start intervention immediately"), value=True):
            start = where.slider(
                _("How many days before intervention start?"),
                1,
                duration,
                value=min(7, duration),
            )
        else:
            start = 0

        duration -= start
        stages = [(start, 1)] if start else []

        size = where.slider(days_msg, 1, duration, duration)
        duration -= size

        msg = rate_msg_now if start == 0 else rate_msg
        rate = where.slider(msg, value=15, step=step)
        stages.append((size, 1 - rate / 100))

        idx = 1
        key = None
        while duration > 0 and where.checkbox(_("Add more stages"), key=key):
            idx += 1
            key = f"intervention-{idx}"

            # header = where.empty()
            msg = _("Intervention {n}")
            where.subheader(msg.format(n=idx))

            size = where.slider(days_msg, 1, duration, min(7, duration), key="T-" + key)
            rate = where.slider(rate_msg, value=50, step=step, key="R-" + key)
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
    st.write(intervention_runner_input(120))
