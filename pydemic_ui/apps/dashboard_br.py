import io
import pathlib
import zipfile
from datetime import timedelta
from types import MappingProxyType

import pandas as pd
import sidekick as sk

import mundi
from pydemic.region import RegionT
from pydemic.utils import extract_keys, today
from pydemic.utils import timed
from pydemic_ui import builtins
from pydemic_ui import st
from pydemic_ui.i18n import _
from pydemic_ui.lib.color_map import COLOR_MAPS
from pydemic_ui.lib.data_columns import dashboard_columns
from pydemic_ui.lib.data_sections import dashboard_sections
from pydemic_ui.lib.databases import paho_br_dataframe
from pydemic_ui.reports import pdf_from_template

PATH = pathlib.Path(__file__).parent
ASSETS = PATH.parent / "assets"
DAY = timedelta(days=1)
TTL = 2 * 3600
COLUMNS = dashboard_columns()
SECTIONS = dashboard_sections()


def main(embed=False, where=st, **kwargs):
    """
    Main application function.
    """

    st = where
    if not embed:
        st.css(keep_menu=True)
        st.sidebar.logo()
        st.title(_("Epidemic situation dashboard (Brazil)"))

    options = sidebar(where=st.sidebar)
    kwargs = extract_keys(("cmap", "static_table"), options)
    kwargs["where"] = where

    data = get_data()
    data = data.loc[options.pop("regions")]

    section_opt = options["section"]
    if section_opt == "download":
        download_data(data, **kwargs)
    else:
        section = SECTIONS[section_opt]
        section.show(data, **kwargs)


def sidebar(where=st.sidebar) -> dict:
    """
    Run sidebar that asks for user input.
    """

    st = where
    st.header(_("Brazilian Epidemiological indicators"))

    st.subheader(_("Sections"))
    opts = {k: v.title for k, v in SECTIONS.items()}
    opts["download"] = _("Download data")
    msg = _("Select a section")
    section = st.radio(msg, list(opts), format_func=opts.get)

    st.subheader(_("Filter results"))
    regions = select_regions(where=st)

    st.subheader(_("Options"))
    opts = {
        "static_table": st.checkbox(_("Static tables")),
        "cmap": st.selectbox(_("Colormap"), COLOR_MAPS, index=COLOR_MAPS.index("BuPu")),
    }

    return {"regions": regions, "section": section, **opts}


