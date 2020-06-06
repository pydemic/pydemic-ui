import base64
import io
import pathlib
import time
from collections import Counter
from contextlib import contextmanager
from datetime import timedelta
from functools import wraps, lru_cache
from types import MappingProxyType
from typing import Tuple, Union, Callable, Optional, Dict

import geopandas
import pandas as pd
import requests
import sidekick as sk
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from pandas.io.formats.style import Styler

import mundi
from pydemic.region import RegionT
from pydemic.utils import extract_keys, fmt
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui.i18n import _

PATH = pathlib.Path(__file__).parent
DAY = timedelta(days=1)
TTL = 2 * 3600
CHECKBOX = False
PERF_LOG = []
PERF_TRACK = True


@contextmanager
def timeit():
    """
    A timer context manager.

    Examples:
        >>> with timeit() as timer:
        ...     do_something()
        ... print('Start time:', timer.start)
        ... print('Elapsed time:', timer.delta)
        ... print('Keep track of time inside with block:', timer())
    """
    t0 = time.time()
    fn = lambda: time.time() - t0 if fn.delta is None else fn.delta
    fn.start = t0
    fn.delta = None
    try:
        yield fn
    finally:
        fn.delta = time.time() - t0


@contextmanager
def log_timing(key):
    """
    A timer that saves results as a key in PERF_LOG.
    """
    try:
        with timeit() as timer:
            yield
    finally:
        PERF_LOG.append((key, timer.delta))


def timed(fn):
    """
    Tracks timing of function execution.
    """
    if PERF_TRACK:

        @wraps(fn)
        def decorated(*args, **kwargs):
            with timeit() as timer:
                res = fn(*args, **kwargs)
            PERF_LOG.append((decorated, timer.delta))
            return res

        return decorated
    else:
        return fn


def show_perf_log():
    n_calls = Counter()
    tot_time = Counter()
    for k, v in PERF_LOG:
        k = getattr(k, "__name__", k)
        n_calls[k] += 1
        tot_time[k] += v
    df = pd.DataFrame({"n_calls": pd.Series(n_calls), "tot_time": pd.Series(tot_time)})
    st.write(df)


def render_svg(svg):
    """Renders the given svg string."""
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return r'<img src="data:image/svg+xml;base64,%s"/>' % b64


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

    for opt, show in options.items():
        if show:
            section = SECTIONS[opt]
            section.show(data, **kwargs)


def sidebar(where=st.sidebar) -> dict:
    """
    Run sidebar that asks for user input.
    """

    st = where
    st.header(_("Brazilian Epidemiological indicators"))

    st.subheader(_("Sections"))
    if CHECKBOX:
        extra = {k: st.checkbox(v.title, value=True) for k, v in SECTIONS.items()}
    else:
        opts = {k: v.title for k, v in SECTIONS.items()}
        msg = _("Select a section")
        extra = {st.radio(msg, list(opts), format_func=opts.get): True}

    st.subheader(_("Filter results"))
    regions = select_regions(where=st)

    st.subheader(_("Options"))
    opts = {
        "static_table": st.checkbox(_("Static tables")),
        "cmap": st.selectbox(_("Colormap"), COLOR_MAPS, index=COLOR_MAPS.index("BuPu")),
    }

    return {"regions": regions, **extra, **opts}


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
def brazil_map() -> geopandas.GeoDataFrame:
    """
    Load shape files and return a GeoDataFrame with the Brazillian map.
    """
    return _brazil_map().copy()


@lru_cache(1)
@st.cache
def _brazil_map():
    num_codes = (
        mundi.regions("BR", type="state")
        .mundi["numeric_code"]
        .astype(object)["numeric_code"]
        .to_dict()
    )
    translate = {v: k for k, v in num_codes.items()}
    geo = geopandas.read_file(PATH.parent / "databases/maps/br/estados.dbf")[
        ["CD_GEOCUF", "geometry"]
    ]
    geo.index = geo.pop("CD_GEOCUF").apply(translate.__getitem__)
    geo["geometry"] = geo.simplify(0.1)
    return geo


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


#
# PAHO/OMS database
#

