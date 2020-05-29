from types import MappingProxyType
from typing import List, Tuple

import pandas as pd

import mundi
from mundi import Region
from pydemic import models
from pydemic.diseases import covid19
from pydemic.utils import pc
from pydemic_ui import components as ui
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui.i18n import _

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
        # _("SUS macro-region"): {
        #     "type": "region",
        #     "subtype": "healthcare region",
        #     "country_code": "BR",
        # },
    }
}


def get_column(
    models: dict,
    regions: List[Region],
    isolation: float,
    col: str,
    days: Tuple[int, int],
    duration: int,
):
    data = {}
    day, prev_day = days
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
        delta = (day, prev_day)
        for target in targets:
            frame = pd.DataFrame(
                {
                    col: get_column(models, regions, target, col, delta, duration)
                    for col in columns
                }
            ).astype(int)

            names = ("days", "isolation", "data")
            prepend = (
                _("{n} days").format(n=day),
                _("isolation {pc}").format(pc=pc(target / 100)),
            )
            cols = ((*prepend, c) for c in frame.columns)

            frame.columns = pd.MultiIndex.from_tuples(cols, names=names)
            frames.append(frame)
        prev_day = day

    df = pd.concat(frames, axis=1)
    extra = df.mundi["numeric_code", "short_code", "name"]
    extra = extra.astype(str)  # streamlit bug?
    extra.columns = pd.MultiIndex.from_tuples(("info", x, "") for x in extra.columns)
    df = pd.concat([extra, df], axis=1)
    return df.sort_values(df.columns[0])


@st.cache
def get_regions(**query):
    """
    Get all children in region that have the same values of the parameters passed
    as keyword arguments.
    """
    return [mundi.region(id_) for id_ in mundi.regions(**query).index]


def collect_inputs(parent_region="BR", where=st.sidebar):
    """
    Collect input parameters for the app to run.

    Returns:
        Dictionary with the following keys:
            parent_region, regions, columns, targets, days
    """
    st = where
    kind = st.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
    query = REGIONS_TYPES[parent_region][kind]

    regions = get_regions(**query)

    msg = _("Columns")
    columns = st.multiselect(msg, COLUMNS, default=COLUMNS_DEFAULT)

    msg = _("Isolation scores")
    kwargs = {"default": TARGETS_DEFAULT, "format_func": lambda x: f"{x}%"}
    targets = st.multiselect(msg, TARGETS, **kwargs)

    msg = _("Show values for the given days")
    days = st.multiselect(msg, DAYS, default=DAYS_DEFAULT)

    return {
        "parent_region": parent_region,
        "regions": regions,
        "columns": columns,
        "targets": targets,
        "days": days,
    }


def show_results(parent_region, regions, columns, targets, days, disease=covid19):
    """
    Show results from user input.
    """

    parent_region = mundi.region(parent_region)
    ax = parent_region.plot.cases_and_deaths(disease=disease, logy=True, grid=True)
    st.pyplot(ax.get_figure())
    if days and targets and columns:
        df = get_dataframe(regions, tuple(days), tuple(targets), tuple(columns), 61)

        st.subheader(_("Download results"))
        st.dataframe_download(df, name="report-brazil.{ext}")


def main(embed=False, disease=covid19):
    """
    Main function for application.
    """

    if not embed:
        ui.css()

    if not embed:
        ui.logo(where=st.sidebar)

    st.title(_("Scenarios for COVID-19 evolution in Brazil"))
    inputs = collect_inputs(where=st if embed else st.sidebar)
    show_results(disease=disease, **inputs)


if __name__ == "__main__":
    main()
