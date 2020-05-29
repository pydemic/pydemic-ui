from collections import deque
from functools import wraps, lru_cache
from types import MappingProxyType
from typing import NamedTuple

from pydemic.utils import format_args


class Mixin:
    result: object
    name: str
    args: tuple
    kwargs: dict

    def __str__(self):
        return f"driver.{self.name}({self._repr_args()})"

    def _repr_args(self):
        if self.args is ... and self.kwargs is ...:
            return "..."
        else:
            return format_args(*self.args, **self.kwargs)

    def assert_arguments(self, args, kwargs):
        """
        Check if given args and kwargs are expected
        """
        if self.args is not ... and (args != self.args or kwargs != self.kwargs):
            args = format_args(*args, **kwargs)
            msg = f"called with wrong arguments, expect {self}, got: {self.name}({args})"
            raise AssertionError(msg)
        return self.result


class _Step(NamedTuple):
    name: str
    args: tuple = ()
    kwargs: dict = MappingProxyType({})
    result = None


class _Expect(NamedTuple):
    result: object
    name: str
    args: tuple = None
    kwargs: dict = None


class Step(Mixin, _Step):
    """
    Execution step of a streamlit command.
    """

    @staticmethod
    def from_call(*args, **kwargs):
        """
        Start step from method call.
        """
        name, *args = args
        return Step(name, args, kwargs)

    def __repr__(self):
        return f"out.{self.name}({self._repr_args()})"

    def run(self, st):
        """
        Run single step in the given streamlit module.
        """
        fn = getattr(st, self.name)
        return fn(*self.args, **self.kwargs)


class Expect(Mixin, _Expect):
    """
    Input step.
    """

    def check(self, step: Step):
        if self.name != step.name:
            raise AssertionError("executed the wrong function.")

        return self.result


class StLogger:
    """
    Log execution of streamlit commands.

    Base class for a replay runner and a test driver.
    """

    def __init__(self):
        self._steps = []

    def __getstate__(self):
        return self._steps[:]

    def __setstate__(self, state):
        self._steps = state[:]

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)

        def method(*args, **kwargs):
            self._steps.append(Step.from_call(attr, *args, **kwargs))
            return None

        setattr(self, attr, method)
        return method

    def __call__(self, st=None):
        """
        Run sequence of steps into the given streamlit-like module.
        """

        if st is None:
            from pydemic_ui import st

        for step in self._steps:
            step.run(st)

    def __iter__(self):
        """
        Return list of steps
        """
        return iter(self._steps)


class Replay(StLogger):
    """
    A simple logger used to cache streamlit executions and replay them.
    """

    def __init__(self, module):
        super().__init__()
        self._module = module

    def __call__(self, st=None):
        return super()(st or self._module)

    def pyplot(self, *args, **kwargs):
        if not args:
            raise ValueError("pyplot requires an explicit figure in cached mode.")
        return self.__getattr__("pyplot")(*args, **kwargs)

    def _input(self, *args, **kwargs):
        raise ValueError("Input functions are not allowed in replay mode")

    selectbox = text_input = number_input = date_input = slider = textarea = _input


class Driver(StLogger):
    """
    Streamlit test driver.
    """

    _tasks: deque

    def __init__(self, expect=()):
        super().__init__()
        self._steps = deque(self._steps)

        for task in expect:
            self.expect(task)

    def __getattr__(self, attr):
        if attr.startswith("_"):
            raise AttributeError(attr)

        def method(*args, **kwargs):
            if not self._steps:
                args = format_args(*args, **kwargs)
                msg = f"Trying to execute st.{attr}({args}), but task queue is empty"
                raise AssertionError(msg)

            task = self._steps.popleft()
            if task is ...:
                return

            if task.name != attr:
                args = format_args(*args, **kwargs)
                msg = f"expect to run {task}, but got st.{attr}({args})"
                raise AssertionError(msg)

            return task.assert_arguments(args, kwargs)

        return method

    def expect(self, task):
        """
        Expect a single task or user interaction.
        """

        if isinstance(task, (Step, Expect)):
            self._steps.append(task)
        elif isinstance(task, str):
            self._steps.append(Step(task, ..., ...))
        elif task is ...:
            self._steps.append(...)
        else:
            cls = type(task).__name__
            raise TypeError(f"Tasks of type {cls} are not supported")

    def is_empty(self) -> bool:
        """
        Return True if the queue of tasks is empty.
        """

        return not self._steps


def replay_cache(func):
    """
    Decorate function that receives a where=st keyword argument.
    """

    from pydemic_ui import st

    @lru_cache(50)
    def output_replay(*args, **kwargs) -> Replay:
        replay = Replay(st)
        func(*args, st=replay, **kwargs)
        return replay

    @wraps(func)
    def cached(*args, where=None, **kwargs):
        replay = output_replay(*args, **kwargs)
        return replay(where)

    return cached


class _Out:
    """
    Implements the out singleton.
    """

    def __getattr__(self, attr):
        def method(*args, **kwargs):
            if args == (...,) and not kwargs:
                return Step(attr, ..., ...)
            return Step(attr, args, kwargs)

        method.__name__ = attr
        return method


class _Ask:
    """
    Implements the ask singleton.
    """

    def __getattr__(self, attr):
        return _AskInput(attr)


class _AskInput:
    """
    Implement the ask.method[result](...) interface
    """

    def __init__(self, name):
        self.__name = name

    def __getitem__(self, item):
        def method(*args, **kwargs):
            if args == (...,) and not kwargs:
                return Expect(item, self.__name, ..., ...)
            return Expect(item, self.__name, args, kwargs)

        return method


def with_title(fn, default=None, level="header", where=None):
    """
    Makes function accept an optional title, header or subheader arguments.
    """

    from pydemic_ui import st as st_mod

    NOT_GIVEN = object()
    if level not in {"header", "subheader"}:
        raise ValueError("level must be either 'header' or 'subheader'")

    @wraps(fn)
    def decorated(
        *args, title=NOT_GIVEN, header=NOT_GIVEN, subheader=NOT_GIVEN, **kwargs
    ):

        st = kwargs.get("where", st_mod) if where is None else where

        if header is not NOT_GIVEN and not isinstance(header, bool):
            st.header(str(header))
        elif subheader is not NOT_GIVEN and not isinstance(subheader, bool):
            st.subheader(str(subheader))
        if title is not NOT_GIVEN or default:
            if subheader or level == "subheader":
                st.subheader(str(title))
            else:
                st.header(str(title))

        return fn(*args, **kwargs)

    return decorated


out = _Out()
ask = _Ask()
