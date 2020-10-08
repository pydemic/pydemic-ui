import mundi
import pandas as pd
from mundi import Region
from pydemic import models
from pydemic.diseases import covid19
from pydemic_ui import components as ui
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui.app import SimpleApp, Timer
from pydemic_ui.i18n import _
from pydemic.utils import pc
from types import MappingProxyType
from typing import List, Tuple

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

DAYS = [1, 5, 7, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 75, 90]
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


class Scenarios1(SimpleApp):
    title = "Scenarios for COVID-19 evolution in Brazil"

    def __init__(self):
        super().__init__()

    @st.cache
    def get_regions(self, **query):
        """
        Get all children in region that have the same values of the parameters passed
        as keyword arguments.
        """

        return [mundi.region(id_) for id_ in mundi.regions(**query).index]

    def ask(self, parent_region="BR", where=st.sidebar):
        """
        Collect input parameters for the app to run.

        Returns:
            Dictionary with the following keys:
                parent_region, regions, columns, targets, days
        """

        st = where
        kind = st.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
        query = REGIONS_TYPES[parent_region][kind]

        regions = self.get_regions(**query)

        msg = _("Columns")
        columns = st.multiselect(msg, COLUMNS, default=COLUMNS_DEFAULT)

        msg = _("Isolation scores")
        kwargs = {"default": TARGETS_DEFAULT, "format_func": lambda x: f"{x}%"}
        targets = st.multiselect(msg, TARGETS, **kwargs)

        msg = _("Show values for the given days")
        days = st.multiselect(msg, DAYS, default=DAYS_DEFAULT)

        self.user_inputs = {
            "parent_region": parent_region,
            "regions": regions,
            "columns": columns,
            "targets": targets,
            "days": days,
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
        disease = self.user_inputs["disease"]

        parent_region = mundi.region(parent_region)
        ax = parent_region.plot.cases_and_deaths(disease=disease, logy=True, grid=True)
        st.pyplot(ax.get_figure())
        if days and targets and columns:
            df = self.get_dataframe(regions, tuple(days), tuple(targets), tuple(columns), 61)

            st.subheader(_("Download results"))
            st.dataframe_download(df, name="report-brazil.{ext}")

    @info.ttl_cache(key="app.projections_br", force_streamlit=True)
    def get_dataframe(self, regions, days, targets, columns, duration):
        models = self.get_models(regions, targets, duration)
        frames = []

        prev_day = 0
        for day in days:
            delta = (day, prev_day)
            for target in targets:
                frame = pd.DataFrame(
                    {
                        col: self.get_column(models, regions, target, col, delta, duration)
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

    @info.ttl_cache(key="app.projections_br", force_streamlit=True)
    def get_models(self, regions, targets, duration) -> dict:
        models = {}
        for region in regions:
            with st.spinner(_("Processing {name}").format(name=region.name)):
                result = self.process_region(region, targets, duration)
                models.update({(region, k): v for k, v in result.items()})
        return models

    @info.ttl_cache(key="app.projections_br", force_streamlit=True)
    def process_region(self, region, targets, duration):
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

    def get_column(
        self,
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

    def main(self):
        self.run()


def main(disease=covid19):
    scenarios_1 = Scenarios1()
    scenarios_1.main()


if __name__ == "__main__":
    main()
