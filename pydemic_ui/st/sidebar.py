import streamlit as _st

from .. import components as _components

#
# Utilities
#
asset = _components.asset

#
# Generic
#
card = _components.card.bind(_st.sidebar)
cards = _components.cards.bind(_st.sidebar)
css = _components.css.bind(_st.sidebar)
footnote_disclaimer = _components.footnote_disclaimer.bind(_st.sidebar)
footnotes = _components.footnotes.bind(_st.sidebar)
html = _components.html.bind(_st.sidebar)
line = _components.line.bind(_st.sidebar)
logo = _components.logo.bind(_st.sidebar)
md_description = _components.md_description.bind(_st.sidebar)
pause = _components.pause.bind(_st.sidebar)

#
# Inputs
#
epidemiological_params = _components.epidemiological_params.bind(_st.sidebar)
healthcare_params = _components.healthcare_params.bind(_st.sidebar)
select_intervention = _components.select_intervention.bind(_st.sidebar)
select_region = _components.select_region.bind(_st.sidebar)
simulation_params = _components.simulation_params.bind(_st.sidebar)

#
# Explicit streamlit names to make static analysis happy
#
add_rows = _st.sidebar.add_rows
altair_chart = _st.sidebar.altair_chart
area_chart = _st.sidebar.area_chart
audio = _st.sidebar.audio
balloons = _st.sidebar.balloons
bar_chart = _st.sidebar.bar_chart
beta_color_picker = _st.sidebar.beta_color_picker
bokeh_chart = _st.sidebar.bokeh_chart
button = _st.sidebar.button
checkbox = _st.sidebar.checkbox
code = _st.sidebar.code
dataframe = _st.sidebar.dataframe
date_input = _st.sidebar.date_input
deck_gl_chart = _st.sidebar.deck_gl_chart
empty = _st.sidebar.empty
error = _st.sidebar.error
exception = _st.sidebar.exception
file_uploader = _st.sidebar.file_uploader
graphviz_chart = _st.sidebar.graphviz_chart
header = _st.sidebar.header
help = _st.sidebar.help
image = _st.sidebar.image
info = _st.sidebar.info
json = _st.sidebar.json
latex = _st.sidebar.latex
line_chart = _st.sidebar.line_chart
map = _st.sidebar.map
markdown = _st.sidebar.markdown
multiselect = _st.sidebar.multiselect
number_input = _st.sidebar.number_input
plotly_chart = _st.sidebar.plotly_chart
progress = _st.sidebar.progress
pydeck_chart = _st.sidebar.pydeck_chart
pyplot = _st.sidebar.pyplot
radio = _st.sidebar.radio
selectbox = _st.sidebar.selectbox
slider = _st.sidebar.slider
subheader = _st.sidebar.subheader
success = _st.sidebar.success
table = _st.sidebar.table
text = _st.sidebar.text
text_area = _st.sidebar.text_area
text_input = _st.sidebar.text_input
time_input = _st.sidebar.time_input
title = _st.sidebar.title
vega_lite_chart = _st.sidebar.vega_lite_chart
video = _st.sidebar.video
warning = _st.sidebar.warning


def __getattr__(name):
    return getattr(_st.sidebar, name)
