from pydemic_ui.i18n import _


class DebugCalc:
    def __init__(self, st, DEBUG):
        self.st = st
        self.DEBUG = DEBUG
        self.mode()

    def mode():
        self.debug = False
        if DEBUG and self.st.checkbox(_("Enable debug")):
            self.running_message()
            self.debug = True

    def running_message(self):
        self.st.info(_("Running in debug mode!"))
        self.st.html(
            """
        <ul>
            <li><a href="#debug">{}</a></li>
        </ul>""".format(
                _("Debug section!")
            )
        )

    def information_message(
        self, results, params, epidemiology, clinical, model, clinical_model
    ):
        if results:
            self.st.html('<div style="height: 15rem"></div>')
        self.st.html('<h2 id="debug">{}</h2>'.format(_("Debug information")))

        self.st.subheader(_("Generic parameters"))
        self.st.write(params)

        self.st.subheader(_("Epidemiological parameters"))
        self.st.write(epidemiology)

        self.st.subheader(_("Clinical parameters"))
        self.st.write(clinical)

        self.st.subheader(_("Output"))
        self.st.write(results)

        if model:
            self.st.line_chart(model.data)

        if clinical_model:
            self.st.line_chart(clinical_model[["infectious", "severe", "critical"]])

            self.st.subheader(_("Distribution of deaths"))
            df = clinical_model[DEATH_DISTRIBUTION_COLUMNS]
            df.columns = [DEATH_DISTRIBUTION_COL_NAMES[k] for k in df.columns]
            self.st.area_chart(df)
