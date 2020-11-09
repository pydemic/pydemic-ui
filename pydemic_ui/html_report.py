from typing import Iterable
from html import escape
from .st_logger import StLogger
import pandas as pd


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
        return '\n'.join(self.render_lines(logger))

    def render_lines(self, logger: StLogger) -> Iterable[str]:
        """
        Renders HTML as an iterator of lines.
        """
        for step in logger:
            try:
                handler = getattr(self, f'handle_{step.name}')
            except AttributeError:
                raise ValueError(f'handler "{step.name}" does not exist or is not supported')
            else:
                result = handler(*step.args, **step.kwargs)
                if isinstance(result, str):
                    yield result
                else:
                    yield from result

    def handle_title(self, body):
        return f'<h1 class="title">{escape(body)}</h1>'

    def handle_text(self, body):
        return f'<pre>{escape(body)}</pre>'

    def handle_error(self, body):
        return f'<p class="error">{escape(body)}</p>'

    def handle_header(self, body):
        return f'<h2>{escape(body)}</h2>'

    def handle_info(self , body):
        return f'<p class="alert">{escape(body)}</p>'

    def handle_subheader(self, body):
        return f'<h3>{escape(body)}</h3>'

    def handle_table(self, data):
        return data.to_html()

    def handle_dataframe(self, data, width=None, height=None):
        html = data.to_html()
        if width:
            html = html.replace('<table', f'<table style="max-width: {width}px"')

        if height:
            html = html.replace('<table', f'<table style="max-height: {height}px"')

        return html
