import itertools
import re
from typing import Tuple, Sequence

import numpy as np
import pandas as pd

import mundi
import sidekick as sk
from pydemic import models, ModelGroup
from pydemic.cache import ttl_cache
from pydemic.diseases import covid19
from pydemic.diseases import disease as get_disease
from pydemic.models import Model
from pydemic.utils import pc
from pydemic_ui import components as ui
from pydemic_ui import region as _r
from pydemic_ui import st
from pydemic_ui.i18n import _
from pydemic_ui.app import SimpleApp, Timer

_r.patch_region()
NUMBER = re.compile(r"(\d+)")
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

DAYS = [
    _("all (15 days)"),
    _("all (30 days)"),
    _("all (60 days)"),
    _("all (90 days)"),
    1,
    5,
    7,
    10,
    15,
    20,
    25,
    30,
    35,
    40,
    45,
    50,
    55,
    60,
    75,
    90,
]
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
        _("SUS macro-region"): {
            "query": {
                "type": "region",
                "subtype": "healthcare region",
                "country_code": "BR",
            },
            "filter": {
                "parent_id": _("Select state"),
                "format_func": lambda x: mundi.region(x).name,
            },
            "info": {"numeric_code": _("ref"), "name": _("Name"), "parent_id": _("UF")},
        },
    }
}

TWO_HOURS: 2 * 60 * 60


class Scenarios2(SimpleApp):
    title = "Scenarios for COVID-19 evolution in Brazil"

    def __init__(self):
        super().__init__()
        self.__datahandler = Scenarios2_DataHandler()

    def ask(self, parent_region="BR", where=st.sidebar):
        st = where
        scenario_kind = st.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
        scenario = REGIONS_TYPES[parent_region][scenario_kind]
        regions = self.__datahandler.get_regions(**scenario["query"])

        if "filter" in scenario:
            filtering = scenario["filter"]
            format_func = filtering.pop("format_func", None)
            if format_func is not None:
                function = format_func

                def format_func(x):
                    if x == "all":
                        return _("All")
                    return function(x)

            field, message = filtering.popitem()
            groups = sk.group_by(lambda x: getattr(x, field), regions)

            key = st.selectbox(message, ["all", *groups], format_func=format_func)
            if key != "all":
                regions = groups[key]

        message = _("Columns")
        columns = st.multiselect(message, COLUMNS, default=COLUMNS_DEFAULT)

        message = _("Isolation scores")
        kwargs = {"default": TARGETS_DEFAULT, "format_func": lambda x: f"{x}%"}
        targets = st.multiselect(message, TARGETS, **kwargs)

        message = _("Show values for the given days")
        days = st.multiselect(message, DAYS, default=DAYS_DEFAULT)
        if any(not isinstance(d, int) for d in days):
            day_max = sk.pipe(
                days,
                sk.remove(lambda d: isinstance(d, int)),
                sk.map(lambda d: int(NUMBER.search(d).groups()[0])),
                max,
            )
            days = list(range(1, day_max + 1))

        message = _("Transpose data")
        transpose = st.checkbox(message, value=False)

        self.__datahandler.user_inputs = {
            "parent_region": parent_region,
            "regions": regions,
            "columns": columns,
            "targets": targets,
            "days": days,
            "scenario": scenario,
            "transpose": transpose,
            "disease": "covid-19"
        }

    def show(self):
        parent_region = self.__datahandler.user_inputs["parent_region"]
        columns = self.__datahandler.user_inputs["columns"]
        targets = self.__datahandler.user_inputs["targets"]
        days = self.__datahandler.user_inputs["days"]
        scenario = self.__datahandler.user_inputs["scenario"]
        transpose = self.__datahandler.user_inputs["transpose"]
        disease = self.__datahandler.user_inputs["disease"]

        parent_region = mundi.region(parent_region)
        parent_region.ui.cases_and_deaths(disease=disease, grid=True, logy=True)

        if days and targets and columns:
            info = scenario["info"]
            info_cols = tuple(info)
            df = self.__datahandler.get_dataframe(
                tuple(days), tuple(columns), info_cols=info_cols
            )
            column_info = {**COL_NAMES, **info}.get
            df.columns = pd.MultiIndex.from_tuples(
                [tuple(_(column_info(x, x) for x in t)) for t in df.columns.to_list()]
            )
            if transpose:
                df = df.T

            st.subheader(_("Download results"))
            st.dataframe_download(df, name="report-brazil.{ext}")

    def main(self):
        self.run()


class Scenarios2_DataHandler():

    @st.cache(show_spinner=False)
    def get_regions(self, **query):
        """
        Get all children in region that have the same values of the parameters passed
        as keyword arguments.
        """

        return tuple(mundi.region(id_) for id_ in mundi.regions(**query).index)

    @st.cache(suppress_st_warning=True, ttl=TWO_HOURS, show_spinner=False)
    def get_dataframe(self, days, columns, info_cols=()):
        regions = self.user_inputs["regions"]
        steps = len(self.user_inputs["regions"])
        duration = max(days)
        days_ranges = np.array([0, *days])
        columns = list(columns)

        progress_bar = st.progress(0)
        with st.spinner(_("Running simulations")):

            rows = {}
            for i, region in enumerate(regions):
                base, group = self.__run_simulations(region, duration)
                progress_bar.progress(int(100 * i / steps))

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
                cols_data = [*cols.values()]
                rows[region.id] = pd.concat(cols_data, axis=1, names=[_("days")], keys=keys)

        progress_bar.empty()
        cols_data = pd.concat(list(rows.values()))
        cols_data.index = rows.keys()

        if info_cols:
            extra_info = cols_data.mundi[info_cols]
            extra_info = extra_info.astype(object)  # streamlit bug?
            extra_info.columns = pd.MultiIndex.from_tuples(("", "info", x) for x in extra_info.columns)
            data = pd.concat([extra_info, cols_data], axis=1)
            return cols_data.sort_values(cols_data.columns[0])
        else:
            return cols_data.sort_index()

    @st.cache(ttl=TWO_HOURS, show_spinner=False)
    def __get_cases_information(self, region, disease):
        return disease.epidemic_curve(region, real=True, keep_observed=True)

    # @ttl_cache("app-scenarios", timeout=2 * 3600)
    @st.cache(ttl=TWO_HOURS, show_spinner=False)
    def __run_simulations(self, region, duration) -> Tuple[Model, ModelGroup]:
        targets = self.user_inputs["targets"]
        disease = get_disease("covid-19")
        base = models.SEAIR(region=region, disease=disease, name=region.id)
        base.set_cases(self.__get_cases_information(region, disease), save_observed=True)

        column_names = []
        R0s = []
        for target in targets:
            column_names.append(_("Isolation {}").format(pc(target / 100)))
            R0s.append(base.R0 * (1 - target / 100))

        info_group = base.split(name=column_names, R0=R0s)
        info_group.run(duration)
        return base, info_group.clinical.overflow_model()


def main(disease=covid19):
    scenarios_2 = Scenarios2()
    scenarios_2.main()


if __name__ == "__main__":
    main()
