from pydemic_ui.st_logger import StLogger
import streamlit
from pydemic_ui.html_report import HtmlReport
import pandas as pd
import numpy as np


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

st(streamlit)

streamlit.header("Producing report...")
html = report.render(st)
streamlit.text(html)
streamlit.subheader("This is a subheader")
