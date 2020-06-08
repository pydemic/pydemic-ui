import io
import pathlib
from typing import BinaryIO

from weasyprint import HTML

from . import jinja

PATH = pathlib.Path(__file__).parent
ASSETS = PATH / "assets"


def pdf_from_html(data, to=None) -> BinaryIO:
    """
    Render a PDF file from an HTML string.
        data:
            Raw HTML string.
        to:
            Destination file. If not given, return a BytesIO object with the
            PDF contents.

    Returns:
        A file descriptor object with the resulting pdf data.
    """

    fd = to or io.BytesIO()
    report = HTML(string=data)
    report.write_pdf(fd, stylesheets=[ASSETS / "report.css"])

    if isinstance(fd, str):
        return open(fd, "rb")
    return io.BytesIO(fd.getvalue())


def pdf_from_template(template, ctx, to=None) -> BinaryIO:
    """
    Render a PDF from an HTML template file in the given context.

    Args:
        template:
            Name of template file.
        ctx:
            A context dictionary with replacement variable values.
        to:
            Destination file. If not given, return a BytesIO object with the
            PDF contents.

    Returns:
        A file descriptor object with the resulting pdf data.
    """
    template = jinja.env.get_template(template + ".jinja2")
    html = template.render(ctx)
    return pdf_from_html(html, to=to)
