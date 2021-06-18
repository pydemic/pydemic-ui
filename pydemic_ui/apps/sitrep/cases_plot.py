from matplotlib import pyplot as plt

import mundi
from pydemic_ui import st
from pydemic_ui.i18n import _

DISPLAY_NAME = _("Accumulated cases")


def regions(*args, **kwargs):
    refs = mundi.regions_dataframe(*args, **kwargs).index
    return [mundi.region(ref) for ref in refs]


def show(
    regions,
    highlight,
    column="cases",
    logy=True,
    thresh=100,
    diff=False,
    smoothing=0,
    population_adj=False,
    where=st,
):
    st = where

    regions = set(regions)
    highlight = set(highlight)
    regions.difference_update(highlight)

    for opt, regs in [
        ({"color": "0.7", "legend": False}, regions),
        ({"legend": True, "lw": 2}, highlight),
    ]:
        for reg in regs:
            data = reg.pydemic.epidemic_curve(diff=diff)[column]
            if population_adj:
                data *= 1e6 / reg.population
            if smoothing:
                data = data.rolling(smoothing, center=True, min_periods=1).mean()
            data = data[data >= thresh].reset_index(drop=True)
            data.plot(logy=logy, grid=True, label=reg.name, **opt)
    plt.tight_layout()
    st.pyplot()


def options(where=st):
    st = where
    regs = regions("BR", type="state")

    # Regions to highlight
    st.subheader(_("Highlight"))
    opts = {
        "BR-1": _("North"),
        "BR-2": _("Northeast"),
        "BR-3": _("Southeast"),
        "BR-4": _("South"),
        "BR-5": _("Midwest"),
        "select": _("Select states"),
        # 'top5': _('Top 5'), NotImplemented
    }
    msg = _("Which states do you want to highlight?")
    opt = st.radio(msg, [*opts], format_func=opts.get)
    if opt == "select":
        fmt = {r.id: r.name for r in regs}.get
        ids = [r.id for r in regs]
        msg = _("Select states to highlight")
        select = set(st.multiselect(msg, ids, format_func=fmt, default=[regs[0].id]))
        highlight = [r for r in regs if r.id in select]
    elif opt == "top5":
        highlight = opt
    else:
        highlight = [r for r in regs if r.parent_id == opt]

    # Options
    st.subheader(_("Options"))
    logy = not st.checkbox(_("Linear scale"))

    column = "deaths" if st.checkbox(_("Plot deaths")) else "cases"

    diff = st.checkbox(_("Plot new daily cases"))

    population_adj = st.checkbox(_("Adjust for population"))

    default = (20 if diff else 100) // (1 if column == "cases" else 10)
    thresh = st.number_input(_("Minimum number of cases"), min_value=0, value=default)

    default = 7 if diff else 0
    smooth = st.number_input(_("Smooth over n days"), min_value=0, value=default)

    return {
        "regions": regs,
        "highlight": highlight,
        "diff": diff,
        "thresh": thresh,
        "smoothing": smooth,
        "column": column,
        "logy": logy,
        "population_adj": population_adj,
    }


def main(embed=False, where=st):
    show(**options(where=(st if embed else st.sidebar)), where=st)


if __name__ == "__main__":
    main()
