import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from pydemic.models import Model, SEAIR
from pydemic.plot import mark_x, mark_y
from pydemic.region import RegionT
from pydemic.utils import extract_keys, fmt, pc
from pydemic_ui import st
from pydemic_ui.i18n import _

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


def main(embed=False, disease=None):
    """
    Run application.
    """
    if not embed:
        st.css(keep_menu=True)
        st.sidebar.logo()
        title = st.empty().title
        title(_("Covid risk factors"))
    else:
        title = lambda *args: None

    opts = sidebar(title, where=st if embed else st.sidebar, embed=embed, disease=disease)
    show_opts = extract_keys(SHOW_OPTS, opts)
    clinical_opts = extract_keys(CLINICAL_OPTS, opts)
    run_opts = extract_keys(RUN_OPTS, opts)

    # Start model with known R0
    region = opts["region"]
    plot_opts = show_opts["plot_opts"]

    st.header(_("Cases and deaths"))
    region.ui.epidemic_summary()
    region.ui.cases_and_deaths(title=None, download=f"cases-{region.id}.csv", **plot_opts)

    model = start_model(**opts)
    group = start_group(model, **run_opts)
    show_outputs(model, group, clinical_opts=clinical_opts, **opts, **show_opts)


def sidebar(title, where=st.sidebar, embed=False, disease="covid-19"):
    """
    Collect inputs in the sidebar or other location.
    """

    st = where
    region = st.region_input("BR", text=True)
    title(_("Covid risk factors ({name})").format(name=_(region.name)))

    # Scenarios
    model = start_model(region, disease)
    R0 = model.R0

    st.header(_("Forecast scenarios"))
    subs = {"R0": fmt(R0), "place": _(region.name)}
    st.markdown(
        _(
            """The computed value of R0 for {place} is **{R0}**. Let us
    consider 3 different scenarios: the first progress with this value of R0, the
    second increases social isolation to obtain a lower R0 and the third loosen
    social isolation and correspond to a higher R0."""
        ).format(**subs)
    )

    st.subheader("Scenario 1: more isolation")
    msg = _("What is the new R0?")
    R0_tight = st.slider(msg, 0.1, R0, R0 * 0.66)

    st.subheader("Scenario 2: less isolation")
    R0_loose = st.slider(msg, R0, max(2 * R0, 3.0), 1.33 * R0)
    R0_list = (R0, R0_tight, R0_loose)

    # Parameters
    st.header(_("Parameters"))
    st.subheader(_("Healthcare system"))
    if np.isnan(region.icu_capacity):
        population = region.population

        msg = _("Total ICU beds")
        icu = int(population / 10_000)
        icu = st.number_input(msg, min_value=0, value=icu)

        msg = _("Total hospital beds")
        hospital = int(population / 1_000)
        hospital = st.number_input(msg, min_value=0, value=hospital)

    else:
        icu = region.icu_capacity
        hospital = region.hospital_capacity

    msg = _("Fraction of ICU beds that is occupied?")
    rate = 1 - st.slider(msg, 0, 100, value=75) / 100

    # Options
    def ask(title, **kwargs):
        if embed:
            return True
        return st.checkbox(title, **kwargs)

    st.header(_("Options"))
    st.subheader(_("Plotting options"))
    options = {"logy": not ask(_("Linear scale")), "grid": not ask(_("Hide grid"))}
    st.subheader(_("Advanced information"))
    options = {
        "plot_opts": options,
        "show_weekday_rate": ask(_("Notification per weekday")),
    }

    return {
        "region": region,
        "icu_capacity": icu,
        "hospital_capacity": hospital,
        "icu_surge_capacity": rate * icu,
        "hospital_surge_capacity": rate * hospital,
        "R0_list": R0_list,
        **options,
    }


@st.cache(show_spinner=False)
def start_model(region: RegionT, disease="covid-19"):
    """
    Start model with cases data for the given region.
    """

    cases = region.pydemic.epidemic_curve(disease=disease, real=True, keep_observed=True)
    m = SEAIR(region=region, disease=disease)
    m.set_cases(cases, adjust_R0=True, save_observed=True)
    m.info.save_event("simulation_start")
    return m


