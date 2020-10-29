from pydemic_ui.st_logger import StLogger
import streamlit
from pydemic_ui.html_report import HtmlReport


st = StLogger()
report = HtmlReport()

st.title("Hello World!")
st.text("This is a text!")
st.error('This is an error')
st.header('This is a header')
st.info('This is info')
st.subheader('This is a subheader')

st(streamlit)

streamlit.header('Producing report...')
html = report.render(st)
streamlit.text(html)
streamlit.subheader('This is a subheader')