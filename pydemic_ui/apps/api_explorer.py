import inspect
import time
from typing import Any

import matplotlib.pyplot as plt

import mundi
from pydemic.models import SEAIR
from pydemic.utils import fmt
from pydemic_ui import st
from pydemic_ui.i18n import _, __

REGION_MESSAGE = __(
    """
Region UI components can be accessed from the region.ui attribute of Mundi
regions. They display information about some region, which is **not** tied to
any  simulation.

The currently selected Mundi region is **{region.id}**. Change your selection
in the  sidebar to see how each component would be displayed for different
regions.
"""
)


def select_method(namespace: str, obj: Any, blacklist=(), where=st):
    """
    Select a method from object.
    """

    methods = {}
    for k in dir(obj):
        if k.startswith("_") or k in blacklist:
            continue
        try:
            value = getattr(obj, k)
        except Exception:
            continue

        if callable(value):
            methods[k] = value

    fmt = lambda x: f"{namespace}.{x}( )"
    method = where.selectbox(_("Select method"), list(methods), format_func=fmt)
    return methods[method]


def select_arguments(fn, where=st):
    """
    Select arguments from a callable object.

    This method only works if we are able to introspect the object signature.
    """

    st = where
    sig = inspect.Signature.from_callable(fn)
    args = []
    kwargs = {}
    show_title = True

    for k, v in sig.parameters.items():
        if k == "where":
            continue
        if show_title:
            st.subheader(_("Arguments"))
            show_title = False
        st.text(k)

    return args, kwargs


def explore_object(name, obj, where=st):
    """
    Explore methods of object.
    """

    fn = select_method(name, obj, where=where)
    args, kwargs = select_arguments(fn, where=where)

    t0 = time.time()
    msg = st.empty()
    result = fn(*args, **kwargs)
    msg.info(_("Method executed in {} seconds.").format(fmt(time.time() - t0)))

    st.line()
    st.subheader(_("Method help and signature"))
    st.help(fn)

    if result is not None:
        st.line()
        st.subheader(_("Function output"))

        if isinstance(result, plt.Axes):
            st.markdown(_("Function returned a matplotlib **ax** object. Showing it..."))
            st.pyplot(result.get_figure())
        else:
            st.write(result)


def explore_object_attribute(name, obj, attrs=("ui", "plot", "pydemic"), where=st):
    """
    Instead of inspecting methods of object, query for the selected attribute
    from attrs and explore it.
    """

    msg = _("Which aspect of the API do you want to explore?")
    attrs = filter(lambda x: hasattr(obj, x), attrs)
    refs = [f"{name}.{child}" for child in attrs]
    ref = where.selectbox(msg, refs)
    child = getattr(obj, ref.partition(".")[-1])

    return explore_object(ref, child, where=where)


def main(embed=False, disease=None):
    """
    Main interface of the API explorer.
    """
    if not embed:
        st.css(keep_menu=True)
        st.sidebar.logo()
    where = st if embed else st.sidebar

    st.title(_("Pydemic-UI API explorer"))
    where.header(_("Options"))

    region = where.text_input(_("Mundi region code"), value="BR")
    try:
        region = mundi.region(region)
    except LookupError:
        where.error("Invalid mundi region code.")
        return

    opts = {"model": _("A Pydemic Model"), "region": _("A Mundi Region")}
    msg = _("What do you want to explore?")
    opt = where.radio(msg, list(opts), format_func=opts.get)

    if opt == "model":
        model = SEAIR(region=region, disease="covid-19")
        model.run(180)
        obj = model.clinical.overflow_model()
    else:
        obj = region

    explore_object_attribute(opt, obj, where=where)


if __name__ == "__main__":
    main()
