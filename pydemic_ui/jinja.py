from gettext import gettext, ngettext
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markdown import markdown
from markupsafe import Markup

PATH = Path(__file__).parent

#
# Create default environment.
#
env = Environment(
    loader=FileSystemLoader(PATH / "templates"),
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=["jinja2.ext.i18n"],
)
env.install_gettext_callables(gettext, ngettext)
env.globals["markdown"] = markdown
env.filters["markdown"] = markdown


#
# Functions
#
def jinja_function(fn):
    """
    Register function in the global environment.
    """
    env.globals[fn.__name__] = fn
    return fn


@jinja_function
def render(template, *args, **kwargs):
    """
    Render object into template.
    """
    template = env.get_template(template + ".jinja2")
    if args:
        kwargs = {**args[0], **kwargs}
    return Markup(template.render(kwargs))
