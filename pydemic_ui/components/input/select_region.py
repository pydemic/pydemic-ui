__package__ = "pydemic_ui.components.input"

import re
from functools import lru_cache

import streamlit as st

import mundi
from mundi import Region
from ..base import twin_component
from ...i18n import _, __

COUNTRIES = {"BR": __("Brazil")}
TEMPLATE_START = [(__("Region"), "region", "macro-region"), (__("State"), "state", None)]
TEMPLATE_IBGE = [
    (__("Meso Region"), "region", "meso-region"),
    (__("Micro-Region"), "region", "micro-region"),
    (__("City"), "city", None),
]
TEMPLATE_SUS = [(__("SUS macro region"), "region", "healthcare region")]


@twin_component()
def select_region(code, *, where=st, **kwargs) -> Region:
    """
    Select region or sub-region based on mundi code.
    """
    kwargs["where"] = where
    region = mundi.region(code)

    if region.id == "BR":
        return select_br_region(**kwargs)
    elif len(code) == 2:
        title = kwargs.pop("title", _("Location"))
        if title:
            where.header(title)
        return select_from_sub_regions(region, _("Location"), where=where)
    else:
        raise NotImplementedError(f"Cannot select {code!r}")


def select_from_sub_regions(code, label, where=st, fastrack=False, **kwargs) -> Region:
    """
    Select a region between a list that starts with the parent region and its
    children.
    """
    region = mundi.region(code)
    regions = sub_regions(region.id, **kwargs)
    if len(regions) == 1 and fastrack:
        return regions[0]
    regions = ("*" + region.id, *regions)
    return mundi.region(
        where.selectbox(str(label), regions, format_func=region_name).lstrip("*")
    )


def select_from_template(code, template, title=__("Location"), where=st) -> Region:
    """
    Select a Brazilian region from country up to municipality.
    """
    if title:
        where.header(str(title))

    code = mundi.region(code)
    for label, type_, subtype in template:
        kwargs = {"type": type_}
        if subtype:
            kwargs["subtype"] = subtype
        new_code = select_from_sub_regions(code, label, where=where, **kwargs)
        if new_code == code:
            return mundi.region(code)
        code = new_code
    return mundi.region(code)


#
# Country-specific selectors.
#
def select_br_region(
    title=__("Location"), where=st, hide_cities=False, healthcare_regions=False
) -> Region:
    """
    Select a Brazilian region from country up to municipality.
    """

    # Select macro-region or the whole country
    region = select_from_template("BR", TEMPLATE_START, title=title, where=where)

    if re.fullmatch(r"[A-Z]{2}(-[0-9])?", region.id):
        return region

    # Choose between IBGE hierarchy and SUS
    if healthcare_regions:
        fmt = {"ibge": _("IBGE subdivisions"), "sus": _("SUS healthcare region")}
        kind = where.radio(_("Select"), ["ibge", "sus"], format_func=fmt.get)
    else:
        kind = "ibge"

    # Continue selection
    template = TEMPLATE_IBGE if kind == "ibge" else TEMPLATE_SUS
    region = select_from_template(region, template, title=None, where=where)

    if not hide_cities and kind == "sus" and "SUS:" in region.id:
        if where.checkbox(_("Show cities")):
            lines = [
                _("List of cities"),
                "",
                *(f"* {child.name}" for child in children(region)),
            ]
            where.markdown("\n".join(lines))
    return region


#
# Caches
#
@lru_cache(65_536)
def region_name(code):
    """Region name from Mundi code."""

    if code.startswith("*"):
        return _("{name} (everything)").format(name=region_name(code[1:]))

    reg = mundi.region(code)
    return _(reg["name"])


@lru_cache(2048)
def sub_regions(code, **kwargs):
    """
    Return a list of mundi codes starting with the given code, followed by all
    sub-regions queried from the given arguments.
    """
    if len(code) == 2:
        kwargs["country_code"] = code
    else:
        kwargs["parent_id"] = code

    sub_df = mundi.regions(**kwargs)
    return tuple(sub_df.index)


@lru_cache(2048)
def children(region, which="both"):
    """
    Return a list of children for the given code.
    """
    return region.children(which=which)


if __name__ == "__main__":
    r1 = select_region("BR", healthcare_regions=st.checkbox("SUS?"))
    st.write(select_region("RU", where=st.sidebar))
    st.write(r1.to_series("name", "type", "subtype", "population"))
