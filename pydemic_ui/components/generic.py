import base64
import html as _html
import io
import os
from typing import Mapping, Optional, Any, Union

import pandas as pd
import streamlit as st

from pydemic.utils import file_type_display_name
from .base import twin_component
from .. import utils
from ..i18n import _, __

html_escape = _html.escape

# Friendly names to colors in the Streamlit palette
# See https://pmbaumgartner.github.io/streamlitopedia/essentials.html
COLOR_ALIASES = {
    # Main colors
    "st-primary": "#f63366",  # Primary pink/magenta used for widgets throughout the app
    "st-secondary": "#f0f2f6",  # Background color of Sidebar
    "st-black": "#262730",  # Font Color
    "st-light-yellow": "#fffd80",  # Right side of top header decoration in app
    "st-white": "#ffffff",  # Background
    # Secondary
    "st-red": "#ff2b2b",
    "st-yellow": "#faca2b",
    "st-blue": "#0068c9",
    "st-green": "#09ab3b",
    "st-gray-200": "#f0f2f6",
    "st-gray-600": "#a3a8b4",
    "st-gray-900": "#262730",
}

# MIME types
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
MIMETYPES_MAP = {
    "aac": "audio/aac",
    "abw": "application/x-abiword",
    "arc": "application/octet-stream",
    "avi": "video/x-msvideo",
    "azw": "application/vnd.amazon.ebook",
    "bin": "application/octet-stream",
    "bz": "application/x-bzip",
    "bz2": "application/x-bzip2",
    "csh": "application/x-csh",
    "css": "text/css",
    "csv": "text/csv",
    "doc": "application/msword",
    "eot": "application/vnd.ms-fontobject",
    "epub": "application/epub+zip",
    "gif": "image/gif",
    "htm": "text/html",
    "html": "text/html",
    "ico": "image/x-icon",
    "ics": "text/calendar",
    "jar": "application/java-archive",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "js": "application/javascript",
    "json": "application/json",
    "mid": "audio/midi",
    "midi": "audio/midi",
    "mpeg": "video/mpeg",
    "mpkg": "application/vnd.apple.installer+xml",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "odt": "application/vnd.oasis.opendocument.text",
    "oga": "audio/ogg",
    "ogv": "video/ogg",
    "ogx": "application/ogg",
    "otf": "font/otf",
    "png": "image/png",
    "pdf": "application/pdf",
    "ppt": "application/vnd.ms-powerpoint",
    "rar": "application/x-rar-compressed",
    "rtf": "application/rtf",
    "sh": "application/x-sh",
    "svg": "image/svg+xml",
    "swf": "application/x-shockwave-flash",
    "tar": "application/x-tar",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "ts": "application/typescript",
    "ttf": "font/ttf",
    "vsd": "application/vnd.visio",
    "wav": "audio/x-wav",
    "weba": "audio/webm",
    "webm": "video/webm",
    "webp": "image/webp",
    "woff": "font/woff",
    "woff2": "font/woff2",
    "xhtml": "application/xhtml+xml",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xml": "application/xml",
    "xul": "application/vnd.mozilla.xul+xml",
    "zip": "application/zip",
    "3gp": "audio/3gpp",
    "3g2": "video/3gpp2",
    "7z": "application/x-7z-compressed",
}


@twin_component()
def html(data: str, where=st):
    """
    Renders raw HTML string.

    Args:
        data:
            Input HTML string.
        where:
            Can be None, st or st.sidebar. If it is None, return the raw string.
    """
    if where is None:
        return data
    try:
        return where.write(data, unsafe_allow_html=True)
    except st.StreamlitAPIException:
        return where.markdown(data, unsafe_allow_html=True)


@twin_component()
def card(title: str, data: str, escape=True, color=None, where: Optional[Any] = st):
    """
    Render description list element representing a summary card with given
    title and datasets.
    """
    if escape:
        title = html_escape(title)
        data = html_escape(data)

    color = COLOR_ALIASES.get(color, color)
    style = "" if color is None else f'style="background: {color};"'
    data = f'<dl class="card-box" {style}><dt>{title}</dt><dd>{data}</dd></dl>'

    return html(data, where=where)


@twin_component()
def cards(entries: Mapping, escape=True, color=None, where=st):
    """
    Renders mapping as a list of cards.
    """
    entries = getattr(entries, "items", lambda: entries)()
    raw = "".join(card(k, v, escape, color, where=None) for k, v in entries)
    data = f"""<div class="card-boxes">{raw}</div>"""
    return html(data, where=where)


