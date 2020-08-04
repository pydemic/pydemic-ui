import io
from enum import Enum, IntFlag
from types import MappingProxyType
from typing import Sequence

import matplotlib.pyplot as plt
import pandas as pd
import requests

import mundi
import sidekick as sk
from mundi import Region
from pydemic.cache import ttl_cache
from pydemic.logging import log
from pydemic.region import RegionT
from pydemic.utils import today, trim_zeros
from pydemic_ui import st
from pydemic_ui.i18n import _


class Symptom(IntFlag):
    NA = 0
    OTHER = 1
    COUGH = 2
    FEVER = 4
    DYSPNOEA = 8
    SORE_THROAT = 16


def to_symptom(
    x,
    _opts=MappingProxyType(
        {
            "outros": Symptom.OTHER,
            "dispneia": Symptom.DYSPNOEA,
            "tosse": Symptom.COUGH,
            "febre": Symptom.FEVER,
            "dor de garganta": Symptom.SORE_THROAT,
            "dificuldade de respirar": Symptom.DYSPNOEA,
        }
    ),
):
    if pd.isna(x) or x in ("null", "undefined", ""):
        return Symptom.NA

    value = Symptom.NA
    opts = x.lower().split(",")
    while opts:
        opt = opts.pop().strip()
        if opt:
            try:
                value |= _opts[opt]
            except KeyError:
                # Maybe it missed the comma
                for prefix in _opts:
                    if opt.startswith(prefix):
                        value |= _opts[prefix]
                        opts.append(opt[len(prefix) :])
                        break
                else:
                    raise
    return value


class Test(Enum):
    COLLECTED = "collected"
    REQUESTED = "requested"
    FINISHED = "finished"


class TestType(Enum):
    FAST_IGG = "collected"
    FAST_ANTI = "requested"
    RT_PCR = "rt-pcr"


class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class Evolution(Enum):
    CURED = "cured"
    CANCELLED = "cancelled"
    DEATH = "death"
    ICU = "icu"
    TREATING = "treating"
    HOME_CARE = "home_care"
    IGNORED = "ignored"


class Status(Enum):
    DISCARDED = "discarded"
    CONFIRMED = "confirmed"
    CONFIRMED_TEST = "confirmed_test"


EVOLUTION = {
    "Cura": Evolution.CURED,
    "Cancelado": Evolution.CANCELLED,
    "Óbito": Evolution.DEATH,
    "Em tratamento": Evolution.TREATING,
    "Em tratamento domiciliar": Evolution.TREATING,
    "Internado em UTI": Evolution.ICU,
    "Internado": Evolution.TREATING,
    "Ignorado": Evolution.IGNORED,
}

TEST = {
    "null": pd.NA,
    "undefined": pd.NA,
    "Coletado": Test.COLLECTED,
    "Solicitado": Test.REQUESTED,
    "Concluído": Test.FINISHED,
}
STATUS = {
    "Confirmado Clínico-Epidemiológico": Status.CONFIRMED,
    "Confirmado Laboratorial": Status.CONFIRMED_TEST,
    "Confirmação Laboratorial": Status.CONFIRMED_TEST,
    "Descartado": Status.DISCARDED,
}

Test.categories = pd.CategoricalDtype(Test)
Gender.categories = pd.CategoricalDtype(Gender)
Evolution.categories = pd.CategoricalDtype(Evolution)
Status.categories = pd.CategoricalDtype(Status)


def from_map(mapping, na=pd.NA, key=lambda x: x):
    def fn(x):
        if not x or pd.isna(x):
            return na
        try:
            res = mapping[key(x)]
        except KeyError:
            opts = ", ".join(map(repr, mapping))
            msg = f"not a valid option: {x!r}, expect: {opts}"
            raise ValueError(msg)
        return res.value if isinstance(res, Enum) else res

    return fn


