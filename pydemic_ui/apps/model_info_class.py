from pydemic_ui.app import SimpleApp, Timer
from pydemic.diseases import covid19
from pydemic.models import SEAIR
from pydemic_ui import st
from pydemic_ui.i18n import _

class ModelInfo(SimpleApp):
    title = "Model Info"

    def __init__(self, embed=False, where=st, **kwargs):
        super().__init__(embed=embed, where=where, **kwargs)
        if not embed:
            self.css = st.css(keep_menu=True)
        self.logo = True

    def ask(self):
        pass

    def show(self):
        pass
        
    def run(self):
        super().run()
        models = ["crude", "delay", "overflow"]
        kind = st.sidebar.selectbox(_("Clinical model"), models)
        m = SEAIR(region="BR", disease=covid19) 
        cm = m.clinical(kind)
        cm.ui.summary_table(subheader=_("Parameters table"))

def main():
    classe_model_info = ModelInfo()
    classe_model_info.main()

if __name__ == "__main__":
    main()
