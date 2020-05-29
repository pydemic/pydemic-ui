from functools import singledispatch

import pandas as pd


@singledispatch
def data_to_dataframe(data) -> pd.DataFrame:
    """
    Coerce input to a pandas DataFrame.
    """
    return pd.DataFrame(data)


@data_to_dataframe.register(pd.DataFrame)
def _(data):
    return data


@data_to_dataframe.register(pd.Series)
def _(data):
    return pd.DataFrame({"data": data})


@data_to_dataframe.register(type(None))
def _(_data):
    return pd.DataFrame([[]], columns=["data"])
