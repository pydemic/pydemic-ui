from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd

import mundi
from pydemic.region import RegionT
from pydemic.utils import trim_zeros
from pydemic_ui import st
from pydemic_ui.i18n import _

DISPLAY_NAME = _("Cases and deaths graph")
CASES_ABSTRACT = _(
    """
The **{region}** region has reported the highest number of cases in the
last 24 hours (**{cases_total}**). {state} is the state with the highest
number of reported cases in the last 24 hours (**{cases_state}** additional cases).
"""
)

DEATHS_ABSTRACT = _(
    """
The highest number of deaths in the last 24 hours (**{deaths_total}**) was reported in
the
{region} region with {state} state reporting **{deaths}** deaths in the last 24 hours.
"""
)


def epidemic_curves_plot(
    regions: Sequence[RegionT],
    smooth_windows=(7, 2),
    column="cases",
    where=st,
    lines=False,
    logy=False,
    **kwargs
):
    st = where
    data = epidemic_curves_data(regions, column, **kwargs)
    names = {r.id: r.name for r in regions}
    window_lines, window_bar = smooth_windows

    if lines:
        (
            data.rename(columns=names)
            .rolling(window_lines, center=True, min_periods=1)
            .mean()
            .plot(logy=logy, grid=True)
        )

    else:
        (
            data.rename(columns=names)
            .rolling(window_bar, center=True)
            .mean()
            .plot(kind="bar", grid=True, stacked=True, width=1)
        )
        xticks = plt.xticks()[0][::7]
        dates = pd.to_datetime(xticks, unit="D", origin=data.index[0])
        dates = [d.strftime("%d/%m") for d in dates]
        plt.xticks(xticks, dates, rotation=45)

    plt.ylim((0, None))
    plt.tight_layout()
    st.pyplot()


@st.cache
def epidemic_curves_data(
    regions: Sequence[RegionT], column: str, **kwargs
) -> pd.DataFrame:
    """
    From a list of regions, create a dataframe with the epidemic curves for all
    regions.

    Region ids are columns and rows are associated with each unique date.

    Args:
        regions:
            Sequence or regions
        column:
            Column used to extract data. Can be either "case" or "deaths"

    """
    frames = {}
    for region in regions:
        data = region.pydemic.epidemic_curve(**kwargs)[column]
        data = trim_zeros(data)
        data = data.where(data > 0, 0.0)
        frames[region.id] = data
    return pd.DataFrame(frames).fillna(0).astype(int)


def regions(*args, **kwargs):
    refs = mundi.regions_dataframe(*args, **kwargs).index
    return [mundi.region(ref) for ref in refs]


def options(where=st.sidebar):
    st = where

    opts = {
        None: _("Brazil"),
        "BR-1": _("North"),
        "BR-2": _("Northeast"),
        "BR-3": _("Southeast"),
        "BR-4": _("South"),
        "BR-5": _("Midwest"),
    }
    st.subheader(_("Region"))
    opt = st.radio(_("Select region"), [*opts], format_func=opts.get)
    if opt is None:
        regs = regions("BR", type="region", parent_id="BR")
    else:
        regs = regions(type="state", parent_id=opt)

    opts = {"cases": _("Cases"), "deaths": _("Deaths")}
    msg = _("Cases or deaths?")
    column = st.radio(msg, [*opts], format_func=opts.get)

    st.subheader(_("Plotting options"))
    lines = st.checkbox(_("Show Lines"))
    logy = False
    if lines:
        logy = st.checkbox(_("Logarithm scale"))

    return {"lines": lines, "logy": logy, "regions": regs, "column": column}


def show(regions, **kwargs):
    epidemic_curves_plot(regions, diff=True, **kwargs)


def main(embed=False, where=st):
    show(**options(where=(st if embed else st.sidebar)), where=st)


if __name__ == "__main__":
    main()
