from pydemic.diseases import covid19
from pydemic.models import SEAIR
from pydemic_ui import st
from pydemic_ui.i18n import _


def main(embed=False):
    if not embed:
        st.css(keep_menu=True)
        st.sidebar.logo()

    models = ["crude", "delay", "overflow"]
    kind = st.sidebar.selectbox(_("Clinical model"), models)
    m = SEAIR(region="BR", disease=covid19)

    cm = m.clinical(kind)
    cm.ui.summary_table(subheader=_("Parameters table"))


if __name__ == "__main__":
    main()
