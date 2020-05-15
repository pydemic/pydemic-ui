import datetime

import streamlit as st

from ..generic import html
from ..base import twin_component
from ... import runner
from ...i18n import _

DAY = datetime.timedelta(days=1)
INTERVENTION_TEXT = _("""
This intervention simulates a situation in which everyone reduces
the average number of encounters throughout the day. Small reductions (~15%) are
possible through small behavioral changes. Larger reductions require implementation
of many non-pharmacological measures.
""")


@twin_component()
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
    st.write(select_intervention(120))
