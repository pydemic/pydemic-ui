import base64
import io

import pandas as pd

import mundi
import pydemic_ui.pyplot as plt
from pydemic import models
from pydemic.diseases import covid19
from pydemic.utils import fmt, pc
from pydemic_ui import components as ui
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui.i18n import _


def get_column(col, lst):
    return pd.DataFrame({m.name: m[col] for m in lst})


def shift_index(df, n):
    df = df.copy()
    df.index = df.index - n
    return df


def progression_cards(deaths, color="st-blue"):
    deaths = deaths.values[-60:]
    st.cards(
        {
            _("7 days"): fmt(deaths[6]),
            _("15 days"): fmt(deaths[14]),
            _("30 days"): fmt(deaths[29]),
            _("60 days"): fmt(deaths[59]),
        },
        color=color,
    )


def hospitalization_chart(model, shift=0):
    df = model[["severe", "critical"]]
    df.index = df.index - shift
    df.plot(logy=logy, grid=grid)
    plt.mark_y(
        model.hospital_surge_capacity, "--", color=plt.color(2), label=_("Hospital beds")
    )
    plt.mark_y(model.icu_surge_capacity, "--", color=plt.color(2), label=_("ICU"))
    if shift:
        plt.mark_x(0, "k--")
    plt.legend()
    plt.tight_layout("x")
    st.pyplot()


def plot_cases_and_projection(model, cases):
    cases = cases.reset_index(drop=True)
    cases.index = cases.index - len(cases)
    corrected = cases["cases"] / notification
    cases["cases"].plot(style="o", alpha=0.25, label=_("Cases"))
    cases["deaths"].plot(style="o", alpha=0.5, label=_("Deaths"))
    corrected.plot(style="o", alpha=0.5, c=plt.color(2), label=_("Cases (corrected)"))

    m_cases = model["cases"]
    m_cases.index = m_cases.index - len(cases)
    m_cases.plot(color=plt.color(3), label=_("Cases (projected)"), lw=2)

    m_deaths = model["deaths"]
    m_deaths.index = m_deaths.index - len(cases)
    m_deaths.plot(color=plt.color(3), label=_("Deaths (projected)"), lw=2)
    plt.ylim(10, None)
    plt.mark_x(0, "k--")
    plt.tight_layout("x")

    plt.legend()
    if grid:
        plt.grid()
    if logy:
        plt.yscale("log")
    st.pyplot()


@st.cache(allow_output_mutation=True)
def run_model(region, duration, R0, notification_rate):
    m = models.SEAIR(region=region, disease=covid19, R0=R0)

    data = info.get_seair_curves_for_region(region, notification_rate=notification_rate)
    m.set_data(data)
    m.initial_cases = info.get_cases_for_region(region)["cases"].iloc[0]
    m.run(duration)
    return m.clinical.overflow_model()


#
# ASK INFO
#
st.css()
st.sidebar.logo()
code = st.sidebar.select_region("BR")
region = mundi.region(code)
params = covid19.params(region=region)

st.sidebar.subheader(_("Parameters"))
duration = 60  # st.sidebar.number_input(_("Duration (days)"), 1, 120, value=60)
notification = st.sidebar.slider(_("Ascertainment ratio"), 0.01, 0.50, value=0.10)
R0 = st.sidebar.slider(_("R0"), 0.1, 5.0, value=params.R0)

st.sidebar.subheader(_("Options"))
logy = not st.sidebar.checkbox(_("Linear scale"))
grid = not st.sidebar.checkbox(_("Hide grid"))

st.title("Epidemic projections")
st.markdown(
    """
This simple fetches epidemic curves from Brasil.io and other public data
sources and make predictions to the future of the epidemic from those
values.
"""
)

# Show cases
cases = info.get_cases_for_region(region)
data = info.get_seair_curves_for_region(region, notification_rate=notification)

n_cases = len(cases)
ui.cases_and_deaths_plot(cases, logy=logy, grid=grid)

# Run model
cm = run_model(region, duration, R0, notification)
data_size = cm.iter - duration

# Show results
st.header("Simulation results")
st.subheader("Cases and deaths")
plot_cases_and_projection(cm, cases)

#
# Cards
#
st.subheader(_("New deaths"))
progression_cards(cm["deaths"], color="st-red")

st.subheader(_("New cases"))
opts = [_("Estimated"), _("Reported")]
is_reported = st.radio(_("Reporting"), [0, 1], format_func=opts.__getitem__)
mul = notification if is_reported else 1.0
progression_cards(cm["cases"] * mul, color="st-gray-900")

st.subheader(_("Hospitalizations"))
hospitalization_chart(cm, shift=len(cases))

st.subheader(_("Projections"))
m = cm.infection_model
date = m.dates[data_size]
base = cm.infection_model.trim_dates(0, data_size)
assert len(base.data) == data_size, (data_size, len(base.data), len(m.times))

valid_rates = [0.1 * i for i in range(1, 10)]
rates = [valid_rates[i] for i in [6, 4, 2]]
msg = _("Isolation score")
rates = st.multiselect(msg, valid_rates, format_func=pc, default=rates)

columns = ["severe", "critical", "cases", "deaths"]
valid_columns = [*columns, "infectious", "recovered", "asymptomatic"]
msg = _("Columns")
columns = st.multiselect(msg, valid_columns, format_func=str.title, default=columns)

ms = [
    base.copy(
        R0=base.R0 * (1 - rate), name=f"Isolation {pc(rate)}"
    ).clinical.overflow_model()
    for rate in rates
]

for m in ms:
    m.run(duration)

data = {col: get_column(col, ms) for col in columns}
for k, df in data.items():
    st.subheader(k)
    shift_index(df, n_cases).plot(logy=logy, grid=grid)
    plt.tight_layout("x")
    plt.mark_x(0, "k--", lw=2)
    st.pyplot()

st.subheader(_("Dataset"))
opts = {
    "show": _("Show in screen"),
    "csv": _("Comma separated values"),
    "xlsx": _("Excel"),
}
mime = {"csv": "text/csv", "xls": "application/vnd.ms-excel"}

opt = st.radio(_("How do you want your data?"), list(opts), format_func=opts.get)
df = pd.concat(data, axis=1)
df.index = base.to_dates(df.index)
df = df.astype(int)

if not st.checkbox(_("Keep observed period")):
    df = df.iloc[data_size:]

if opt == "show":
    st.write(df)
else:
    df.index = [d.strftime("%Y-%m-%d") for d in df.index]
    if opt == "csv":
        fd = io.StringIO()
        df.to_csv(fd)
        data = fd.getvalue().encode("utf8")
    else:
        fd = io.BytesIO()
        df.to_excel(fd)
        data = fd.getvalue()
    data = base64.b64encode(data).decode("utf8")
    name = f"curves-%s.{opt}" % region.id
    msg = _("Right click link to download")
    st.html(f'<a href="data:{opt};base64,{data}" download="{name}">{msg}</a>')
