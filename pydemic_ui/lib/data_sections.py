from typing import Tuple, Optional, Dict

import pandas as pd
import sidekick as sk
from pandas.io.formats.style import Styler

from pydemic.utils import timed
from .data_columns import Column, dashboard_columns
from .. import st
from ..i18n import _


class Section(sk.Record):
    """
    Represent a section that display several columns of a dataframe.
    """

    name: str
    title: str
    columns: Tuple[Column] = ()
    description: Optional[str] = None

    def __init__(self, name, title, columns=(), description=None):
        def to_col(col):
            return col if isinstance(col, Column) else col_data[col]

        col_data = dashboard_columns()
        columns = tuple(map(to_col, columns))
        super().__init__(name, title, columns, description)

    @timed
    def show(self, data, static_table=False, download=True, where=st, **kwargs):
        """
        Render section in streamlit.
        """

        st = where
        st.html('<div id="section"></div>')
        st.header(self.title)
        if self.description:
            st.markdown(self.description)
        where.html(self.render_index())

        for col in self.columns:
            if not col.skip_choropleth:
                col.show_choropleth(data, where=st, **kwargs)
        display = self.display_data(data)
        st.subheader(_("Raw data"))
        st.html('<div id="raw-data"></div>')
        self.show_table(display, static_table=static_table, download=download, where=st)

    @timed
    def show_table(self, data, static_table=False, download=True, where=st):
        """
        Show table with data
        """
        if static_table:
            where.table(data)
        else:
            where.dataframe(data)
        if download:
            st.data_anchor(data, f"{self.name}-data.csv")

    @timed
    def display_data(self, data: pd.DataFrame) -> Styler:
        """
        Return a Styled dataframe.
        """
        columns = [col.name for col in self.columns]
        fmt = {col.name: col.fmt for col in self.columns if col.fmt}
        return (
            data[columns]
            .style.format(fmt, na_rep="-")
            .highlight_max(color="red")
            .highlight_min(color="green")
        )

    def render_index(self) -> str:
        """
        Render index as HTML.
        """
        subsections = _("Quick links")
        lines = [f'<div id="section-toc">{subsections}</div><ul>']
        for col in self.columns:
            if not col.skip_choropleth:
                lines.append(f'<li><a href="#choropleth-{col.name}">{col.title}</a></li>')
        raw_data = _("Raw data")
        lines.append(f'<li><a href="#raw-data">{raw_data}</a></li>')
        lines.append("</ul>")
        return "\n".join(lines)


#
# Initialize Dashboard sections
#
@sk.once
def dashboard_sections() -> Dict[str, Section]:
    return {
        sec.name: sec
        for sec in (
            Section(
                "basic",
                title=_("Basic information"),
                columns=["name", "short_code", "population"],
                description=_("Basic parameters"),
            ),
            Section(
                "healthcare_system",
                title=_("Healthcare system"),
                columns=[
                    "hospital_pm",
                    "icu_10k",
                    "hospital_public",
                    "icu_public",
                    "hospital_occupancy",
                    "icu_occupancy",
                ],
                description=_("Healthcare system data was collected from CNES."),
            ),
            Section(
                "acc_cases",
                title=_("Prevalence"),
                columns=["cases", "prevalence", "prevalence_15d"],
            ),
            Section(
                "acc_deaths",
                title=_("Mortality"),
                columns=["deaths", "mortality", "mortality_15d"],
            ),
            Section(
                "new_cases",
                title=_("Active cases"),
                columns=["new_cases", "new_prevalence_today", "new_prevalence_15d"],
            ),
            Section(
                "new_deaths",
                title=_("Death rate"),
                columns=["new_deaths", "new_mortality_today", "new_mortality_15d"],
            ),
            Section("fatality", title=_("Fatality rates"), columns=["CFR", "CFR_15d"]),
            Section(
                "policy",
                title=_("Policy and behavior"),
                columns=["isolation_score", "has_lockdown", "lockdown_ratio"],
            ),
            Section(
                "tests",
                title=_("Testing"),
                columns=["tests", "tests_100k", "tests_positive", "tests_positive_ratio"],
            ),
        )
    }