# Originally at
# "https://docs.google.com/spreadsheets/d/1go3gYrgKsMmlGpHv9XGAACdk2T7XHSf7lOKDyfRfFak
# /export?format=xlsx"
OPAS_DATABASE_URL = "https://github.com/pydemic/databases/raw/master/paho_info.xlsx"


@timed
@info.ttl_cache(force_joblib=True)
def paho_br_xlsx() -> bytes:
    return requests.get(OPAS_DATABASE_URL).content


@timed
@st.cache(ttl=2 * 3600)
def paho_br_dataframe(sheet) -> pd.DataFrame:
    content = paho_br_xlsx()
    fd = io.BytesIO(content)
    if sheet == "states":
        drop_columns = [
            "chave",
            "Região",
            "Estados",
            "codigo_UF",
            "data de referencia",
            "taxa positividade",
            "Link taxa de ocupação",
        ]
        rename_columns = {
            "sigla_UF": "id",
            "População": "population",
            "índice in loco": "isolation_score",
            "estado tem lockdown": "has_lockdown",
            "Municipios em lockdown": "n_cities_lockdown",
            "Total de municipios": "n_cities",
            "Taxa de ocupaçao clínicos": "hospital_occupancy",
            "Taxa ocupação UTI": "icu_occupancy",
            "Testes realizados": "tests",
            "Testes positivos": "tests_positive",
            "Casos novos ultimas 24 horas": "cases_24h",
            "Obitos ultimas 24 horas": "deaths_24h",
        }
        df = (
            pd.read_excel(fd, key="Estados", skipfooter=1)
            .drop(columns=drop_columns)
            .rename(columns=rename_columns)
            .astype({"id": "str"})
        )
        df.index = "BR-" + df.pop("id")

        # Replace "Not available" in occupancy columns
        for col in ("icu_occupancy", "hospital_occupancy"):
            series = df[col]
            if series.dtype != float:
                series = series.replace({"Not available": "nan", "": "nan"}).astype(float)
                df[col] = series
        return df
    else:
        raise ValueError


@timed
def paho_br_state_data(region: RegionT):
    """
    """
    df = paho_br_dataframe("states")
    return df.loc[region.id].to_dict()


#
# Color maps
#
COLOR_MAPS = [
    "Accent",
    "Accent_r",
    "Blues",
    "Blues_r",
    "BrBG",
    "BrBG_r",
    "BuGn",
    "BuGn_r",
    "BuPu",
    "BuPu_r",
    "CMRmap",
    "CMRmap_r",
    "Dark2",
    "Dark2_r",
    "GnBu",
    "GnBu_r",
    "Greens",
    "Greens_r",
    "Greys",
    "Greys_r",
    "OrRd",
    "OrRd_r",
    "Oranges",
    "Oranges_r",
    "PRGn",
    "PRGn_r",
    "Paired",
    "Paired_r",
    "Pastel1",
    "Pastel1_r",
    "Pastel2",
    "Pastel2_r",
    "PiYG",
    "PiYG_r",
    "PuBu",
    "PuBuGn",
    "PuBuGn_r",
    "PuBu_r",
    "PuOr",
    "PuOr_r",
    "PuRd",
    "PuRd_r",
    "Purples",
    "Purples_r",
    "RdBu",
    "RdBu_r",
    "RdGy",
    "RdGy_r",
    "RdPu",
    "RdPu_r",
    "RdYlBu",
    "RdYlBu_r",
    "RdYlGn",
    "RdYlGn_r",
    "Reds",
    "Reds_r",
    "Set1",
    "Set1_r",
    "Set2",
    "Set2_r",
    "Set3",
    "Set3_r",
    "Spectral",
    "Spectral_r",
    "Wistia",
    "Wistia_r",
    "YlGn",
    "YlGnBu",
    "YlGnBu_r",
    "YlGn_r",
    "YlOrBr",
    "YlOrBr_r",
    "YlOrRd",
    "YlOrRd_r",
    "afmhot",
    "afmhot_r",
    "autumn",
    "autumn_r",
    "binary",
    "binary_r",
    "bone",
    "bone_r",
    "brg",
    "brg_r",
    "bwr",
    "bwr_r",
    "cividis",
    "cividis_r",
    "cool",
    "cool_r",
    "coolwarm",
    "coolwarm_r",
    "copper",
    "copper_r",
    "cubehelix",
    "cubehelix_r",
    "flag",
    "flag_r",
    "gist_earth",
    "gist_earth_r",
    "gist_gray",
    "gist_gray_r",
    "gist_heat",
    "gist_heat_r",
    "gist_ncar",
    "gist_ncar_r",
    "gist_rainbow",
    "gist_rainbow_r",
    "gist_stern",
    "gist_stern_r",
    "gist_yarg",
    "gist_yarg_r",
    "gnuplot",
    "gnuplot2",
    "gnuplot2_r",
    "gnuplot_r",
    "gray",
    "gray_r",
    "hot",
    "hot_r",
    "hsv",
    "hsv_r",
    "inferno",
    "inferno_r",
    "jet",
    "jet_r",
    "magma",
    "magma_r",
    "nipy_spectral",
    "nipy_spectral_r",
    "ocean",
    "ocean_r",
    "pink",
    "pink_r",
    "plasma",
    "plasma_r",
    "prism",
    "prism_r",
    "rainbow",
    "rainbow_r",
    "seismic",
    "seismic_r",
    "spring",
    "spring_r",
    "summer",
    "summer_r",
    "tab10",
    "tab10_r",
    "tab20",
    "tab20_r",
    "tab20b",
    "tab20b_r",
    "tab20c",
    "tab20c_r",
    "terrain",
    "terrain_r",
    "twilight",
    "twilight_r",
    "twilight_shifted",
    "twilight_shifted_r",
    "viridis",
    "viridis_r",
    "winter",
    "winter_r",
]


