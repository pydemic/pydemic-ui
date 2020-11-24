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
    }
}

DURATION = 61


class Scenarios1(SimpleApp):
    title = "Scenarios for COVID-19 evolution in Brazil"

    def __init__(self):
        super().__init__()
        self.__datahandler = Scenarios1_DataHandler()

    def ask(self, parent_region="BR", where=st.sidebar):

        st = where
        scenario_kind = st.selectbox(_("Select scenario"), list(REGIONS_TYPES[parent_region]))
        query = REGIONS_TYPES[parent_region][scenario_kind]

        regions = self.__datahandler.get_regions(**query)

        message = _("Columns")
        columns = st.multiselect(message, COLUMNS, default=COLUMNS_DEFAULT)

        message = _("Isolation scores")
        kwargs = {"default": TARGETS_DEFAULT, "format_func": lambda x: f"{x}%"}
        targets = st.multiselect(message, TARGETS, **kwargs)

        message = _("Show values for the given days")
        days = st.multiselect(message, DAYS, default=DAYS_DEFAULT)

        self.__datahandler.user_inputs = {
            "parent_region": parent_region,
            "regions": regions,
            "columns": columns,
            "targets": targets,
            "days": days,
            "disease": "covid-19"
        }

    def show(self):

        parent_region = self.__datahandler.user_inputs["parent_region"]
        columns = self.__datahandler.user_inputs["columns"]
        targets = self.__datahandler.user_inputs["targets"]
        days = self.__datahandler.user_inputs["days"]
        disease = self.__datahandler.user_inputs["disease"]

        parent_region = mundi.region(parent_region)
        axes = parent_region.plot.cases_and_deaths(disease=disease, logy=True, grid=True)
        st.pyplot(axes.get_figure())
        if days and targets and columns:
            df = self.__datahandler.get_dataframe(tuple(days), tuple(targets), tuple(columns))

            st.subheader(_("Download results"))
            st.dataframe_download(df, name="report-brazil.{ext}")

    def main(self):
        self.run()


class Scenarios1_DataHandler:
    @st.cache
    def get_regions(self, **query):
        """
        Get all children in region that have the same values of the parameters passed
        as keyword arguments.
        """

        return [mundi.region(id_) for id_ in mundi.regions(**query).index]

    @info.ttl_cache(key="app.projections_br", force_streamlit=True)
    def get_dataframe(self, days, targets, columns):
        regions = self.user_inputs["regions"]
        frames = []

        prev_day = 0
        for day in days:
            delta = (day, prev_day)
            for target in targets:
                frame = pd.DataFrame(
                    {
                        column: self.__get_column(regions, target, column, delta)
                        for column in columns
                    }
                ).astype(int)

                columns_names = ("days", "isolation", "data")
                prepend = (
                    _("{n} days").format(n=day),
                    _("isolation {pc}").format(pc=pc(target / 100)),
                )
                cols = ((*prepend, col) for col in frame.columns)

                frame.columns = pd.MultiIndex.from_tuples(cols, names=columns_names)
                frames.append(frame)
            prev_day = day

        df = pd.concat(frames, axis=1)
        extra_info = df.mundi["numeric_code", "short_code", "name"]
        extra_info = extra_info.astype(str)  # streamlit bug?
        extra_info.columns = pd.MultiIndex.from_tuples(("info", extra_col, "") for extra_col in extra.columns)
        df = pd.concat([extra_info, df], axis=1)
        return df.sort_values(df.columns[0])

    @info.ttl_cache(key="app.projections_br", force_streamlit=True)
    def __process_region(self, region):
        targets = self.user_inputs["targets"]

        data = info.get_seair_curves_for_region(region, use_deaths=True)
        model = models.SEAIR(region=region, disease=covid19)
        model.set_data(data)
        model.initial_cases = info.get_cases_for_region(region)["cases"].iloc[0]

        out = {}
        for level in targets:
            new_model = model.copy(name=_("Isolation {}").format(pc(level / 100)))
            new_model.R0 *= 1 - level / 100
            new_model.run(DURATION)
            out[level] = new_model.clinical.overflow_model()

        return MappingProxyType(out)

    @info.ttl_cache(key="app.projections_br", force_streamlit=True)
    def __get_models(self) -> dict:
        models = {}
        regions = self.user_inputs["regions"]

        for region in regions:
            with st.spinner(_("Processing {name}").format(name=region.name)):
                result = self.__process_region(region)
                models.update({(region, k): v for k, v in result.items()})
        return models

    def __get_column(
        self,
        regions: List[Region],
        isolation: float,
        column: str,
        days: Tuple[int, int],
    ):
        models = self.__get_models()
        data = {}
        day, prev_day = days

        for region in regions:
            model = models[region, isolation]
            try:
                values = model[column]
            except KeyError:
                value = getattr(model, column)
            else:
                initial = -(DURATION - prev_day)
                final = -(DURATION - day)
                value = values.iloc[initial:final].max()
            data[region.id] = value

        data = pd.Series(data)
        data.name = column
        data.index.name = "region"
        return data


def main(disease=covid19):
    scenarios_1 = Scenarios1()
    scenarios_1.main()


if __name__ == "__main__":
    main()
