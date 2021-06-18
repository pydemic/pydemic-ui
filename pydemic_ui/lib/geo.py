from functools import lru_cache
from pathlib import Path

import geopandas

import mundi
from pydemic.cache import disk_cache
from pydemic.utils import timed

PATH = Path(__file__).parent.parent


@timed
def brazil_map() -> geopandas.GeoDataFrame:
    """
    Load shape files and return a GeoDataFrame with the Brazilian map.
    """
    return _brazil_map().copy()


@lru_cache(1)
@disk_cache("shapefiles")
def _brazil_map():
    num_codes = (
        mundi.regions_dataframe("BR", type="state")
        .mundi["numeric_code"]
        .astype(object)["numeric_code"]
        .to_dict()
    )
    translate = {v: k for k, v in num_codes.items()}
    geo = geopandas.read_file(PATH / "databases/maps/br/estados.dbf")[
        ["CD_GEOCUF", "geometry"]
    ]
    geo.index = geo.pop("CD_GEOCUF").apply(translate.__getitem__)
    geo["geometry"] = geo.simplify(0.1)
    return geo
