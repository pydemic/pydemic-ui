__package__ = "pydemic_ui.components"

from typing import Mapping

import streamlit as st

from .base import twin_component


@twin_component()
def html(data: str, where=None):
    """
    Renders raw HTML string.

    Args:
        data:
            Input HTML string.
        where:
            Can be None, st or st.sidebar. If it is None, return the raw string.
    """
    try:
        return where.write(data, unsafe_allow_html=True)
    except st.StreamlitAPIException:
        return where.markdown(data, unsafe_allow_html=True)


@twin_component()
def card(title: str, data: str, where=None):
    """
    Render description list element representing a summary card with given
    title and datasets.
    """
    data = f'<dl class="card-box"><dt>{title}</dt><dd>{data}</dd></dl>'
    return html(data, where=where)


@twin_component()
def cards(entries: Mapping, where=None):
    """
    Renders mapping as a list of cards.
    """
    entries = getattr(entries, "items", lambda: entries)()
    raw = "".join(card(k, v, where=None) for k, v in entries)
    data = f"""<div class="card-boxes">{raw}</div>"""
    return html(data, where=where)


@twin_component()
def md_description(data: Mapping, where=None):
    """
    Renders a dictionary or sequence of tuples as a markdown string of associations.
    """
    data = getattr(data, "items", lambda: data)()
    md = "\n\n".join(f"**{k}**: {v}" for k, v in data)
    return where.markdown(md)


@twin_component()
def pause(where=None):
    """
    Space separator between commands.
    """
    where.markdown("` `")


@twin_component()
def line(where=None):
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

    st.subheader("cards()")
    cards({
        "Card 1": "Card 1 data",
        "Card 2": "Card 2 data",
    })

    st.subheader("md_description()")
    md_description({
        "Entry 1": "Description for entry 1",
        "Entry 2": "Description for entry 2",
    })