def download_data(data, cmap, where=st, **kwargs):
    opts = {
        "csv": _("Download tables as CSV"),
        "xlsx": _("Download tables as an Excel spreadsheet"),
        "maps": _("Download all maps in a ZIP file"),
        "pdf": _("Download a PDF with the complete report"),
    }
    opt = st.radio(_("What do you want?"), list(opts), format_func=opts.get)

    if opt in ("csv", "xlsx"):
        st.data_anchor(
            data,
            f"full-data-{today()}.{opt}",
            style=None,
            label=_("Click here to download the complete dataset."),
        )
    elif opt == "maps":
        fd = io.BytesIO()

        with zipfile.ZipFile(
            fd, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zip:
            for section in SECTIONS.values():
                rendered_cols = set()

                for col in section.columns:
                    if col.skip_choropleth or col in rendered_cols:
                        continue
                    rendered_cols.add(col)

                    name = f"{section.name}-{col.name}.svg"
                    svg = col.render_choropleth(data, cmap, kind="svg")
                    zip.writestr(name, svg)

        st.data_anchor(fd.getvalue(), filename=f"maps-{today()}.zip")

    elif opt == "pdf":
        ctx = {"sections": SECTIONS.values(), "data": data, "cmap": cmap}
        fd = pdf_from_template("dashboard-report", ctx)
        st.data_anchor(fd.read(), filename=f"report-{today()}.pdf")


@timed
@st.cache(show_spinner=False, ttl=TTL)
def region_data(region: RegionT):
    """
    Collect data from region.
    """
    data = dict(epidemic_data(region))
    if region.country_code == "BR" and region.type == "state":
        paho = sk.record(paho_br_state_data(region))

        data.update(
            # Update daily information since the PAHO database more carefully handle
            # "reports from the last 24h" than Brazil.io
            new_cases=paho.cases_24h,
            new_prevalence_today=1e5 * paho.cases_24h / region.population,
            new_deaths=paho.deaths_24h,
            new_mortality_today=1e5 * paho.deaths_24h / region.population,
            # Occupancy data
            hospital_occupancy=paho.hospital_occupancy,
            icu_occupancy=paho.icu_occupancy,
            # Policy
            isolation_score=paho.isolation_score,
            has_lockdown=bool(paho.n_cities_lockdown),
            lockdown_ratio=100 * paho.n_cities_lockdown / paho.n_cities,
            # Tests
            tests=paho.tests,
            tests_100k=1e5 * paho.tests / region.population,
            tests_positive=paho.tests_positive,
            tests_positive_ratio=100 * paho.tests_positive / paho.tests,
        )
    return MappingProxyType(data)


@timed
@st.cache(show_spinner=False, ttl=TTL)
def epidemic_data(region: RegionT) -> MappingProxyType:
    # Epidemic curves
    acc = region.pydemic.epidemic_curve()
    new = acc.diff().fillna(0)

    cases = acc["cases"].loc
    deaths = acc["deaths"].loc
    new_cases = new["cases"].loc
    new_deaths = new["deaths"].loc

    today = acc.index[-1]
    yesterday = today - DAY
    last15 = today - 15 * DAY

    population = region.population

    def epidemic_curve_info(col, alt=None, acc=acc, new=new):
        acc = acc[col].loc
        new = new[col].loc
        alt = alt or f"{col}_100k"
        delta = new[today] or new[yesterday]

        return {
            col: acc[today],
            f"{alt}": 1e5 * acc[today] / population,
            f"{alt}_15d": 1e5 * acc[last15] / population,
            f"new_{col}": delta,
            f"new_{alt}_today": 1e5 * delta / population,
            f"new_{alt}_15d": 1e5 * new[last15] / population,
        }

    public_ratio = lambda x: region[f"{x}_capacity_public"] / region[f"{x}_capacity"]
    return MappingProxyType(
        {
            "name": region.name,
            "short_code": region.short_code,
            "population": population,
            "hospital_pm": 1_000 * region.hospital_capacity / population,
            "icu_10k": 10_000 * region.icu_capacity / population,
            "hospital_public": 100 * public_ratio("hospital"),
            "icu_public": 100 * public_ratio("icu"),
            "CFR": 100 * deaths[today] / cases[today],
            "CFR_15d": 100 * new_deaths[last15:].sum() / new_cases[last15:].sum(),
            **epidemic_curve_info("cases", "prevalence"),
            **epidemic_curve_info("deaths", "mortality"),
        }
    )


def select_regions(where=st.sidebar):
    """
    Select regions for app.
    """
    st = where
    opts = {
        "BR": _("Brazil (everything)"),
        "BR-1": _("North Region"),
        "BR-2": _("Northeast Region"),
        "BR-3": _("Southeast Region"),
        "BR-4": _("South Region"),
        "BR-5": _("Center-West Region"),
    }
    opt = st.radio(_("What do you want to show?"), list(opts), format_func=opts.get)
    if opt == "BR":
        df = mundi.regions("BR", type="state")
    else:
        df = mundi.regions(type="state", parent_id=opt)
    return df.index


@timed
def get_data() -> pd.DataFrame:
    """
    Load full dataframe with information about all states.
    """
    return _get_data().copy()


@st.cache(ttl=TTL, allow_output_mutation=True)
def _get_data():
    states = fetch_states()
    state_codes = [state.id for state in states]
    return pd.DataFrame([*map(region_data, states)], index=state_codes)


@timed
@st.cache
def fetch_states():
    return tuple(map(mundi.region, mundi.regions("BR", type="state").index))


@timed
def paho_br_state_data(region: RegionT):
    """
    Retrieve data for a single state.
    """
    df = paho_br_dataframe("states")
    return df.loc[region.id].to_dict()


if __name__ == "__main__":
    main()
    builtins.reload("pydemic_ui.lib")
    builtins.reload("pydemic_ui.components")
    builtins.reload("pydemic_ui.st")
