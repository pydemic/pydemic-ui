import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import mundi
from pydemic import fitting as fit
from pydemic import formulas
from pydemic import models
from pydemic.diseases import covid19
from pydemic.utils import fmt, today
from pydemic_ui import components as ui
from pydemic_ui import info
from pydemic_ui import st
from pydemic_ui.i18n import _


@st.cache
def get_epidemic_curves(refs: list):
    curves = []
    for ref in refs:
        curve = covid19.epidemic_curve(ref)
        curve.columns = pd.MultiIndex.from_tuples((ref, col) for col in curve.columns)
        curves.append(curve)

    return pd.concat(curves, axis=1).dropna()


@st.cache
def get_growths(refs, which="cases"):
    data = []
    curves = get_epidemic_curves(refs)
    for ref in refs:
        series = curves[ref, which]
        sdiff = fit.smoothed_diff(series)[-30:]
        data.append(fit.growth_factor(sdiff))
    return pd.DataFrame(data, index=refs).sort_index()


@st.cache(allow_output_mutation=False)
def run_models(refs, which):
    growths = get_growths(refs, which)
    R0s = []
    ms = []
    ms_bad = []
    ms_good = []
    for st_, (g, _) in growths.iterrows():
        params = covid19.params(region=st_)
        R0 = min(formulas.R0_from_K("SEAIR", params, K=np.log(g)), 2.5)
        R0s.append(R0)
        m = models.SEAIR(disease=covid19, region=st_, R0=R0)
        m.set_data(info.get_seair_curves_for_region(st_))
        base = m.copy()

        m.run(120)
        ms.append(m.clinical.overflow_model())

        m = base.copy(R0=2.74)
        m.run(120)
        ms_bad.append(m.clinical.overflow_model())

        m = base.copy(R0=1.0)
        m.run(120)
        ms_good.append(m.clinical.overflow_model())
    return map(tuple, [ms_good, ms, ms_bad])


def collect_inputs(region="BR", where=st.sidebar):
    states = mundi.regions(region, type="state")
    highlight = where.selectbox(_("Select a state to highlight"), states.index)

    msg = _("Which kind of curve to you want to analyze?")
    which = where.selectbox(msg, ["cases", "deaths"])

    return {
        "loc": highlight,
        "idx": int(which == "deaths"),
        "states": states,
        "which": which,
    }


def show_results(states, loc, idx, which, disease=covid19):
    curves = get_epidemic_curves(states.index).fillna(0)

    # Acc cases
    ax = curves.iloc[-30:, idx::2].plot(legend=False, grid=True)
    curves[loc, which].iloc[-30:].plot(ax=ax, legend=False, grid=True)
    st.pyplot()

    # Daily cases
    ax = curves.iloc[-30:, idx::2]
    curves[loc, which].iloc[-30:].diff().plot(ax=ax, legend=False, grid=True)
    st.pyplot()

    # Growth factors
    growths = get_growths(states.index, which)
    ci = pd.DataFrame({"low": growths["value"] - growths["std"], "std": growths["std"]})

    st.header("Growth factor +/- error")
    ci.plot.bar(width=0.9, ylim=(0.8, 2), stacked=True, grid=True)
    plt.plot(states.index, [1] * len(states), "k--")
    st.pyplot()

    # Duplication times
    st.header("Duplication time")
    (np.log(2) / np.log(growths["value"])).plot.bar(grid=True, ylim=(0, 30))
    st.pyplot()

    # R0
    st.header("R0")
    params = covid19.params(region=loc)
    (
        np.log(growths["value"])
        .apply(lambda K: formulas.R0_from_K("SEAIR", params, K=K))
        .plot.bar(width=0.9, grid=True, ylim=(0, 4))
    )
    st.pyplot()

    ms_good, ms_keep, ms_bad = run_models(states.index, which)

    # ICU overflow
    for ms, msg in [
        (ms_keep, "keep trends"),
        (ms_bad, "no distancing"),
        (ms_good, "more distancing"),
    ]:
        st.header(f"Deaths and ICU overflow ({msg})")

        deaths = pd.DataFrame({m.region.id: m["deaths:dates"] for m in ms})
        deaths.plot(legend=False, color="0.5")
        deaths.sum(1).plot(grid=True)
        deaths[loc].plot(legend=True, grid=True)

        st.cards({"Total de mortes": fmt(deaths.iloc[-1].sum())})
        st.pyplot()

        data = {}
        for m in ms:
            overflow = m.results["dates.icu_overflow"]
            if overflow:
                data[m.region.id] = (overflow - pd.to_datetime(today())).days
        if data:
            data = pd.Series(data)
            data.plot.bar(width=0.9, grid=True)
            st.pyplot()


def main(embed=False, disease=covid19):
    if not embed:
        ui.css(keep_menu=True)

    if not embed:
        ui.logo(where=st.sidebar)

    st.title(_("Projections for COVID-19 evolution in Brazil"))
    inputs = collect_inputs(where=st if embed else st.sidebar)
    show_results(disease=disease, **inputs)


if __name__ == "__main__":
    main()
