import operator as op

from pydemic.properties import Property


class UIBaseProperty(Property):
    """
    Common implementation of model.ui and model.ui.sidebar properties.
    """

    __slots__ = ()
    model = property(op.attrgetter("_object"))
    module = None
