import numpy as np
import pandas as pd
import sidekick as sk

from pydemic_ui import builtins

builtins.main()
builtins.reload("pydemic.models")

import mundi
from pydemic.models import Model, SEAIR
from pydemic.utils import as_seq
from pydemic_ui import st


# references:
# https://farolcovid.coronacidades.org/
# https://covidactnow.org/?s=38532


@sk.fn.curry(1)
def observed_curves(model: Model, notification_rate=None, method="rate", dates=False):
    """
    Infer the observed cases curve from model, notification_rate and some
    other parameters.
    """
    if notification_rate is None:
        notification_rate = model.info.get("observed.notification_rate", 1.0)

    if method == "rate":
        cases = model["cases"] * notification_rate
        deaths = model["deaths"]
        columns = ["cases", "deaths"]
        data = pd.concat([cases, deaths], axis=1).set_axis(columns, axis=1)
    else:
        raise ValueError(f"invalid inference method: {method}")

    if dates:
        data.index = model.to_dates(data.index)
    return data


@sk.fn.curry(3)
def backcasting(
    predictor,
    window,
    curves,
    distance="RMS",
    columns=("cases", "deaths"),
    min_series=14,
    step=1,
):
    """
    Perform a backcasting performance analysis of the given model. For the sake
    of this method, the model is just a function that receives an epidemic curve
    dataframe and a list of time windows and return the forecasts for cases and
    deaths for the specified times.

    Args:
        cases:
        fn:
        window:

    Returns:

    """
    windows = np.array(as_seq(windows))
    min_window = windows.min(initial=len(curves))

    def distance(x, y):
        return (x - y).dropna().abs() / x

    results = []
    for k in range(min_window, len(curves) - min_series, step):
        data = curves.iloc[:-k]
        prediction = fn(data, windows)
        results.append(distance(curves, prediction))
    st.write(results[-1])

    return pd.concat(results, axis=0)


def predictor(self, kind="epidemic_curves", **kwargs):
    """
    Return a predictor function to model
    """

    if kind == "epidemic_curves":

        def predictor(curves, window):
            m = self.copy()
            m.fit(curves, **kwargs)
            m.run(window)
            data = m[[x + ":dates" for x in curves.columns]].iloc[-window:]
            data.columns = curves.columns
            return data

    else:
        raise ValueError("invalid predictor type")

    return predictor


def fit(self, data):
    """
    Fit model to epidemic curve.
    """
    self.set_cases(data, adjust_R0=True)


Model.predictor = predictor
Model.fit = fit

region = mundi.region("IT")
model = SEAIR(region=region).clinical.overflow_model()
params = model.disease_params
predictor = model.predictor()

curves: pd.DataFrame = region.pydemic.epidemic_curve()
curves = curves.reset_index().drop_duplicates("date", keep="first").set_index("date")

tf = curves.index[-1]
notification_ratio = params.CFR / (curves.loc[tf, "deaths"] / curves.loc[tf, "cases"])
curves["cases"] /= notification_ratio | dbg

start, end = curves.index[[0, -1]]
full_index = pd.to_datetime(np.arange((end - start).days), unit="D", origin=start)
curves = curves.reindex(full_index).fillna(method="ffill")

train = curves.iloc[:-15]
test = curves.iloc[-15:]

data = predictor(train, 15)
df = pd.concat([data, test], axis=1, keys=["predicted", "observed"])
st.line_chart(df["predicted", "deaths"] / df["observed", "deaths"])
st.line_chart(df["predicted", "cases"] / df["observed", "cases"])
st.pyplot()

df.plot(grid=True, logy=True)
st.pyplot()
