import base64
import io
from types import MappingProxyType

import pandas as pd

import mundi
from pydemic import models
from pydemic.diseases import covid19
from pydemic.utils import pc
from pydemic_ui import components as ui
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui.i18n import _

MIMETYPES_MAP = {"csv": "text/csv", "xlsx": "application/vnd.ms-excel"}

TARGETS = list(range(90, 10, -10))
TARGETS_DEFAULT = [TARGETS[2], TARGETS[4], TARGETS[6]]

COLUMNS = [
    # Infectious model
    "susceptible",
    "exposed",
    "asymptomatic",
    "infectious",
    "recovered",
    "cases",
    "infected",
    "R0",
    # Clinical outcomes
    "severe",
    "critical",
    "deaths",
    "natural_deaths",
    # Parameters
    "icu_capacity",
    "hospital_capacity",
    "icu_surge_capacity",
    "hospital_surge_capacity",
]
COLUMNS_DEFAULT = ["critical", "severe"]
COL_NAMES = {
    "critical": _("ICU"),
    "severe": _("Clinical"),
    "cases": _("Cases"),
    "infected": _("Infected"),
    "deaths": _("Deaths"),
}

DAYS = [5, 7, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 75, 90]
DAYS_DEFAULT = [7, 15, 30, 60]

REGIONS_TYPES = {
    "BR": {
        _("State"): {"type": "state", "country_code": "BR"},
        _("Macro-region"): {
            "type": "region",
            "subtype": "macro-region",
            "country_code": "BR",
        },
        _("SUS macro-region"): {
            "type": "region",
            "subtype": "healthcare region",
            "country_code": "BR",
        },
    }
}


def get_column(
    col: str, day: int, prev_day: int, isolation: float, models: dict, duration: int
):
    data = {}
    for r in regions:
        model = models[r, isolation]
        try:
            values = model[col]
        except KeyError:
            value = getattr(model, col)
        else:
            initial = -(duration - prev_day)
            final = -(duration - day)
            value = values.iloc[initial:final].max()
        data[r.id] = value

    data = pd.Series(data)
    data.name = col
    data.index.name = "region"
    return data


@info.ttl_cache(key="app.projections_br", force_streamlit=True)
def process_region(region, targets, duration):
    data = info.get_seair_curves_for_region(region, use_deaths=True)
    m = models.SEAIR(region=region, disease=covid19)
    m.set_data(data)
    m.initial_cases = info.get_cases_for_region(region)["cases"].iloc[0]

    out = {}
    for level in targets:
        new = m.copy(name=_("Isolation {}").format(pc(level / 100)))
        new.R0 *= 1 - level / 100
        new.run(duration)
        out[level] = new.clinical.overflow_model()

    return MappingProxyType(out)


@info.ttl_cache(key="app.projections_br", force_streamlit=True)
def get_models(regions, targets, duration) -> dict:
    models = {}
    for region in regions:
        with st.spinner(_("Processing {name}").format(name=region.name)):
            result = process_region(region, targets, duration)
            models.update({(region, k): v for k, v in result.items()})
    return models


@info.ttl_cache(key="app.projections_br", force_streamlit=True)
def get_dataframe(regions, days, targets, columns, duration):
    models = get_models(regions, targets, duration)
    frames = []

    prev_day = 0
    for day in days:
        for isolation in targets:
            frame = pd.DataFrame(
                {
                    col: get_column(col, day, prev_day, isolation, models, duration)
                    for col in columns
                }
            ).astype(int)

            names = ("days", "isolation", "data")
            prepend = (
                _("{n} days").format(n=day),
                _("isolation {pc}").format(pc=pc(isolation / 100)),
            )
            cols = ((*prepend, c) for c in frame.columns)

            frame.columns = pd.MultiIndex.from_tuples(cols, names=names)
            frames.append(frame)
        prev_day = day

    df = pd.concat(frames, axis=1)
    extra = df.mundi["name", "short_code", "numeric_code"]
    extra = extra.astype(str)  # streamlit bug?
    extra.columns = pd.MultiIndex.from_tuples(("info", x, "") for x in extra.columns)
    return pd.concat([extra, df], axis=1)


def dataframe_download_link(df, name="data.{ext}", show_option=True):
    """
    Create a download link to dataframe.
    """
    opts = {
        "show": _("Show in screen"),
        "csv": _("Comma separated values"),
        "xlsx": _("Excel"),
    }
    if not show_option:
        del opts["show"]

    opt = st.radio(_("How do you want your data?"), list(opts), format_func=opts.get)

    if opt == "show":
        st.write(df)
    else:
        st.html(data_anchor(df, name.format(ext=opt), type=opt))


def data_anchor(
    df: pd.DataFrame,
    filename: str,
    label: str = _("Right click link to download"),
    type="csv",
) -> str:
    """
    Create a string with a data URI that permits downloading the contents of a
    a dataframe.
    """
    href = data_uri(df, type)
    return f'<a href="{href}" download="{filename}">{label}</a>'


def data_uri(df: pd.DataFrame, type: str, mime_type=None):
    """
    Returns only the href component of a data anchor.
    """
    if type == "csv":
        fd = io.StringIO()
        df.to_csv(fd)
        data = fd.getvalue().encode("utf8")
    elif type == "xlsx":
        fd = io.BytesIO()
        df.to_excel(fd)
        data = fd.getvalue()
    else:
        raise ValueError(f"invalid output type: {type}")
    data = base64.b64encode(data).decode("utf8")
    mime_type = mime_type or MIMETYPES_MAP[type]
    return f"data:{mime_type};base64,{data}"


@st.cache
def get_regions(**query):
    """
    Get all children in region that have the same values of the parameters passed
    as keyword arguments.
    """
    return [mundi.region(id_) for id_ in mundi.regions(**query).index]


ui.css()
ui.logo(where=st.sidebar)

parent_region = "BR"
kind = st.sidebar.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
query = REGIONS_TYPES[parent_region][kind]

trim_days = st.sidebar.number_input(_("Trim days"), 0, value=0)

regions = get_regions(**query)

msg = _("Columns")
columns = st.sidebar.multiselect(msg, COLUMNS, default=COLUMNS_DEFAULT)

msg = _("Isolation scores")
kwargs = {"default": TARGETS_DEFAULT, "format_func": lambda x: f"{x}%"}
targets = st.sidebar.multiselect(msg, TARGETS, **kwargs)

msg = _("Show values for the given days")
days = st.sidebar.multiselect(msg, DAYS, default=DAYS_DEFAULT)

ui.cases_and_deaths_plot.from_region(parent_region, logy=True, grid=True)

if days and targets and columns:
    df = get_dataframe(regions, tuple(days), tuple(targets), tuple(columns), 61)

    st.subheader(_("Download results"))
    dataframe_download_link(df, name="report-brazil.{ext}")
