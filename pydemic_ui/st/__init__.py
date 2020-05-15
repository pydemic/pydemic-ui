import streamlit as _st

from . import sidebar
from .. import components as _components

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
select_intervention = _components.select_intervention.bind(_st)
select_region = _components.select_region.bind(_st)
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
table = _st.table
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


def __getattr__(name):
    return getattr(_st, name)
