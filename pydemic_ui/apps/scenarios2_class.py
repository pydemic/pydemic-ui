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

class Scenarios2(SimpleApp):
    title = "Scenarios for COVID-19 evolution in Brazil"

    def __init__(self):
        super().__init__()

    def ask(self, parent_region="BR", where=st.sidebar):
        """
        Collect input parameters for the app to run.

        Returns:
            Dictionary with the following keys:
                parent_region, regions, columns, targets, days
        """
        st = where
        kind = st.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
        scenario = REGIONS_TYPES[parent_region][kind]
        regions = self.get_regions(**scenario["query"])

        if "filter" in scenario:
            filtering = scenario["filter"]
            format_func = filtering.pop("format_func", None)
            if format_func is not None:
                fn = format_func

                def format_func(x):
                    if x == "all":
                        return _("All")
                    return fn(x)

            field, msg = filtering.popitem()
            groups = sk.group_by(lambda x: getattr(x, field), regions)

            key = st.selectbox(msg, ["all", *groups], format_func=format_func)
            if key != "all":
                regions = groups[key]

        msg = _("Columns")
        columns = st.multiselect(msg, COLUMNS, default=COLUMNS_DEFAULT)

        msg = _("Isolation scores")
        kwargs = {"default": TARGETS_DEFAULT, "format_func": lambda x: f"{x}%"}
        targets = st.multiselect(msg, TARGETS, **kwargs)

        msg = _("Show values for the given days")
        days = st.multiselect(msg, DAYS, default=DAYS_DEFAULT)
        if any(not isinstance(d, int) for d in days):
            day_max = sk.pipe(
                days,
                sk.remove(lambda d: isinstance(d, int)),
                sk.map(lambda d: int(NUMBER.search(d).groups()[0])),
                max,
            )
            days = list(range(1, day_max + 1))

        msg = _("Transpose data")
        transpose = st.checkbox(msg, value=False)

        self.user_inputs = {
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
        """
        Show results from user input.
        """
        parent_region = self.user_inputs["parent_region"]
        regions = self.user_inputs["regions"]
        columns = self.user_inputs["columns"]
        targets = self.user_inputs["targets"]
        days = self.user_inputs["days"]
        scenario = self.user_inputs["scenario"]
        transpose = self.user_inputs["transpose"]
        disease = self.user_inputs["disease"]

        parent_region = mundi.region(parent_region)
        parent_region.ui.cases_and_deaths(disease=disease, grid=True, logy=True)

        if days and targets and columns:
            info = scenario["info"]
            info_cols = tuple(info)
            df = get_dataframe(
                regions, tuple(days), tuple(targets), tuple(columns), info_cols=info_cols
            )
            get = {**COL_NAMES, **info}.get
            df.columns = pd.MultiIndex.from_tuples(
                [tuple(_(get(x, x) for x in t)) for t in df.columns.to_list()]
            )
            if transpose:
                df = df.T

            st.subheader(_("Download results"))
            st.dataframe_download(df, name="report-brazil.{ext}")

    @st.cache(show_spinner=False)
    def get_regions(self, **query):
        """
        Get all children in region that have the same values of the parameters passed
        as keyword arguments.
        """

        return tuple(mundi.region(id_) for id_ in mundi.regions(**query).index)

    def main(self):
        self.run()

def main(disease=covid19):
    """
    Main function for application.
    """
    scenarios_2 = Scenarios2()
    scenarios_2.main()

if __name__ == "__main__":
    main()