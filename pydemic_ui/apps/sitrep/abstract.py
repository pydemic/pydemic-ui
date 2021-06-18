import pandas as pd

import mundi
import sidekick as sk
from pydemic_ui import st
from pydemic_ui.i18n import _

DISPLAY_NAME = _("Abstract")
ABSTRACT = _(
    """
## Update from the last 24 hours (as {date} Brasilia Time)

**{cases}** additional cases and **{deaths}** additional deaths reported from
all {n_children} {unit_kind};

The {n_top_cases} {unit_kind} reporting the highest number of cases in the
last 24 hours: {top_cases}.

The {n_top_deaths} {unit_kind} reporting the highest number of deaths in the
past 24 hours: {top_deaths}.
"""
)


def abstract(*args, where=st, **kwargs):
    """
    Print the abstract of the situation report.
    """
    where.markdown(abstract_str(*args, **kwargs))


@st.cache
def abstract_str(top=10, kind=_("Federal Units"), date=None):
    """
    Create a markdown string with an abstract to the dashboard.
    """

    children_refs = mundi.regions_dataframe(country_id="BR", type="state").index
    children = [mundi.region(ref) for ref in children_refs]
    n_children = len(children)

    curves = [child.pydemic.epidemic_curve().diff() for child in children]
    date = date or max(curve.index.max() for curve in curves)
    cases = pd.Series([c.loc[date, "cases"] for c in curves], index=children_refs)
    deaths = pd.Series([c.loc[date, "deaths"] for c in curves], index=children_refs)

    def list_top(data: pd.Series):
        *head, last = sk.pipe(
            data.sort_values(ascending=False).index[:top],
            sk.map(mundi.region),
            sk.map("{0.name}".format),
        )
        head = ", ".join(head)
        return _(" and ").join([head, last])

    return _(ABSTRACT).format(
        cases="{:n}".format(cases.sum()),
        deaths="{:n}".format(deaths.sum()),
        date=date,
        n_children=n_children,
        n_top_cases=min(top, n_children),
        n_top_deaths=min(top, n_children),
        top_cases=list_top(cases),
        top_deaths=list_top(deaths),
        unit_kind=_(kind),
    )


def options(where=st):
    return {}


def show(where=st):
    abstract()


def main(embed=False, where=st):
    show(**options(where=(st if embed else st.sidebar)), where=st)


if __name__ == "__main__":
    main()
