import inspect
from functools import wraps

from . import st

NOT_GIVEN = object()


def title(default=None, level="header"):
    """
    A decorator that add an optional title argument to component.
    """

    def decorator(fn):
        loc = get_argument_default(fn, "where", None) or st

        @wraps(fn)
        def wrapped(
            *args,
            title=default,
            level=level,
            header=None,
            subheader=None,
            where=loc,
            **kwargs,
        ):
            if header:
                where.header(str(header))
            elif subheader:
                where.subheader(str(subheader))
            elif title:
                if level == "header":
                    where.header(str(title))
                elif level == "subheader":
                    where.subheader(str(title))
                elif level == "bold":
                    where.markdown(f"**{title}**")
                else:
                    raise ValueError(f"invalid title level: {level!r}")

            kwargs["where"] = where
            return fn(*args, **kwargs)

        return wrapped

    return decorator


def get_argument_default(fn, argument, default=NOT_GIVEN):
    """
    Return the default value of the given function argument or raise an exception.
    """

    try:
        sig = inspect.Signature.from_callable(fn)
        param = sig.parameters[argument]
        return param.value
    except AttributeError:
        if default is NOT_GIVEN:
            raise ValueError("argument does not exist or have a default value")
        return default
