import inspect
import time
from typing import Any

import matplotlib.pyplot as plt

import mundi
from pydemic.models import SEAIR
from pydemic.utils import fmt
from pydemic_ui import st
from pydemic_ui.i18n import _, __
from pydemic_ui.app import SimpleApp, Timer

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


class ApiExplorer(SimpleApp):
    title = "Pydemic-UI API explorer"

    def __init__(self, embed=False, where=st, **kwargs):
        super().__init__(embed=embed, where=where, **kwargs)
        self.logo = True
        self.css = st.css(keep_menu=True) if not embed else False
        self.where = st if self.embed else st.sidebar

    def ask(self):
        """
        Ask for user input and save values as properties in the app.
        """
        self.where.header(("Options"))

        self.region = self.where.text_input(_("Mundi region code"), value="BR")
        try:
            self.region = mundi.region(self.region)
        except LookupError:
            self.where.error("Invalid mundi region code.")
            return

        options = {
            "model": _("A Pydemic Model"),
            "region": _("A Mundi Region"),
            "components": _("Input components"),
        }
        message = _("What do you want to explore?")
        option = self.where.radio(message, list(options), format_func=options.get)

        self.option = option
        self.object = self.handle_explore_option(option)

    def show(self):
        """
        Runs simulations and display outputs.
        """
        self.explore_object_attribute(self.option, self.object)

    def handle_explore_option(self, option):
        if option == "model":
            model = SEAIR(region=self.region, disease="covid-19")
            model.run(180)
            object = model.clinical.overflow_model()
        elif option == "region":
            object = self.region
        else:
            import pydemic_ui.components as object

        return object

    def explore_object_attribute(
        self, name, object, attributes=("ui", "plot", "pydemic", "input")
    ):
        """
        Instead of inspecting methods of object, query for the selected attribute
        from attributes and explore it.
        """

        message = _("Which aspect of the API do you want to explore?")
        attributes = filter(lambda x: hasattr(object, x), attributes)
        references = [f"{name}.{child}" for child in attributes]
        reference = self.where.selectbox(message, references)
        child = getattr(object, reference.partition(".")[-1])

        return self.explore_object(reference, child)

    def explore_object(self, name, obj):
        """
        Explore methods of object.
        """

        self.where = st.sidebar
        method = self.select_method(name, obj)
        args, kwargs = self.select_arguments(method)

        start = time.time()
        message = st.empty()
        result = method(*args, **kwargs)
        message.info(_("Method executed in {} seconds.").format(fmt(time.time() - start)))

        self.where.line()
        self.where.subheader(_("Method help and signature"))
        self.where.help(method)

        self.explore_function_output(result)

    def explore_function_output(self, result):
        if result is not None:
            self.where = st
            self.where.line()
            self.where.subheader(_("Function output"))

            if isinstance(result, plt.Axes):
                self.where.markdown(_("Function returned a matplotlib **ax** object. Showing it..."))
                self.where.pyplot(result.get_figure())
            else:
                self.where.write(result)

    def select_method(self, namespace: str, object: Any, blacklist=()):
        """
        Select a method from object.
        """

        methods = {}
        for method in dir(object):
            if method.startswith("_") or method in blacklist:
                continue
            try:
                value = getattr(object, method)
            except Exception:
                continue

            if callable(value):
                methods[method] = value

        format = lambda x: f"{namespace}.{x}( )"
        method = self.where.selectbox(_("Select method"), list(methods), format_func=format)
        return methods[method]

    def select_arguments(self, method):
        """
        Select arguments from a callable object.

        This method only works if we are able to introspect the object signature.
        """

        signature = inspect.Signature.from_callable(method)
        args = []
        kwargs = {}
        show_title = True

        for k, v in signature.parameters.items():
            if k == "where":
                continue
            if show_title:
                st.subheader(_("Arguments"))
                show_title = False
            if v.annotation == str:
                kwargs[k] = st.text_input(k)
            elif v.annotation == bool:
                kwargs[k] = st.checkbox(k)
            elif v.annotation == float:
                kwargs[k] = st.number_input(k)
            elif v.annotation == int:
                kwargs[k] = st.number_input(k)
            else:
                self.where.text(k)

        return args, kwargs


def main():
    api_explorer = ApiExplorer()
    api_explorer.main()


if __name__ == '__main__':
    main()
