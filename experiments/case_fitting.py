import numpy as np
import pandas as pd

import mundi
from pydemic import fitting as fit, models
from pydemic.diseases import covid19
from pydemic_ui import st

region = mundi.region(st.text_input("Region", value="BR"))
params = covid19.params(region=region)
cases = covid19.epidemic_curve(region)


def fit_infectious(df, gamma=params.gamma, fmt="{}-smooth", **kwargs):
    return pd.DataFrame(
        {
            fmt.format(key): _infectious_curve(col, gamma, **kwargs)
            for key, col in df.items()
        },
        index=df.index,
    )


def _infectious_curve(col, gamma, **kwargs):
    cases = fit.infectious_curve(col, gamma, **kwargs)
    cases *= col[-1] / cases.sum()
    return cases


def seir_curves(cases, params, **kwargs):
    for param in ["gamma", "sigma", "prob_symptoms", "rho", "R0"]:
        kwargs.setdefault(param, getattr(params, param))
    return fit.seair_curves(cases, **kwargs)


notification = st.slider("Sub-notificação", 0.01, 0.30, value=0.13)
R0 = st.slider("R0", 0.1, 3.0, value=2.0)

m = models.SEAIR(region=region, disease=covid19, R0=R0)
data = seir_curves(cases["cases"] / notification, params, population=region.population)
m.set_ic(state=data.iloc[0])
m.data = data.reset_index(drop=True)
m.time = len(m.data) - 1
m.date = data.index[-1]
m.state[:] = data.iloc[-1]
m._initialized = True
m.run(60)

cm = m.clinical.overflow_model()
ax = cases.plot(logy=True)
ax = (cases["cases"] / notification).plot(logy=True, ax=ax)
cm.plot(["cases:dates", "deaths:dates"], log=True, ax=ax)
st.pyplot()

df = pd.concat([cases.diff(), fit_infectious(cases)], axis=1)
df = np.maximum(df, 1).dropna()

st.line_chart(np.log(df))
