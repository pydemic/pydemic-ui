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
from pydemic_ui.app import SimpleApp, Timer

class ProjectionsBR(SimpleApp):
    title = "Projections for COVID-19 evolution in Brazil"

    def __init__(self, embed=False, **kwargs):
        super().__init__(embed=embed, **kwargs)
        if not embed:
            self.css = st.css(keep_menu=True)
        self.logo = True
        self.where = st if self.embed else st.sidebar

    def ask(self, region="BR", where=st.sidebar):
        self.where = where
        states = mundi.regions(region, type="state")
        highlight = self.where.selectbox(_("Select a state to highlight"), states.index)

        msg = _("Which kind of curve to you want to analyze?")
        which = self.where.selectbox(msg, ["cases", "deaths"])

        self.user_inputs = {
            "loc": highlight,
            "idx": int(which == "deaths"),
            "states": states,
            "which": which,
        }

    def show(self):
        curves = self.get_epidemic_curves(self.user_inputs['states'].index).fillna(0)

        # Acc cases
        ax = curves.iloc[-30:, self.user_inputs['idx']::2].plot(legend=False, grid=True)
        curves[self.user_inputs['loc'], self.user_inputs['which']].iloc[-30:].plot(ax=ax, legend=False, grid=True)
        st.pyplot()

        # # Daily cases
        # ax = curves.iloc[-30:, idx::2]
        # curves[self.user_inputs['loc'], self.user_inputs['which']].iloc[-30:].diff().plot(ax=ax, legend=False, grid=True)
        # st.pyplot()

        # # Growth factors
        # growths = get_growths(self.user_inputs['states'].index, self.user_inputs['which'])
        # ci = pd.DataFrame({"low": growths["value"] - growths["std"], "std": growths["std"]})

        # st.header("Growth factor +/- error")
        # ci.plot.bar(width=0.9, ylim=(0.8, 2), stacked=True, grid=True)
        # plt.plot(states.index, [1] * len(states), "k--")
        # st.pyplot()

        # # Duplication times
        # st.header("Duplication time")
        # (np.log(2) / np.log(growths["value"])).plot.bar(grid=True, ylim=(0, 30))
        # st.pyplot()

        # # R0
        # st.header("R0")
        # params = covid19.params(region=loc)
        # (
        #     np.log(growths["value"])
        #     .apply(lambda K: formulas.R0_from_K("SEAIR", params, K=K))
        #     .plot.bar(width=0.9, grid=True, ylim=(0, 4))
        # )
        # st.pyplot()

        # ms_good, ms_keep, ms_bad = run_models(states.index, which)

        # # ICU overflow
        # for ms, msg in [
        #     (ms_keep, "keep trends"),
        #     (ms_bad, "no distancing"),
        #     (ms_good, "more distancing"),
        # ]:
        #     st.header(f"Deaths and ICU overflow ({msg})")

        #     deaths = pd.DataFrame({m.region.id: m["deaths:dates"] for m in ms})
        #     deaths.plot(legend=False, color="0.5")
        #     deaths.sum(1).plot(grid=True)
        #     deaths[loc].plot(legend=True, grid=True)

        #     st.cards({"Total de mortes": fmt(deaths.iloc[-1].sum())})
        #     st.pyplot()

        #     data = {}
        #     for m in ms:
        #         overflow = m.results["dates.icu_overflow"]
        #         if overflow:
        #             data[m.region.id] = (overflow - pd.to_datetime(today())).days
        #     if data:
        #         data = pd.Series(data)
        #         data.plot.bar(width=0.9, grid=True)
        #         st.pyplot()

    @st.cache
    def get_epidemic_curves(self, refs: list):
        curves = []
        for ref in refs:
            curve = covid19.epidemic_curve(ref)
            curve.columns = pd.MultiIndex.from_tuples((ref, col) for col in curve.columns)
            curves.append(curve)

        return pd.concat(curves, axis=1).dropna()

    def main(self):
        self.run()

def main():
    projections_br = ProjectionsBR()
    projections_br.main()

if __name__ == '__main__':
    main()