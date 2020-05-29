import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from statsmodels import api as sm

from pydemic import fitting as fit
from pydemic import formulas
from pydemic.models import Model, SEAIR
from pydemic.plot import mark_x, mark_y
from pydemic.region import RegionT
from pydemic.types import ValueStd
from pydemic.utils import extract_keys, trim_zeros, fmt
from pydemic_ui import st
from pydemic_ui.i18n import _

pd = pd
np = np
SHOW_OPTS = ("show_cases_plot", "show_weekday_rate", "healthcare_available")
START_OPTS = ("notification_rate",)
RUN_OPTS = ("R0", "duration")


def main(embed=False):
    """
    Run application.
    """
    if not embed:
        st.css(keep_menu=True)
        st.sidebar.logo()
        st.title(_("Epidemic projections"))

    opts = sidebar(where=st if embed else st.sidebar, embed=embed)
    show_opts = extract_keys(SHOW_OPTS, opts)
    start_opts = extract_keys(START_OPTS, opts)
    run_opts = extract_keys(RUN_OPTS, opts)

    model = start_model(**opts, **start_opts)
    model = run_model(model, **run_opts)
    show_outputs(model, **opts, **show_opts)


def sidebar(where=st.sidebar, embed=False):
    """
    Collect inputs in the sidebar or other location.
    """

    st = where
    region = st.select_region("BR")

    st.header(_("Parameters"))
    extra = {
        "R0": st.slider(_("R0"), 0.0, 5.0, value=2.0),
        "duration": st.slider(_("Duration (weeks)"), 1, 32, value=8) * 7,
    }

    # Notification rate
    msg = _("How should we compute the ascertainment rate?")
    opts = {"deaths": _("From deaths"), "value": _("Explicit value")}
    opt = st.radio(msg, list(opts), format_func=opts.get)
    if opt == "value":
        msg = _("Notification rate")
        extra["notification_rate"] = (st.slider(msg, 0.0, 100.0, value=10.0) / 100,)
    else:
        extra["notification_rate"] = "deaths"

    st.subheader(_("Healthcare system"))
    msg = _("Percentage of ICU available to treat COVID")
    extra["healthcare_available"] = st.slider(msg, 0, 100, value=25) / 100

    return {"region": region, **extra, **sidebar_options(st, embed)}


def start_model(region: RegionT, notification_rate: float, disease="covid-19"):
    m = SEAIR(region=region, disease=disease)
    m.set_cases(notification_rate=notification_rate, adjust_R0=True)
    return m


def run_model(model: Model, R0, duration):
    name1 = _("Projection (R0 = {R0})").format(R0=fmt(model.R0))
    name2 = _("Selected R0 ({R0})").format(R0=R0)
    models = model.split(R0=[model.R0, R0], name=[name1, name2])
    models.run(duration)
    return models


