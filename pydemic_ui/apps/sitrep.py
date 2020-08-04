from typing import List

import pandas as pd
from matplotlib import pyplot as plt

import mundi
import sidekick as sk
from mundi import Region
from pydemic.utils import fmt, pc
from pydemic_ui import st
from pydemic_ui.app import SimpleApp
from pydemic_ui.apps.sitrep import abstract, cases_or_deaths, cases_plot
from pydemic_ui.i18n import _, __

APPS = {
    "abstract": abstract,
    "cases_or_deaths": cases_or_deaths,
    "cases_plot": cases_plot,
}


class ReportCasesTableApp(SimpleApp):
    """
    A simple table-centric situation report.

    It shows the number of cases and deaths in the last 14 and 28 days for each
    sub-region in the selected query.
    """

    message = __(
        """
The highest increase in the reported case rate in the last 14 days was observed in
the  {self.max_cases_region} region, followed by the {self.other_cases_regions} regions.

The highest increase in the mortality rate in the last 14 days was observed in the
{self.max_deaths_region}, followed by the {self.other_deaths_regions} regions.
"""
    )

    mundi_query = {"country_id": "BR", "type": "state"}

    @sk.lazy
    def regions(self) -> List[Region]:
        """
        Return a list of regions
        """
        return regions(**self.mundi_query)

    @sk.lazy
    def tables(self):
        """
        Compute tables by state and by region.
        """

        def get_data(rs):
            data = [*map(info, rs)]
            index = [r.id for r in rs]
            data = pd.DataFrame(data, index=index)
            data.columns = pd.MultiIndex.from_tuples(data.columns)

            dtypes = {col: float for col in data.dtypes.keys()}
            dtypes["", "name"] = str
            return data.astype(dtypes)

        parent_ids = sorted({r.parent_id for r in self.regions})
        parents = [*map(mundi.region, parent_ids)]
        return get_data(parents), get_data(self.regions)

    def _max_region(self, col):
        data, _ = self.tables
        names = data[col].sort_values()
        return mundi.region(names.index[-1]).name

    def _other_regions(self, col):
        data, _ = self.tables
        names = data.sort_values(col).mundi["name"]
        *other, last = names.iloc[1:]
        other = ", ".join(other)
        if other:
            return _(" and ").join([other, last])
        return last

    @sk.lazy
    @sk.ignore_error(AttributeError, handler=str)
    def max_cases_region(self):
        return self._max_region(("14 days", "cases"))

    @sk.lazy
    @sk.ignore_error(AttributeError, handler=str)
    def max_deaths_region(self):
        return self._max_region(("14 days", "deaths"))

    @sk.lazy
    @sk.ignore_error(AttributeError, handler=str)
    def other_cases_regions(self):
        return self._other_regions(("14 days", "cases"))

    @sk.lazy
    @sk.ignore_error(AttributeError, handler=str)
    def other_deaths_regions(self):
        return self._other_regions(("14 days", "deaths"))

    def ask(self):
        ...

    def show(self):
        by_region, by_state = self.tables
        self.st.markdown(self.message.format(self=self))

        self.st.subheader(_("Epidemic situation, by region"))
        self.st.markdown(_("Cases and deaths by 100k people."))
        self.show_table(by_region)

        self.st.subheader(_("Epidemic situation, by state"))
        self.st.markdown(_("Cases and deaths by 100k people."))
        self.show_table(by_state)

    def show_table(self, data):
        self.st.write(
            data.style_dataframe.format(fmt)
            .format({("increase", x): pc for x in ["cases", "deaths"]})
            .highlight_max(axis=0, color="red")
            .highlight_min(axis=0, color="green")
        )


def groupby_parent(data, column="parent_id"):
    parents_col = pd.DataFrame({column: parents(data.index)})
    new = pd.concat([data, parents_col], axis=1)
    return new.groupby(column)


def parents(lst):
    parents = [mundi.region(ref).parent_id for ref in lst]
    return pd.Series(parents, index=lst)


def info(region):
    curve = region.pydemic.epidemic_curve(diff=True)
    last = 1e5 * curve.iloc[-14:].sum() / region.population
    prev = 1e5 * curve.iloc[-28:-14].sum() / region.population
    increase = last / prev - 1

    def prefix(value):
        return {k: (value, k) for k in last.index}

    return {
        ("", "name"): region.name,
        **last.rename(prefix("14 days")).to_dict(),
        **prev.rename(prefix("28 days")).to_dict(),
        **increase.rename(prefix("increase")).to_dict(),
    }


def regions(*args, **kwargs):
    refs = mundi.regions(*args, **kwargs).index
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


APPS["cases_plot"] = sk.record(
    show=show, options=options, DISPLAY_NAME=_("Accumulated cases")
)


def sidebar(where=st.sidebar):
    st = where

    st.subheader(_("Section"))
    msg = _("Which section do you want to see?")
    key = st.radio(msg, list(APPS), format_func=lambda x: APPS[x].DISPLAY_NAME)
    app = APPS[key]
    opts = app.options(where=where)
    return app.show, opts


def main(**kwargs):
    app = ReportCasesTableApp(title=_("Mortality rate and reported cases"))
    app.run()
    # st.css(keep_menu=True)
    # st.logo(where=st.sidebar)
    # st.title(_('Situation report'))
    # run, opts = sidebar()
    # run(**opts)


if __name__ == "__main__":
    main()
