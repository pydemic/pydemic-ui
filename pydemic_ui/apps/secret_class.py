from pydemic_ui.apps.calc_class import Calc
import datetime


class Secret:
    self.date = datetime.date(1904, 11, 10)

    def area(self):
        self.where = globals()["st"]
        self.where.title(_("Secret area for beta testers"))
        self.easter_egg()

    def is_easter_egg_activated(params):
        return params is None

    def easter_egg(disease=covid19):
        apps = {
            "api_explorer": _("Showcase Pydemic-UI components"),
            "scenarios1": _("Forecast for BR states in different scenarios (model 1)"),
            "scenarios2": _("Forecast for BR states in different scenarios (model 2)"),
            "projections": _("Epidemic forecasts"),
            "dashboard_br": _("Dashboard with epidemic information (Brazil)"),
        }
        msg = _("Select the secret application")
        app = st.selectbox(msg, list(apps.keys()), format_func=apps.get)

        mod = importlib.import_module(f"pydemic_ui.apps.{app}")
        mod.main(embed=True, disease=disease)
