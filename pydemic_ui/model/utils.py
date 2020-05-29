from functools import wraps


def bind_function(fn):
    """
    Binds function such as where is bound to the property default module.
    """

    @wraps(fn)
    def method(self, *args, where=None, **kwargs):
        if where is None:
            where = self.module
        return fn(self._object, *args, where=where, **kwargs)

    return method
