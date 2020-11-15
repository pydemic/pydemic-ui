from typing import Iterable
from html import escape
from .st_logger import StLogger
import pandas as pd
import plotly.express as px

class HtmlReport:
    """
    Render HTML reports from logged sequences of Streamlit commands.
    """

    logger: StLogger

    def __init__(self, ignore_input=False):
        self._ignore_input = ignore_input

    def render(self, logger: StLogger):
        """
        Render HTML report to string.
        """
        return "\n".join(self.render_lines(logger))

    def render_lines(self, logger: StLogger) -> Iterable[str]:
        """
        Renders HTML as an iterator of lines.
        """
        for step in logger:
            try:
                handler = getattr(self, f"handle_{step.name}")
            except AttributeError:
                raise ValueError(
                    f'handler "{step.name}" does not exist or is not supported'
                )
            else:
                result = handler(*step.args, **step.kwargs)
                if isinstance(result, str):
                    yield result
                else:
                    yield from result

    def handle_title(self, body):
        return f'<h1 class="title">{escape(body)}</h1>'

    def handle_text(self, body):
        return f"<pre>{escape(body)}</pre>"

    def handle_error(self, body):
        return f'<p class="error">{escape(body)}</p>'

    def handle_header(self, body):
        return f"<h2>{escape(body)}</h2>"

    def handle_info(self, body):
        return f'<p class="alert">{escape(body)}</p>'

    def handle_subheader(self, body):
        return f"<h3>{escape(body)}</h3>"

    def handle_table(self, data):
        return data.to_html()

    def handle_dataframe(self, data, width=None, height=None):
        html = data.to_html()
        if width:
            html = html.replace("<table", f'<table style="max-width: {width}px"')

        if height:
            html = html.replace("<table", f'<table style="max-height: {height}px"')

        return html

    def handle_line_chart(self, data):
        fig = px.line(data)
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return html+'\n'

    def handle_area_chart(self, data):
        fig = px.area(data)
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return html+'\n'
    
    def handle_bar_chart(self, data):
        fig = px.bar(data)
        html = fig.to_html(full_html=False, include_plotlyjs='cdn')
        return html+'\n'
        
    def handle_button(self, text):
        return f'<button data-baseweb="button" class="st-en st-eo st-c9 st-ep st-eq st-er st-es st-et st-cn st-co st-cp st-cq st-cr st-eu st-ax st-ev st-ew st-ex st-b0 st-ey st-de st-ez st-f0 st-f1 st-f2 st-d0 st-aq st-cs st-ar st-ae st-af st-ag st-ah st-au st-av st-at st-aw st-f3 st-f4 st-f5 st-f6 st-c1 st-ec st-f7 st-f8 st-f9 st-fa st-fb st-fc st-fd st-fe st-ff st-fg st-eg st-fh st-fi st-fj">{escape(text)}</button>'
