import numpy as np
import pandas as pd
import streamlit as st

import mundi
import mundi_demography as mdm
from pydemic.diseases import covid19 as disease
from pydemic.fitting.smoothing import smoothed_diff
from pydemic.params import get_param
from pydemic_ui.apps.curve import seair_curves, infectious_curve
from pydemic_ui.i18n import gettext as _

region = st.sidebar.text_input(_("Region"), value="BR")
with st.spinner(_("Downloading epidemic curve")):
    curve = disease.epidemic_curve(region)

st.write(mundi.region(region).to_series("name", "population"))
st.line_chart(curve)

gamma = get_param("gamma", disease.params())
sigma = get_param("sigma", disease.params())
population = mdm.population(region)

Qs = 0.14
if st.sidebar.checkbox(_("Use deaths")):
    cases = curve["deaths"] * (Qs / disease.IFR(age_distribution=region))
else:
    cases = curve["cases"]


infectious = infectious_curve(cases, gamma, smooth=True)

R0 = get_param("R0", disease.params())
R0 = st.sidebar.number_input("R0", value=R0)
sm = st.sidebar.number_input("Smooth", value=0.2)
ds = int(st.sidebar.number_input("days", value=3))

kwargs = dict(
    sigma=sigma,
    gamma=gamma,
    R0=R0,
    Rt_smooth=sm,
    smooth_days=ds,
    ret_Rt=True,
    population=population,
    smooth=True,
)
data = seair_curves(cases, prob_symptoms=Qs, rho=0.4, **kwargs)
# data = seir_curves(cases, **kwargs)
data = data.drop(columns="susceptible")
Rt = data.pop("Rt")
data *= 100 / population


st.line_chart(
    pd.DataFrame({"cases": np.maximum(cases.diff(), 0), "smooth": smoothed_diff(cases)})
)
st.line_chart(Rt)
st.line_chart(data)
st.line_chart(data.sum(1))
st.bar_chart(data.iloc[-1])
