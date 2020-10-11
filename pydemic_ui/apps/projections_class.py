import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from pydemic.models import Model, SEAIR
from pydemic.plot import mark_x, mark_y
from pydemic.region import RegionT
from pydemic.utils import extract_keys, fmt, pc
from pydemic_ui import st
from pydemic_ui.i18n import _
from pydemic_ui.app import SimpleApp, Timer

pd = pd
np = np
SHOW_OPTS = ("show_cases_plot", "show_weekday_rate", "plot_opts")
CLINICAL_OPTS = (
    "icu_capacity",
    "hospital_capacity",
    "icu_surge_capacity",
    "hospital_surge_capacity",
)
RUN_OPTS = ("duration", "R0_list")

class Projections(SimpleApp):
    title = False

    def __init__(self, embed=False, disease="covid-19", **kwargs):
        super().__init__(embed=embed, **kwargs)
        self.embed
        if not self.embed:
            self.css = st.css(keep_menu=True)
        self.logo = True
        self.where = st if self.embed else st.sidebar
        self.disease = disease

    def ask(self):
        pass

    def show(self):
        self.render_sidebar()

    def checkbox_options(self, title, **kwargs):
        if self.embed:
            return True
        return self.where.checkbox(title, **kwargs)

    def render_sidebar(self):
        self.where = st.sidebar
        region = self.where.region_input("BR", text=True)
        st.title(f"Covid risk factors {region.name}")

        # # Scenarios
        model = self.start_model(region)
        R0 = model.R0.item()

        self.where.header(_("Forecast scenarios"))
        subs = {"R0": fmt(R0), "place": _(region.name)}
        self.where.markdown(
            _(
                """The computed value of R0 for {place} is **{R0}**. Let us
        consider 3 different scenarios: the first progress with this value of R0, the
        second increases social isolation to obtain a lower R0 and the third loosen
        social isolation and correspond to a higher R0."""
            ).format(**subs)
        )

        self.where.subheader("Scenario 1: more isolation")
        msg = _("What is the new R0?")
        R0_tight = self.where.slider(msg, 0.1, R0, R0 * 0.66)

        self.where.subheader("Scenario 2: less isolation")
        R0_loose = self.where.slider(msg, R0, max(2 * R0, 3.0), 1.33 * R0)
        R0_list = (R0, R0_tight, R0_loose)

        # Parameters
        self.where.header(_("Parameters"))
        self.where.subheader(_("Healthcare system"))
        if np.isnan(region.icu_capacity):
            population = region.population

            msg = _("Total ICU beds")
            icu = int(population / 10_000)
            icu = self.where.number_input(msg, min_value=0, value=icu)

            msg = _("Total hospital beds")
            hospital = int(population / 1_000)
            hospital = self.where.number_input(msg, min_value=0, value=hospital)

        else:
            icu = region.icu_capacity
            hospital = region.hospital_capacity

        msg = _("Fraction of ICU beds that is occupied?")
        rate = 1 - self.where.slider(msg, 0, 100, value=75) / 100

        self.where.header(_("Options"))
        self.where.subheader(_("Plotting options"))
        options = {
            "logy": not self.checkbox_options(title="Linear scale"),
            "grid": not self.checkbox_options(title="Hide grid")
        }
        self.where.subheader(_("Advanced information"))
        options = {
            "plot_opts": options,
            "show_weekday_rate": self.checkbox_options(title="Notification per weekday"),
        }

        self.user_inputs = {
            "region": region,
            "icu_capacity": icu,
            "hospital_capacity": hospital,
            "icu_surge_capacity": rate * icu,
            "hospital_surge_capacity": rate * hospital,
            "R0_list": R0_list,
            **options,
        }

        self.process_data()

    def process_data(self):
        show_opts = extract_keys(SHOW_OPTS, self.user_inputs)
        clinical_opts = extract_keys(CLINICAL_OPTS, self.user_inputs)
        run_opts = extract_keys(RUN_OPTS, self.user_inputs)

        # Start model with known R0
        region = self.user_inputs["region"]
        plot_opts = show_opts["plot_opts"]

        self.where = st
        self.where.header(_("Cases and deaths"))
        region.ui.epidemic_summary()
        region.ui.cases_and_deaths(title=None, download=f"cases-{region.id}.csv", **plot_opts)

        # model = self.start_model()
        # group = self.start_group(model, **run_opts)
        # self.show_outputs(model, group, clinical_opts=clinical_opts, **opts, **show_opts)

    @st.cache(show_spinner=False)
    def start_model(self, region: RegionT):
        """
        Start model with cases data for the given region.
        """

        cases = region.pydemic.epidemic_curve(disease=self.disease, real=True, keep_observed=True)
        m = SEAIR(region=region, disease=self.disease)
        m.set_cases(cases, adjust_R0=True, save_observed=True)
        m.info.save_event("simulation_start")
        return m

    @st.cache(show_spinner=False)
    def start_group(self, model: Model, duration=60, R0_list=()):
        """
        Split into 4 models: a forecast model, one that tighten social distancing by
        the given amount delta, one that loosen social distancing by the same ammount
        and one that completely lift social distancing measures
        """
        models = model.split(R0=R0_list, name=["baseline", "isolate", "open"])
        models.run(duration)
        return models


    def main(self):
        # opts = sidebar(title, where=st if embed else st.sidebar, embed=embed, disease=disease)
        
        self.run()


def main():
    projections = Projections()
    projections.main()


if __name__ == "__main__":
    main()