@st.cache(show_spinner=False)
def start_group(model: Model, duration=60, R0_list=()):
    """
    Split into 4 models: a forecast model, one that tighten social distancing by
    the given amount delta, one that loosen social distancing by the same ammount
    and one that completely lift social distancing measures
    """
    models = model.split(R0=R0_list, name=["baseline", "isolate", "open"])
    models.run(duration)
    return models


def show_outputs(base, group, region: RegionT, plot_opts, clinical_opts, **kwargs):
    """
    Show results from user input.
    """
    cmodels = group.clinical.overflow_model(**clinical_opts)
    cforecast = cmodels[0]
    start = base.info["event.simulation_start"]

    #
    # Introduction
    #
    st.header(_("Introduction"))
    st.markdown(report_intro(region))
    st.cards(
        {
            _("Basic reproduction number"): fmt(base.R0),
            _("Ascertainment rate"): pc(base.info["observed.notification_rate"]),
        },
        color="st-gray-900",
    )

    #
    # Forecast
    #
    st.header(_("Forecasts"))
    st.markdown(forecast_intro(region))

    # Infectious curve
    group["infectious:dates"].plot(**plot_opts)
    mark_x(start.date, "k--")
    plt.legend()
    plt.title(_("Active cases"))
    plt.tight_layout()
    st.pyplot()

    st.markdown("#### " + _("Download data"))
    opts = ["critical", "severe", "infectious", "cases", "deaths"]
    default_columns = ["critical", "severe", "cases", "deaths"]
    columns = st.multiselect(_("Select columns"), opts, default=default_columns)

    rename = dict(zip(range(len(columns)), columns))
    columns = [c + ":dates" for c in columns]
    data = pd.concat(
        [cm[columns].rename(rename, axis=1) for cm in cmodels], axis=1, keys=cmodels.names
    )
    st.data_anchor(data.astype(int), f"data-{region.id}.csv")

    #
    # Reopening
    #
    st.header(_("When can we reopen?"))
    st.markdown(reopening_intro(region))

    st.subheader(_("Step 1: Controlling the curve"))
    st.markdown(rt_intro(region))

    st.subheader(_("Step 2: Testing"))
    st.markdown(rt_intro(region))
    if kwargs.get("show_weekday_rate"):
        region.ui.weekday_rate()

    st.subheader(_("Step 3: Hospital capacity"))
    st.markdown(rt_intro(region))

    # Hospitalization
    cmodels["critical:dates"].plot(**plot_opts)
    mark_x(start.date, "k--")
    mark_y(cforecast.icu_surge_capacity, "k:")
    plt.legend()
    plt.title(_("Critical cases"))
    plt.tight_layout()
    st.pyplot()


@st.cache
def report_intro(region):
    name = _(region.name)
    return _(
        """{name} is in a **(good|bad|ugly)** state, yadda, yadda, yadda.

The plot bellow shows the progression of cases and deaths.
"""
    ).format(**locals())


@st.cache
def forecast_intro(region):
    name = _(region.name)
    return _(
        """Epidemic forecasting depends on good data, which is hard to find.
Take it with a grain of salt.
"""
    ).format(**locals())


@st.cache
def reopening_intro(region):
    name = _(region.name)
    return _("""...""").format(**locals())


@st.cache
def rt_intro(region):
    name = _(region.name)
    return _("""...""").format(**locals())


#
# Auxiliary methods
#
def scenarios_table(group, col, t0=0, days=(7, 15, 30, 60), download=False):
    """
    Display a table showing some column for the given value in the requested days.
    """
    steps = np.array(days)
    times = t0 + steps
    region = group[0].region

    data = group[col, times].astype(int).applymap(fmt)
    dates = pd.DataFrame({_("Date"): group[0].to_dates(times)}, index=times)
    data = pd.concat([dates, data], axis=1)
    data = data.set_axis(steps)
    st.table(data, link=f"{col}-table-{region.id}.csv" if download else None)


if __name__ == "__main__":
    main()