def show_outputs(
    models, region, show_cases_plot, show_weekday_rate, healthcare_available
):
    """
    Show results from user input.
    """

    region.ui.epidemic_summary()
    if show_cases_plot:
        region.ui.epidemic_curve(logy=True, grid=True)
    if show_weekday_rate:
        region.ui.weekday_rate()

    curves = region.pydemic.epidemic_curve()
    simulation_date = models[0].info["observed.dates"][1]
    notification_rate = models[0].info["cases.notification_rate"]

    # Linear model for logs
    Y = np.log(np.maximum(np.diff(curves["cases"], prepend=0), 0.5))
    X = np.arange(len(Y))
    ols = sm.OLS(Y, sm.add_constant(X), missing="drop")
    res = ols.fit()
    cte, K = res.params
    st.line_chart(np.array([Y - cte, K * X]).T)
    st.text(res.summary())

    # Model with seasonal variance
    w = 2 * np.pi / 7
    Xcos = np.cos(w * X)
    Xsin = np.sin(w * X)
    exog = sm.add_constant(np.array([X, Xcos, Xsin]).T)
    ols = sm.OLS(Y, exog, missing="drop")
    res = ols.fit()
    cte, K, a, b = res.params
    seasonal = a * Xcos + b * Xsin
    st.line_chart(np.array([Y - cte, K * X, K * X + a * Xcos + b * Xsin]).T)
    st.line_chart(np.array([Y - cte - K * X, Y - cte - seasonal - K * X]).T)
    st.text(res.summary())

    # Rolling OLS
    from statsmodels.regression.rolling import RollingOLS

    ols = RollingOLS(Y - seasonal, sm.add_constant(X), window=14)
    res = ols.fit()
    df = pd.DataFrame(res.params, columns=["cte", "K"])
    st.line_chart(formulas.R0_from_K("SEAIR", models[0], K=df["K"]))

    st.header(_("Simulation results"))
    st.subheader(_("Infectious curve"))

    df = models["cases:dates"]
    ax = curves["cases"].plot(label=_("Confirmed cases"))
    (curves["cases"] / notification_rate).plot(ax=ax, label=_("Adjusted cases"))
    df.plot(grid=True, logy=True, ax=ax, ylim=(max(10, min(df.iloc[0])), None))
    mark_x(simulation_date, "k--")
    plt.legend()
    plt.title(_("Accumulated cases"))
    st.pyplot()

    df = models["infectious:dates"]
    df.plot(grid=True, logy=True)
    mark_x(simulation_date, "k--")
    plt.legend()
    plt.title(_("Infectious"))
    st.pyplot()

    st.subheader(_("Hospitalization"))
    cm = models.clinical.overflow_model()
    cm[["severe:dates", "critical:dates"]].plot(grid=True, logy=True, ylim=(10, None))
    mark_y(region.icu_capacity * healthcare_available, "k:")
    mark_y(region.hospital_capacity * healthcare_available, "k:")
    mark_x(simulation_date, "k--")
    st.pyplot()

    ax = curves["deaths"].plot()
    cm[["deaths:dates"]].plot(grid=True, logy=True, ylim=(10, None), ax=ax)
    mark_x(simulation_date, "k--")
    st.pyplot()


#
# Auxiliary methods
#
def sidebar_options(where=st, embed=False):
    """
    Auxiliary sidebar method.
    """

    st = where

    def ask(title, **kwargs):
        if embed:
            return True
        return st.checkbox(title, **kwargs)

    st.header(_("Options"))
    st.subheader(_("Show elements"))
    return {
        "show_cases_plot": ask(_("Cases and deaths chart")),
        "show_weekday_rate": ask(_("Notification per weekday")),
    }


def set_cases(
    self: Model, cases=None, notification_rate=None, adjust_R0=False, save_cases=False
):
    """
    Initialize model from a dataframe with the deaths and cases curve.

    This curve is usually the output of disease.epidemic_curve(region), and is
    automatically retrieved if not passed explicitly and the region of the model
    is set.

    Args:
        cases:
            Dataframe with cumulative ["cases", "deaths"] columns. If not given,
            or None, fetches from disease.epidemic_curves(info)
        notification_rate:
            If given, controls the fraction of cases that where observed.
        adjust_R0:
            If true, adjust R0 from the observed cases.
        save_cases:
            If true, save the cases curves into the model.info["observed.cases"] key.
    """

    if cases is None:
        if self.region is None or self.disease is None:
            msg = 'must provide both "region" and "disease" or an explicit cases curve.'
            raise ValueError(msg)
        cases = self.region.pydemic.epidemic_curve(self.disease)

    model = self._meta.model_name
    if adjust_R0:
        method = "OLS" if adjust_R0 is True else adjust_R0
        Re, _ = value = adjust_R0_from_cases(model, cases, self, method=method)
        assert np.isfinite(Re), f"invalid value for R0: {value}"

        self.R0 = Re
        self.info["stats.R0"] = value

    # Select notification rate and save it in the info dictionary for reference
    if notification_rate in ("deaths", "CFR", None):
        CFR = self.disease_params.CFR
        last = cases.iloc[-1]
        empirical_CFR = last["deaths"] / last["cases"]
        notification_rate = CFR / empirical_CFR
    self.info["cases.notification_rate"] = notification_rate

    # Save simulation state from data
    curve = cases["cases"] / notification_rate
    data = fit.epidemic_curve(model, curve, self)
    self.set_data(data)
    self.initial_cases = curve.iloc[0]

    if adjust_R0:
        self.R0 /= self["susceptible:final"] / self.population

    # Optionally save cases curves into the info dictionary
    if save_cases:
        key = "observed.cases" if save_cases is True else save_cases
        df = cases.copy()
        df["cases"] = curve
        df["cases_raw"] = cases["cases"]
        self.info[key] = df


