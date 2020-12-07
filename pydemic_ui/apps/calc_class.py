"""
Pydemic Calc Application
========================

This is the main application in the Pydemic UI package. It consists of an
epidemic calculator that allows user to choose some region and configure basic
epidemiological parameters to make scenarios about how the epidemic spreads
in the near future.

This app uses components from the Pydemic UI package.
"""
import importlib
import os

from pydemic.diseases import covid19
from pydemic.models import SEAIR
from pydemic.utils import extract_keys
from pydemic_ui import st
from pydemic_ui import ui
from pydemic_ui.i18n import _
from pydemic_ui.app import SimpleApp, Timer
from pydemic_ui.apps.secret_class import Secret
from pydemic_ui.apps.construct_model_class import ConstructModel
from pydemic_ui.apps.debug_calc_class import DebugCalc

DEBUG = os.environ.get("DEBUG", "false").lower() in ("true", "on", "1")

DEATH_DISTRIBUTION_COLUMNS = [
    "natural_deaths:dates",
    "icu_overflow_deaths:dates",
    "hospital_overflow_deaths:dates",
]

DEATH_DISTRIBUTION_COL_NAMES = {
    "natural_deaths": _("Natural"),
    "icu_overflow_deaths": _("Lack of hospital beds"),
    "hospital_overflow_deaths": _("Lack of ICUs"),
}

PARAMS = [
    "region",
    "R0",
    "infectious_period",
    "incubation_period",
    "prob_symptoms",
    "date",
    "daily_cases",
    "runner",
    "period",
]

CLINICAL = [
    "hospitalization_period",
    "icu_period",
    "severe_period",
    "critical_period",
    "hospital_capacity",
    "icu_capacity",
    "prob_severe",
    "prob_critical",
]

CAPACITY = ["hospital_full_capacity", "icu_full_capacity"]


class Calc(SimpleApp):
    title = "Hospital pressure calculator"

    def __init__(self):
        super().__init__()
        self.where = st

    def ask(self, region="BR", disease=covid19, secret_date=None):
        """
        Calculator sidebar element.

        It receives a region and a disease (defaults to Covid-19) and return a
        dictionary of parameters that might be useful to configure a simulation.
        """
        self.where = st.sidebar
        region = self.where.region_input(region, sus_regions=True, arbitrary=True)

        try:
            params = self.where.simulation_params(
                region, disease, secret_date=secret_date
            )
        except RuntimeError:
            Secret.area()
            return

        return {
            "region": region,
            **params,
            **self.where.healthcare_params(region),
            **self.where.epidemiological_params(region, disease),
            **{"runner": self.where.intervention_runner_input(params["period"])},
        }

    def show(self, model, title=_("Hospital pressure calculator")):
        """
        Create default output from model.
        """
        if title:
            st.title(title)

        model.ui.summary_cards()

        st.pause()
        model.ui.hospitalizations_chart()

        st.pause()
        model.ui.available_beds_chart()

        st.line()
        ui.population_info_chart(model.age_pyramid)

        st.pause()
        model.ui.deaths_chart()

        st.line()
        model.ui.healthcare_parameters()

        st.pause()
        model.ui.ppe_demand_table()

        st.pause()
        model.ui.epidemiological_parameters()

        st.pause()
        st.footnotes()

    def run_infectious_model(Debug):
        epidemiology = extract_keys(PARAMS, params)
        clinical = extract_keys(CLINICAL, params)

        model = clinical_model = results = None
        try:
            model = ConstructModel(disease=disease, **epidemiology).new_model()
            clinical_model = model.clinical.overflow_model(
                icu_occupancy=0, hospital_occupancy=0, **clinical
            )
            clinical_model.extra_info = params
            self.show(clinical_model)

        finally:
            if Debug:
                Debug.information_message(
                    results, params, epidemiology, clinical, model, clinical_model
                )

    def main(self, region="BR", disease=covid19):
        st.css()
        params = self.ask(region=region, disease=disease, secret_date=Secret.date)

        if Secret.is_easter_egg_activated(params):
            return

        Debug = DebugCalc(st, DEBUG)
        run_infectious_model(Debug)


def main(disease=covid19):
    """
    Main function for application.
    """
    calc = Calc()
    calc.main()


# Start main script
if __name__ == "__main__":
    main()
