import io
from typing import Union, Callable, Optional, Dict

import sidekick as sk
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from pydemic.utils import fmt, timed
from .color_map import reverse_cmap
from .geo import brazil_map
from .. import info
from .. import st
from ..components import render_svg
from ..i18n import _


class Column(sk.Record):
    """
    Represents a single column of information in a dataframe.
    """

    name: str
    title: str
    fmt: Union[str, Callable, None] = fmt
    description: Optional[str] = None
    skip_choropleth: bool = False
    positive: bool = False

    @timed
    def show_choropleth(self, data, cmap="BuPu", where=st):
        st.html(f'<div id="choropleth-{self.name}"></div>')
        where.subheader(self.title)
        if self.description:
            st.markdown(self.description)
        data = self.render_choropleth(data, cmap, "img")
        where.html(data)
        link = '<a href="#section" style="display: block; text-align: right;">{back}</a>'
        where.html(link.format(back=_("^ Back")))

    def render_choropleth(self, data, cmap="BuPu", kind="svg"):
        """
        Return a SVG string with the choropleth representing the column of data.
        """
        if kind == "svg":
            return get_map_pyplot(
                data[self.name], self.name, self.title, cmap, self.positive
            )
        elif kind == "img":
            return render_svg(self.render_choropleth(data, cmap, "svg"))
        else:
            raise ValueError(f"invalid kind: {kind}")


@timed
@info.ttl_cache(force_streamlit=True)
def get_map_pyplot(data, name, title, cmap, is_positive) -> str:
    """
    Some message
    """

    with st.spinner(_('Creating plot "{title}"').format(title=title)):
        geo = brazil_map().loc[data.index]
        geo[name] = data
        ax: Axes = geo.plot(
            column=name,
            legend=True,
            cmap=reverse_cmap(cmap) if is_positive else cmap,
            edgecolor="black",
            legend_kwds={"label": title},
            missing_kwds={"color": "white", "hatch": "///", "label": _("Missing values")},
        )
        fd = io.StringIO()
        ax.set_axis_off()
        plt.tight_layout()
        plt.savefig(fd, format="svg")
        return fd.getvalue()


#
# Columns for specific apps
#
@sk.once
def dashboard_columns() -> Dict[str, Column]:
    return {
        col.name: col
        for col in (
            #
            # Basic info
            #
            Column("name", title=_("Region name"), skip_choropleth=True),
            Column(
                "population",
                title=_("Population"),
                description=_("Total population estimated for 2020"),
                skip_choropleth=True,
            ),
            Column("short_code", title=_("IBGE Code"), skip_choropleth=True),
            #
            # Healthcare system
            #
            Column(
                "hospital_pm",
                title=_("Hospital beds per 1k"),
                description=_("Number of hospital beds per 1.000 people."),
                positive=True,
            ),
            Column(
                "icu_10k",
                title=_("ICU beds per 10k"),
                description=_("Number of ICUs per 10.000 people."),
                positive=True,
            ),
            Column(
                "hospital_public",
                title=_("Fraction of public hospital beds"),
                fmt="{:02.2n}%",
                description=_("Fraction of hospital beds belonging to SUS"),
                positive=True,
            ),
            Column(
                "icu_public",
                title=_("Fraction of public ICUs"),
                fmt="{:02.2n}%",
                description=_("Fraction of ICUs belonging to SUS"),
                positive=True,
            ),
            Column(
                "hospital_occupancy",
                title=_("Fraction of occupied beds"),
                fmt="{:02.2n}%",
            ),
            Column(
                "icu_occupancy", title=_("Fraction of occupied ICUs"), fmt="{:02.2n}%"
            ),
            #
            # Prevalence
            #
            Column(
                "cases",
                title=_("Confirmed cases"),
                fmt="{:n}",
                description=_("Confirmed cases"),
                skip_choropleth=True,
            ),
            Column(
                "prevalence",
                title=_("Prevalence per 100k"),
                description=_(
                    "This data point only considers the prevalence of confirmed cases."
                ),
            ),
            Column(
                "prevalence_15d",
                title=_("Prevalence per 100k (15 days ago)"),
                description=_("Confirmed prevalence 15 days ago."),
            ),
            Column(
                "prevalence_30d",
                title=_("Prevalence per 100k (30 days ago)"),
                description=_("Confirmed prevalence er 100k people 30 days ago."),
            ),
            #
            # Mortality
            #
            Column(
                "deaths",
                title=_("Confirmed Deaths"),
                fmt="{:n}",
                description=_("Confirmed deaths"),
                skip_choropleth=True,
            ),
            Column(
                "mortality",
                title=_("Mortality"),
                description=_("Official count of mortality per 100k people."),
            ),
            Column("mortality_15d", title=_("Mortality (15 days ago)")),
            Column("mortality_30d", title=_("Mortality (30 days ago)")),
            #
            # Infectiousness
            #
            Column(
                "new_cases", title=_("Confirmed cases (last 24h)"), skip_choropleth=True
            ),
            Column(
                "new_prevalence_today",
                title=_("Prevalence increment (last 24h)"),
                description=_("Confirmed cases per 100k (last 24h)"),
            ),
            Column(
                "new_prevalence_15d",
                title=_("Prevalence increment (last 15 days)"),
                description=_("Confirmed cases per 100k (last 15 days)"),
            ),
            #
            # Mortality rate
            #
            Column(
                "new_deaths", title=_("Confirmed deaths (last 24h)"), skip_choropleth=True
            ),
            Column(
                "new_mortality_today",
                title=_("Mortality increment (last 24h)"),
                description=_("Confirmed deaths per 100k (last 24h)"),
            ),
            Column(
                "new_mortality_15d",
                title=_("Mortality increment (last 15 days)"),
                description=_("Confirmed deaths per 100k (last 15 days)"),
            ),
            #
            # Fatality ratios
            #
            Column(
                "CFR",
                title=_("CFR"),
                fmt="{:.3n}%",
                description=_(
                    'Empirical case fatality ratio computed as "confirmed deaths" / '
                    '"confirmed cases".'
                ),
            ),
            Column(
                "CFR_15d",
                title=_("CFR 15 days ago"),
                fmt="{:.3n}%",
                description=_("Case fatality ratio 15 days ago."),
            ),
            #
            # Policy
            #
            Column(
                "isolation_score",
                title=_("Isolation score"),
                fmt="{:.2n}%",
                positive=True,
                description=_(
                    "Isolation score by InLoco. It roughthly measures the reduction in "
                    "the "
                    "average number of contacts throughout the day."
                ),
            ),
            Column(
                "has_lockdown",
                title=_("Has lockdown?"),
                description=_("True, if has at least one city in lockdown"),
            ),
            Column("lockdown_ratio", title=_("lockdown_ratio"), fmt="{:.2n}%"),
            #
            # Tests
            #
            Column(
                "tests",
                title=_("Total number of tests"),
                positive=True,
                skip_choropleth=True,
            ),
            Column("tests_100k", title=_("Tests per 100k population"), positive=True),
            Column("tests_positive", title=_("tests_positive"), skip_choropleth=True),
            Column(
                "tests_positive_ratio", title=_("tests_positive_ratio"), fmt="{:.2n}%"
            ),
        )
    }
