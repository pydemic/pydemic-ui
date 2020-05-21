from pydemic import fitting as fit
from pydemic import formulas
from pydemic import models
from pydemic.all import *
from pydemic_ui import info
from pydemic_ui import st

st.css(keep_menu=True)
br = mundi.region("BR")
states = mundi.regions("BR", type="state")

loc = st.selectbox("State", states.index)
which = st.selectbox("Which?", ["cases", "deaths"])
idx = int(which == "deaths")


def get_data(ref):
    curve = covid19.epidemic_curve(ref)
    curve.columns = pd.MultiIndex.from_tuples((ref, col) for col in curve.columns)
    return curve


def get_all_curves(refs):
    refs = getattr(refs, "index", refs)
    return pd.concat([get_data(ref) for ref in refs], axis=1)


curves = get_all_curves(states).fillna(0)
ax = curves.iloc[-30:, idx::2].plot(
    logy=True, grid=True, ylim=(10, None), legend=False, color="0.5"
)
ax = (
    curves[loc, which]
    .iloc[-30:]
    .plot(logy=True, grid=True, ylim=(10, None), legend=False, color="red", ax=ax)
)

st.pyplot()


@st.cache
def get_growths(which="cases"):
    data = []
    for r in states.index:
        series = curves[r, which]
        sdiff = fit.smoothed_diff(series)[-30:]
        data.append(fit.growth_factor(sdiff))
    return pd.DataFrame(data, index=states.index)


growths = get_growths(which)
ci = pd.DataFrame({"low": growths["value"] - growths["std"], "std": growths["std"]})

st.header("Growth factor +/- error")
ci.plot.bar(width=0.9, ylim=(0.8, None), stacked=True, grid=True)
plt.plot(states.index, [1] * len(states), "k--")
st.pyplot()

st.header("Duplication time")
(np.log(2) / np.log(growths["value"])).plot.bar(grid=True)
st.pyplot()

st.header("R0")
params = covid19.params(region=region)
(
    np.log(growths["value"])
    .apply(lambda K: formulas.R0_from_K("SEAIR", params, K=K))
    .plot.bar(width=0.9, grid=True)
)
st.pyplot()


@st.cache(allow_output_mutation=True)
def run_models(which):
    growths = get_growths(which)
    R0s = []
    ms = []
    ms_bad = []
    ms_good = []
    for st_, (g, _) in growths.iterrows():
        params = covid19.params(region=st_)
        R0 = formulas.R0_from_K("SEAIR", params, K=np.log(g))
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
    return ms_good, ms, ms_bad


ms_good, ms_keep, ms_bad = run_models(which)

# ICU overflow
for ms, msg in [
    (ms_keep, "keep trends"),
    (ms_bad, "no distancing"),
    (ms_good, "more distancing"),
]:
    st.header(f"Deaths and ICU overflow ({msg})")

    deaths = pd.DataFrame({m.region.id: m["deaths:dates"] for m in ms})
    deaths.plot(legend=False, color="0.5")
    deaths.sum(1).plot(grid=True, logy=True, label="Soma")
    deaths[loc].plot(grid=True, logy=True, legend=True)
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
