from pydemic_ui.st_logger import StLogger
import streamlit
from pydemic_ui.html_report import HtmlReport
import pandas as pd
import numpy as np
import pdfkit

st = StLogger()
report = HtmlReport()

st.title("Hello World!")
st.text("This is a text!")
st.error("This is an error")
st.header("This is a header")
st.info("This is info")
st.subheader("This is a subheader")
st.button("This is a button")
df = pd.DataFrame(np.random.randn(10, 5), columns=("col %d" % i for i in range(5)))

st.table(df)
st.dataframe(df, 100, 250)

## line chart
chart_data = pd.DataFrame(
np.random.randn(30, 3),
columns=['a', 'b', 'c'])
st.line_chart(chart_data)

## area chart
chart_data = pd.DataFrame(
np.random.randn(40, 3),
columns=['a', 'b', 'c'])
st.area_chart(chart_data)

## bar chart
chart_data = pd.DataFrame(
np.random.randn(50, 3),
columns=['a', 'b', 'c'])
st.bar_chart(chart_data)

st(streamlit)

streamlit.header("Producing report...")
html = report.render(st)

pdfkit.from_string('<html><body>'+html+'</body></html>', 'out.pdf')

streamlit.text(html)
streamlit.subheader("This is a subheader")
