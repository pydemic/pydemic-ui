__package__ = "pydemic_ui.components"

import html as _html
from typing import Mapping, Optional, Any

import streamlit as st

from .base import twin_component

html_escape = _html.escape

# Friently names to colors in the Streamlit palette
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


if __name__ == "__main__":
    from ..ui import css

    css()
    st.header("Components")

    st.subheader("html()")
    html("<div><pre>Raw HTML</pre></div>")

    st.subheader("card()")
    card("Card", "Card data")
    card("Colored Card", "Card data", color="blue")

    st.subheader("cards()")
    cards({"Card 1": "Card 1 data", "Card 2": "Card 2 data"}, color="red")

    st.subheader("md_description()")
    md_description(
        {"Entry 1": "Description for entry 1", "Entry 2": "Description for entry 2"}
    )