GENDER = {"Feminino": Gender.FEMALE, "Masculino": Gender.MALE, "null": pd.NA}
DTYPES = {
    "idade": int,
    "profissionalSaude": bool,
    "resultadoTeste": bool,
    "tipoTeste": "string",
    "bairro": "string",
    "estado": "string",
    "municipio": "string",
    "cnes": "string",
    "estadoTeste": "string",
    "sexo": "string",
    "evolucaoCaso": "string",
    "classificacaoFinal": "string",
    "cbo": "string",
}
CONVERTERS = {
    "sintomas": to_symptom,
    "estadoTeste": from_map(TEST),
    "resultadoTeste": lambda x: x.lower() == "positivo",
    "sexo": from_map(GENDER),
    "tipoTeste": lambda x: x if isinstance(x, str) else pd.NA,
    "evolucaoCaso": from_map(EVOLUTION),
    "classificacaoFinal": from_map(STATUS),
    "profissionalSaude": from_map({"Sim": True, "Não": False, "null": False}, False),
    "cbo": lambda x: pd.NA if x in ("null",) else x.split("-")[0].strip()[:4],
}
RENAME = {
    "dataNotificacao": "notification_date",
    "dataInicioSintomas": "onset_date",
    "dataNascimento": "birthday",
    "sintomas": "symptoms",
    "profissionalSaude": "is_healthcare_worker",
    "cbo": "healthcare_worker_kind",
    "condicoes": "conditions",
    "estadoTeste": "test_status",
    "dataTeste": "test_date",
    "tipoTeste": "test_type",
    "resultadoTeste": "is_confirmed",
    "origem": "origin",
    "cnes": "healthcare_unit_id",
    "estadoNotificacao": "notification_state",
    "municipioNotificacao": "notification_city",
    "numeroNotificacao": "notification_id",
    "excluido": "excluded",
    "validado": "validated",
    "idade": "age",
    "dataEncerramento": "recovery_date",
    "evolucaoCaso": "evolution",
    "classificacaoFinal": "status",
    "paisOrigiem": "country",
    "sexo": "gender",
    "estado": "state",
    "bairro": "neigborhood",
    "municipio": "city",
}


@ttl_cache("sari-br", timeout=24 * 3600)
def sari_br_state_content(region: str) -> bytes:
    region = mundi.region(region)
    ref = region.short_code.lower()
    url = f"https://s3-sa-east-1.amazonaws.com/ckan.saude.gov.br/dados-{ref}.csv"
    log.info(f"[sari-br] Downloading data for {region}")
    response = requests.get(url)
    log.info(f"[sari-br] Download complete!")
    return response.content


def sari_br_state_dataframe(region: Region) -> pd.DataFrame:
    """
    Return the full table of SARI hospital vigilance for the given region.
    """

    region = mundi.region(region)
    content = sari_br_state_content(region.id)
    lines = content.splitlines()
    content = lines[0] + b"\n" + b"\n".join(lines[-1000:])
    fd = io.BytesIO(content)

    with st.spinner(f"Converting to CSV ({region.name})"):
        chunks = []
        date_columns = [
            "dataNotificacao",
            "dataInicioSintomas",
            "dataNascimento",
            "dataEncerramento",
            "dataTeste",
        ]
        for df in pd.read_csv(
            fd,
            index_col=0,
            sep=";",
            parse_dates=date_columns,
            dtype=DTYPES,
            converters=CONVERTERS,
            engine="c",
            chunksize=1000,
            encoding="latin1",
        ):
            df: pd.DataFrame = (
                df.astype(DTYPES)
                .rename(columns=RENAME)
                .astype(
                    {
                        "status": Status.categories,
                        "gender": Gender.categories,
                        "evolution": Evolution.categories,
                        "test_status": Test.categories,
                    }
                )
            )

            def localtime(x):
                if pd.isna(x):
                    return x
                return x.time()

            df["notification_time"] = df["notification_date"].apply(localtime)
            df["notification_date"] = df["notification_date"].apply(
                lambda x: x if pd.isna(x) else x.date()
            )
            df.index.name = "id"
            chunks.append(df)

    df = pd.concat(chunks)
    return df


def sari_br_dataframe():
    """
    Aggregate SARI vigilance for all states.
    """
    states = mundi.regions("BR", type="state").index
    data = [sari_br_state_dataframe(state) for state in states]
    return pd.concat(data)


# https://shiny.hmg.saude.gov.br/dataset/casos-nacionais


def main(**kwargs):
    df = sari_br_dataframe()
    st.write(
        df.astype(
            {
                k: str
                for k in df.dtypes[
                    (df.dtypes == "string") | (df.dtypes == "category")
                ].index
            }
        )
    )
    x = df.reset_index()[["age", "id"]].groupby("age").count()
    st.bar_chart(x)


if __name__ == "__main__":
    main()