@twin_component()
def md_description(data: Mapping, where=st):
    """
    Renders a dictionary or sequence of tuples as a markdown string of associations.
    """
    data = getattr(data, "items", lambda: data)()
    md = "\n\n".join(f"**{k}**: {v}" for k, v in data)
    return where.markdown(md)


@twin_component()
def pause(where=st):
    """
    Space separator between commands.
    """
    where.markdown("` `")


@twin_component()
def line(where=st):
    """
    Line separator between commands.
    """
    where.markdown("---")


@twin_component()
def dataframe_download(
    df,
    name="data.{ext}",
    show_option=True,
    title=__("How do you want your data?"),
    where=st,
    **kwargs,
):
    """
    Create a download link to dataframe.
    """
    opts = {
        "show": _("Show in screen"),
        "csv": _("Comma separated values"),
        "xlsx": _("Excel"),
    }
    if not show_option:
        del opts["show"]

    opt = st.radio(str(title), list(opts), format_func=opts.get)

    if opt == "show":
        st.write(df.astype(object))
    else:
        name = name.format(ext=opt)
        data_anchor(df, name, where=where, **kwargs)


@twin_component()
def data_anchor(
    data,
    filename,
    label=None,
    style="display: block; text-align: right; margin-bottom: 2rem;",
    where=st,
    **kwargs,
):
    """
    Display a download link for the given data.

    Args:
        data:
            String, bytes or any object that can be converted to a dataframe using
            :func:`pydemic.utils.data_to_dataframe`
        filename:
            Name of downloaded file with extension. By default, file type is
            inferred from extension.
        label:
            Visible text inside the anchor element.

    Keyword Args:
        Additional keyword arguments are forwarded to the :func:`dataframe_uri`
        function.

    See Also:
        :func:`dataframe_uri`
        :func:`pydemic.utils.data_to_dataframe`
    """

    ext = os.path.splitext(filename)[1][1:]
    if label is None:
        label = _("Download as {kind}").format(kind=file_type_display_name(ext))

    kwargs.setdefault("ext", ext)
    if isinstance(data, (str, bytes)):
        href = data_uri(data, **kwargs)
    else:
        data = utils.data_to_dataframe(data)
        href = dataframe_uri(data, **kwargs)

    anchor = f'<a href="{href}" download="{filename}">{label}</a>'
    div = f'<div style="{style}">{anchor}</div>'
    html(div, where=where)


def dataframe_uri(df: pd.DataFrame, ext: str, mime_type=None, dates_format=None):
    """
    Returns only the href component of a data URI anchor that encodes a
    dataframe.
    """

    if dates_format:
        df.index = [d.strftime(dates_format) for d in df.index]

    if ext == "csv":
        fd = io.StringIO()
        df.to_csv(fd)
        data = fd.getvalue().encode("utf8")
    elif ext == "xlsx":
        fd = io.BytesIO()
        df.to_excel(fd)
        data = fd.getvalue()
    else:
        raise ValueError(f"invalid output type: {ext}")

    return data_uri(data, ext=ext, mime_type=mime_type)


def data_uri(data: Union[str, bytes], *, ext=None, mime_type=None) -> str:
    """
    Create a Base64 encoded data URI for the given raw data string and mime type
    or extension.

    Args:
        data:
            String or bytes with data content.
        mime_type:
            Data mime-type. If not given, it is inferred from extension.
        ext:
            Extension of data file. Used to infer MIME  type, if not given. The
            default mime_type for string content is "text/plain". If raw data is
            bytes, it assumes "application/octet-stream".

    Returns:
        A string with the contents that can be attached into the href attribute
        of an anchor element.
    """
    if isinstance(data, str):
        data = data.encode("utf8")
        ext = "txt" if ext is None else ext

    if mime_type is None:
        try:
            mime_type = MIMETYPES_MAP[ext]
        except KeyError:
            mime_type = "application/octet-stream"

    data = base64.b64encode(data).decode("utf8")
    return f"data:{mime_type};base64,{data}"


def render_svg(svg: str) -> str:
    """Renders the given svg string as an img tag."""

    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    return r'<img src="data:image/svg+xml;base64,%s"/>' % b64