def adjust_R0_from_cases(model, cases, params, method="OLS") -> ValueStd:
    """
    Read curve of cases and adjust the model R0 from cases.
    """
    # Methods that infer the growth ratio between successive observations
    if method.startswith("ratio-"):
        r, dr = growth_ratio_from_cases(cases, method=method[6:])

        R0 = formulas.R0_from_K(model, params, K=np.log(r))
        R0_plus = formulas.R0_from_K(model, params, K=np.log(r - min(dr, 0.9 * r)))
        R0_minus = formulas.R0_from_K(model, params, K=np.log(r + dr))

    # Methods that infer the exponential growth factor
    elif method in ("OLS",):
        K, dK = growth_factor_from_cases(cases, method=method)

        R0 = formulas.R0_from_K(model, params, K=K)
        R0_plus = formulas.R0_from_K(model, params, K=K - dK)
        R0_minus = formulas.R0_from_K(model, params, K=K + dK)

    else:
        raise ValueError(f"invalid method: {method!r}")

    dR0 = abs(R0_plus - R0_minus) / 2
    return ValueStd(R0, dR0)


def growth_ratio_from_cases(curves, method="GGBayes", **kwargs) -> ValueStd:
    """
    Return the growth rate combining the "cases" and "deaths" columns of an
    epidemic curve.

    Args:
        curves:
            A DataFrame with "cases" and "deaths" columns.

    Keyword Args:
        Additional keyword arguments are passed to the smoothed_diff function.

    See Also:
        :func:`pydemic.fitting.smoothed_diff`
    """

    if method == "GGBayes":
        fn = lambda col: clean_exponential(curves[col], diff=True, **kwargs)
        cases, deaths = map(fn, curves.columns)
        ratios = [fit.growth_factor(cases), fit.growth_factor(deaths)]
        return fit.average_growth(ratios)
    else:
        raise ValueError


def growth_factor_from_cases(curves, method="OLS", **kwargs) -> ValueStd:
    """
    Return the growth rate combining the "cases" and "deaths" columns of an
    epidemic curve.

    Args:
        curves:
            A DataFrame with "cases" and "deaths" columns.

    Keyword Args:
        Additional keyword arguments are passed to the smoothed_diff function.

    See Also:
        :func:`pydemic.fitting.smoothed_diff`
    """

    if method == "OLS":

        def stats(col):
            data = curves[col]
            data = clean_exponential(data, diff=True, **kwargs)
            Y = np.log(data / data[0])
            X = np.arange(len(Y))
            ols = sm.OLS(Y, sm.add_constant(X))
            res = ols.fit()
            _, K = res.params
            ci = res.conf_int()
            dK = (ci[1, 1] - ci[1, 0]) / 2
            return ValueStd(K, dK)

        cases, deaths = map(stats, curves.columns)
        return fit.average_growth([cases, deaths])
    else:
        raise ValueError


def clean_exponential(curve, diff=False, smoothing_level=1 / 10, **kwargs):
    """
    Clean exponential curve removing outliers and initialization.
    """
    curve: np.ndarray = trim_zeros(curve)
    if diff:
        kwargs["smoothing_level"] = smoothing_level
        curve = fit.smoothed_diff(curve, **kwargs)
        curve = trim_zeros(curve)

    curve = curve[-30:]
    return curve


Model.set_cases = set_cases

if __name__ == "__main__":
    main()
