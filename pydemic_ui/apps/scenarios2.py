import itertools
from typing import Tuple, Sequence

import numpy as np
import pandas as pd
import sidekick as sk

import mundi
from pydemic import models, ModelGroup
from pydemic.diseases import covid19
from pydemic.diseases import disease as get_disease
from pydemic.models import Model
from pydemic.utils import pc
from pydemic_ui import components as ui
from pydemic_ui import region as _r
from pydemic_ui import st
from pydemic_ui.i18n import _

_r.patch_region()
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

DAYS = [1, 5, 7, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 75, 90]
DAYS_DEFAULT = [7, 15, 30, 60]

REGIONS_TYPES = {
    "BR": {
        _("All Brazilian states"): {
            "query": {"type": "state", "country_code": "BR"},
            "info": {
                "numeric_code": _("Numeric code"),
                "short_code": _("UF"),
                "name": _("Name"),
            },
        },
        _("Brazilian macro-regions"): {
            "query": {"type": "region", "subtype": "macro-region", "country_code": "BR"},
            "info": {"numeric_code": _("Numeric code"), "name": _("Name")},
        },
        # _("SUS macro-region"): {
        #     "type": "region",
        #     "subtype": "healthcare region",
        #     "country_code": "BR",
        # },
    }
}


def main(embed=False, disease=covid19):
    """
    Main function for application.
    """

    if not embed:
        ui.css()

    if not embed:
        ui.logo(where=st.sidebar)

    st.title(_("Scenarios for COVID-19 evolution in Brazil"))
    inputs = sidebar(where=st if embed else st.sidebar)
    show_results(disease=disease, **inputs)


def sidebar(parent_region="BR", where=st.sidebar):
    """
    Collect input parameters for the app to run.

    Returns:
        Dictionary with the following keys:
            parent_region, regions, columns, targets, days
    """
    st = where
    kind = st.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
    scenario = REGIONS_TYPES[parent_region][kind]
    regions = get_regions(**scenario["query"])

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
        "scenario": scenario,
    }


def show_results(
    parent_region, regions, columns, targets, days, scenario, disease=covid19
):
    """
    Show results from user input.
    """

    parent_region = mundi.region(parent_region)
    parent_region.ui.cases_and_deaths(disease=disease, grid=True)

    if days and targets and columns:
        info = scenario["info"]
        info_cols = tuple(info)
        df = get_dataframe(
            regions,
            tuple(days),
            tuple(targets),
            tuple(columns),
            duration=60,
            info_cols=info_cols,
        )
        get = {**COL_NAMES, **info}.get
        df.columns = pd.MultiIndex.from_tuples(
            [tuple(_(get(x, x) for x in t)) for t in df.columns.to_list()]
        )

        st.subheader(_("Download results"))
        st.dataframe_download(df, name="report-brazil.{ext}")


@st.cache(ttl=2 * 3600, show_spinner=False)
def cases(region, disease):
    return disease.epidemic_curve(region, real=True, keep_observed=True)


@st.cache(ttl=2 * 3600, show_spinner=False, allow_output_mutation=True)
def simulations(
    region, targets: Sequence[int], duration, disease
) -> Tuple[Model, ModelGroup]:
    disease = get_disease(disease)
    base = models.SEAIR(region=region, disease=disease, name=region.id)
    base.set_cases(cases(region, disease), save_cases=True)

    names = []
    R0s = []
    for target in targets:
        names.append(_("Isolation {}").format(pc(target / 100)))
        R0s.append(base.R0 * (1 - target / 100))

    group = base.split(name=names, R0=R0s)
    group.run(duration)
    return base, group.clinical.overflow_model()


@st.cache(suppress_st_warning=True, ttl=2 * 3600, show_spinner=False)
def get_dataframe(
    regions, days, targets, columns, duration=60, disease="covid-19", info_cols=()
):
    steps = len(regions)
    days_ranges = np.array([0, *days])
    columns = list(columns)

    bar = st.progress(0)
    with st.spinner(_("Running simulations")):

        rows = {}
        for i, region in enumerate(regions):
            base, group = simulations(region, targets, duration, disease=disease)
            bar.progress(int(100 * i / steps))

            cols = {}
            for a, b in sk.window(2, days_ranges):
                day = b
                a += base.time + 1
                b += a - 1
                renames = dict(zip(itertools.count(), columns))

                name = _("{} days").format(day)
                cols[name] = (
                    pd.DataFrame(group[columns, a:b].max(0))
                    .T.rename(columns=renames)
                    .rename(index={0: region.id})
                    .astype(int)
                )

            keys = [*cols]
            data = [*cols.values()]
            rows[region.id] = pd.concat(data, axis=1, names=[_("days")], keys=keys)

    bar.empty()
    data = pd.concat(list(rows.values()))
    data.index = rows.keys()

    if info_cols:
        extra = data.mundi[info_cols]
        extra = extra.astype(object)  # streamlit bug?
        extra.columns = pd.MultiIndex.from_tuples(("", "info", x) for x in extra.columns)
        data = pd.concat([extra, data], axis=1)
        return data.sort_values(data.columns[0])
    else:
        return data.sort_index()


@st.cache(show_spinner=False)
def get_regions(**query):
    """
    Get all children in region that have the same values of the parameters passed
    as keyword arguments.
    """
    return tuple(mundi.region(id_) for id_ in mundi.regions(**query).index)


if __name__ == "__main__":
    main()