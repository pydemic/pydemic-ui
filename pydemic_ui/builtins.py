import builtins
import importlib
import io
import sys
from functools import wraps
from gettext import gettext as _
from pprint import pformat, pprint as _pprint, pp as _pp

import numpy as np
import pandas as pd
import sidekick as sk
import streamlit as st

_print = print
_input = input


@sk.fn
@wraps(_pprint)
def pprint(*args, **kwargs):
    out = pformat(*args, **kwargs)
    print(out)


@sk.fn
@wraps(_pp)
def pp(obj, **kwargs):
    out = io.StringIO()
    _pp(obj, stream=out, **kwargs)
    st.text(out.getvalue())


@sk.fn
@wraps(_print)
def print(*args, file=None, **kwargs):
    if file is None:
        out = io.StringIO()
        _print(*args, file=out, **kwargs)
        st.text(out.getvalue())
    else:
        _print(*args, file=file, **kwargs)


@wraps(_input)
def input(prompt="<- "):
    return st.text_input(prompt)


def require(mod):
    """
    Load a module, cleaning it first from sys.modules.
    """

    def loader():
        reload(mod)
        return sk.import_later(mod)

    return sk.deferred(loader)


def reload(mod):
    """
    Reload module and all sub-modules
    """
    prefix = mod + "."

    for k, mod in list(sys.modules.items()):
        if k == mod or k.startswith(prefix):
            importlib.reload(mod)


@sk.fn
def dbg(obj):
    st.warning(_("Debugging {obj} instance").format(obj=type(obj).__name__))

    if isinstance(obj, (pd.DataFrame, pd.Series, np.ndarray)):
        chart, table = opts = [_("Chart"), _("Table")]
        if st.radio(_("Debug"), opts, key=repr(obj)) == chart:
            st.line_chart(obj)
        else:
            st.write(obj)
    else:
        st.text(str(obj))
    return obj


def main():
    """
    Patch builtins.
    """

    import matplotlib.pyplot
    import numpy
    import pandas
    import sidekick
    import mundi

    builtins.st = require("pydemic_ui.st")
    builtins.sk = sidekick
    builtins.X = sidekick.X
    builtins.pd = pandas
    builtins.np = numpy
    builtins.mundi = mundi
    builtins.plt = matplotlib.pyplot
    builtins.print = print
    builtins.input = input
    builtins.pprint = pprint
    builtins.pp = pp
    builtins.require = require
    builtins.dbg = dbg
    builtins.reload = reload
