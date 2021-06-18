import re
from functools import lru_cache

import streamlit as st

import mundi
from mundi import Region
from pydemic.region.multi_region import CompositeRegion
from ..base import twin_component
from ...decorators import title
from ...i18n import _, __

COMMA = re.compile(r"\s*[,;\s]\s*")
COUNTRIES = {"BR": __("Brazil")}
TEMPLATE_BR_START = [
    (__("Region"), "region", "macro-region"),
    (__("State"), "state", None),
]
TEMPLATE_BR_IBGE = [
    (__("Meso Region"), "region", "meso-region"),
    (__("Micro-Region"), "region", "micro-region"),
    (__("City"), "city", None),
]
TEMPLATE_BR_SUS = [(__("SUS macro region"), "region", "healthcare region")]


@twin_component()
@title(__("Location"))
def region_input(
    default: str, *, advanced=False, text=False, where=st, **kwargs
) -> Region:
    """
    Select region or sub-region based on mundi code.
    """
    st = where
    kwargs["where"] = where
    default = mundi.code(default)
    if text or advanced and st.checkbox(_("Advanced selection"), value=False):
        try:
            code = st.text_input(_("Select mundi region"), value=default)
            return mundi.region(code)
        except LookupError:
            st.error(_("Region not found!"))
            return mundi.region(default)
    region = mundi.region(default)

    if region.id == "BR":
        return _br_region_input(**kwargs)
    elif len(default) == 2:
        return _from_sub_regions(region, _("Location"), where=where)
    else:
        raise NotImplementedError(f"Cannot select {default!r}")


def _from_sub_regions(code, label, fastrack=False, where=st, **kwargs) -> Region:
    """
    Select a region from a list that starts with the parent region and its
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


def _from_template(code, template, where=st) -> Region:
    """
    Select a Brazilian region from country up to municipality.
    """
    code = mundi.region(code)
    for label, type_, subtype in template:
        kwargs = {"type": type_}
        if subtype:
            kwargs["subtype"] = subtype
        new_code = _from_sub_regions(code, label, where=where, **kwargs)
        if new_code == code:
            return mundi.region(code)
        code = new_code
    return mundi.region(code)


#
# Country-specific selectors.
#
def _br_region_input(
    hide_cities=False, sus_regions=False, arbitrary=False, where=st
) -> Region:
    """
    Select a Brazilian region from country up to municipality.
    """

    # Select macro-region or the whole country
    region = _from_template("BR", TEMPLATE_BR_START, where=where)

    if re.fullmatch(r"[A-Z]{2}(-[0-9])?", region.id):
        return region

    # Choose between IBGE hierarchy and SUS
    choices = {"ibge": _("IBGE subdivisions")}
    if sus_regions:
        choices.update(sus=_("SUS healthcare region"))
    if arbitrary:
        choices.update(arbitrary=_("List of IBGE city codes"))

    if choices:
        kind = where.radio(_("Select"), [*choices], format_func=choices.get)
    else:
        kind = "ibge"

    # Continue selection
    if kind == "arbitrary":
        codes = where.text_area(_("List of IBGE city codes"))
        codes = set(COMMA.split(codes))
        codes.discard("")
        if not codes:
            return region
        return _from_ibge_city_codes(codes, region, where=where)
    else:
        template = TEMPLATE_BR_IBGE if kind == "ibge" else TEMPLATE_BR_SUS
        region = _from_template(region, template, where=where)

    if not hide_cities and kind == "sus" and "SUS:" in region.id:
        if where.checkbox(_("Show cities")):
            lines = [
                _("List of cities"),
                "",
                *(f"* {child.name}" for child in children(region)),
            ]
            where.markdown("\n".join(lines))
    return region


def _from_ibge_city_codes(codes, parent, where=st):
    state_code = parent.numeric_code
    cities = tuple(map(ibge_city, codes))
    for city in cities:
        if city.type == "city" and city.numeric_code[:2] != state_code:
            msg = _("{city} is not in {state}!").format(city=city.name, state=parent.name)
            where.warning(msg)
    return CompositeRegion(cities, name=_("Arbitrary region"))


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

    sub_df = mundi.regions_dataframe(**kwargs)
    return tuple(sub_df.index)


@lru_cache(2048)
def children(region, which="both"):
    """
    Return a list of children for the given code.
    """
    return region.children(which=which)


@lru_cache(2048)
def ibge_city(code):
    if code.isdigit():
        if len(code) == 7:
            code = code[:-1]
        elif len(code) != 6:
            raise ValueError(_("invalid city code: {code}").format(code=code))
        return mundi.region(country_code="BR", type="city", short_code=code)
    return mundi.region(code)
