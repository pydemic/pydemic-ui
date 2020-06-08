import io

import pandas as pd
import requests

from pydemic.cache import ttl_cache
from pydemic.utils import timed

# Originally at
# "https://docs.google.com/spreadsheets/d/1go3gYrgKsMmlGpHv9XGAACdk2T7XHSf7lOKDyfRfFak
# /export?format=xlsx"
PAHO_DATABASE_URL = "https://github.com/pydemic/databases/raw/master/paho_info.xlsx"


@timed
@ttl_cache("paho", timeout=6 * 3600)
def paho_br_dataframe(sheet) -> pd.DataFrame:
    content = paho_br_xlsx()
    fd = io.BytesIO(content)
    if sheet == "states":
        drop_columns = [
            "chave",
            "Região",
            "Estados",
            "codigo_UF",
            "data de referencia",
            "taxa positividade",
            "Link taxa de ocupação",
        ]
        rename_columns = {
            "sigla_UF": "id",
            "População": "population",
            "índice in loco": "isolation_score",
            "estado tem lockdown": "has_lockdown",
            "Municipios em lockdown": "n_cities_lockdown",
            "Total de municipios": "n_cities",
            "Taxa de ocupaçao clínicos": "hospital_occupancy",
            "Taxa ocupação UTI": "icu_occupancy",
            "Testes realizados": "tests",
            "Testes positivos": "tests_positive",
            "Casos novos ultimas 24 horas": "cases_24h",
            "Obitos ultimas 24 horas": "deaths_24h",
        }
        df = (
            pd.read_excel(fd, key="Estados", skipfooter=1)
            .drop(columns=drop_columns)
            .rename(columns=rename_columns)
            .astype({"id": "str"})
        )
        df.index = "BR-" + df.pop("id")

        # Replace "Not available" in occupancy columns
        for col in ("icu_occupancy", "hospital_occupancy"):
            series = df[col]
            if series.dtype != float:
                series = series.replace({"Not available": "nan", "": "nan"}).astype(float)
                df[col] = series
        return df
    else:
        raise ValueError


@timed
@ttl_cache("paho", timeout=6 * 3600)
def paho_br_xlsx() -> bytes:
    return requests.get(PAHO_DATABASE_URL).content
