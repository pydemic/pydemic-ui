from typing import Union

import sidekick as _sk
import streamlit as _st

from . import sidebar
from .. import components as _components

_self = _sk.import_later("pydemic_ui.st")

#
# Utilities
#
asset = _components.asset

#
# Generic
#
card = _components.card.bind(_st)
cards = _components.cards.bind(_st)
css = _components.css.bind(_st)
dataframe_download = _components.dataframe_download.bind(_st)
data_anchor = _components.data_anchor.bind(_st)
footnote_disclaimer = _components.footnote_disclaimer.bind(_st)
footnotes = _components.footnotes.bind(_st)
html = _components.html.bind(_st)
line = _components.line.bind(_st)
logo = _components.logo.bind(_st)
md_description = _components.md_description.bind(_st)
pause = _components.pause.bind(_st)

# Exclusive main component
pyramid_chart = _components.pyramid_chart.bind(_st)

#
# Inputs
#
epidemiological_params = _components.epidemiological_params.bind(_st)
healthcare_params = _components.healthcare_params.bind(_st)
intervention_runner_input = _components.intervention_runner_input.bind(_st)
region_input = _components.region_input.bind(_st)
simulation_params = _components.simulation_params.bind(_st)

#
# Explicit streamlit names to make static analysis happy
#
altair_chart = _st.altair_chart
area_chart = _st.area_chart
audio = _st.audio
balloons = _st.balloons
bar_chart = _st.bar_chart
beta_color_picker = _st.beta_color_picker
bokeh_chart = _st.bokeh_chart
button = _st.button
cache = _st.cache
caching = _st.caching
checkbox = _st.checkbox
code = _st.code
dataframe = _st.dataframe
date_input = _st.date_input
deck_gl_chart = _st.deck_gl_chart
echo = _st.echo
empty = _st.empty
error = _st.error
errors = _st.errors
exception = _st.exception
experimental_show = _st.experimental_show
file_uploader = _st.file_uploader
get_option = _st.get_option
graphviz_chart = _st.graphviz_chart
header = _st.header
help = _st.help
image = _st.image
info = _st.info
json = _st.json
latex = _st.latex
line_chart = _st.line_chart
map = _st.map
markdown = _st.markdown
multiselect = _st.multiselect
number_input = _st.number_input
plotly_chart = _st.plotly_chart
progress = _st.progress
proto = _st.proto
pydeck_chart = _st.pydeck_chart
pyplot = _st.pyplot
radio = _st.radio
selectbox = _st.selectbox
set_option = _st.set_option
slider = _st.slider
spinner = _st.spinner
subheader = _st.subheader
subprocess = _st.subprocess
success = _st.success
text = _st.text
text_area = _st.text_area
text_input = _st.text_input
time_input = _st.time_input
title = _st.title
util = _st.util
vega_lite_chart = _st.vega_lite_chart
video = _st.video
warning = _st.warning
write = _st.write

#
# Overridden streamlit functions
#
streamlit_table = _st.table


def table(data, link: Union[bool, str] = False, *, label: str = None, where=_self):
    """
    Display a static table.

    This differs from `st.dataframe` in that the table in this case is
    static: its entire contents are just laid out directly on the page.

    This extends the default "st.table" function to include the possibility of
    displaying a download link.

    Args:
        data (pandas.DataFrame, pandas.Styler, numpy.ndarray, Iterable, dict, or None)
            The table data.
        link (bool, str):
            If True or a file name with a compatible extension such as csv, xls,
            etc, it includes a download  link bellow data. The default file
            format is csv.
        label (str):
            Override the default label in the anchor element.

    Example
    -------
    >>> df = pd.DataFrame(
    ...    np.random.randn(10, 5),
    ...    columns=('col %d' % i for i in range(5)))
    ...
    >>> st.table(df, 'data.csv')

    .. output::
       https://share.streamlit.io/0.25.0-2JkNY/index.html?id=KfZvDMprL4JFKXbpjD3fpq
       height: 480px

    """
    try:
        fn = where.streamlit_table
    except AttributeError:
        fn = where.table
        if fn is table:
            fn = _st.table  # avoid infinite recursion
    fn(data)
    if link is True:
        link = "data.csv"
    if link:
        data_anchor(data, link, label=label, where=where)


def __getattr__(name):
    return getattr(_st, name)
