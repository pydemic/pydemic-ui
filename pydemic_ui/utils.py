from functools import singledispatch

import pandas as pd
from babel.dates import format_date

from pydemic_ui.i18n import _

NOT_GIVEN = object()


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


def natural_date(x):
    """
    Friendly representation of dates.

    String inputs are returned as-is.
    """
    if isinstance(x, str):
        return x
    elif x is None:
        return _("Not soon...")
    else:
        return format_date(x, format="short")


def get_some_attr(obj, *attrs, default=NOT_GIVEN):
    """
    Get the first valid attribute from list or return default, if given.

    It accepts attributes in dotted notation
    """

    for attr in attrs:
        if "." in attr:
            tmp = obj

            for part in attr.split("."):
                try:
                    tmp = getattr(tmp, part)
                except AttributeError:
                    break
            else:
                return tmp
        else:
            try:
                return getattr(obj, attr)
            except AttributeError:
                continue

    if default is NOT_GIVEN:
        raise AttributeError
    return default