def reverse_cmap(cmap):
    """
    Reverse the color map.
    """
    if cmap.endswith("_r"):
        return cmap[:-2]
    return cmap + "_r"


#
# Columns metadata
#
class Column(sk.Record):
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
        data = get_map_pyplot(data[self.name], self.name, self.title, cmap, self.positive)
        where.html(data)
        link = '<a href="#section" style="display: block; text-align: right;">{back}</a>'
        where.html(link.format(back=_("^ Back")))


@timed
@info.ttl_cache(force_streamlit=True)
def get_map_pyplot(data, name, title, cmap, is_positive) -> bytes:
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
        return render_svg(fd.getvalue())


COLUMNS: Dict[str, Column] = {
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
            "hospital_occupancy", title=_("Fraction of occupied beds"), fmt="{:02.2n}%"
        ),
        Column("icu_occupancy", title=_("Fraction of occupied ICUs"), fmt="{:02.2n}%"),
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
        Column("new_cases", title=_("Confirmed cases (last 24h)"), skip_choropleth=True),
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
                "Isolation score by InLoco. It roughthly measures the reduction in the "
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
            "tests", title=_("Total number of tests"), positive=True, skip_choropleth=True
        ),
        Column("tests_100k", title=_("Tests per 100k population"), positive=True),
        Column("tests_positive", title=_("tests_positive"), skip_choropleth=True),
        Column("tests_positive_ratio", title=_("tests_positive_ratio"), fmt="{:.2n}%"),
    )
}


#
# Section data
#
class Section(sk.Record):
    name: str
    title: str
    columns: Tuple[Column] = ()
    description: Optional[str] = None

    def __init__(self, name, title, columns=(), description=None):
        def to_col(col):
            return col if isinstance(col, Column) else COLUMNS[col]

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
        self.show_index()

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

    @timed
    def show_index(self, where=st):
        subsections = _("Quick links")
        lines = [f'<div id="section-toc">{subsections}</div><ul>']
        for col in self.columns:
            if not col.skip_choropleth:
                lines.append(f'<li><a href="#choropleth-{col.name}">{col.title}</a></li>')
        raw_data = _("Raw data")
        lines.append(f'<li><a href="#raw-data">{raw_data}</a></li>')
        lines.append("</ul>")
        return where.html("\n".join(lines))


SECTIONS: Dict[str, Section] = {
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

if __name__ == "__main__":
    main()
    # show_perf_log()
