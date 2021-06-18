import datetime
import math
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from logging import getLogger
from typing import ContextManager

import sidekick.api as sk
from . import st
from .i18n import _


class SimpleApp(ABC):
    """
    Simple app that asks for user input and
    """

    # Default attributes
    title: str = _("No title")
    description: str = _("No description")
    logging = False

    @classmethod
    def main(cls, *args, **kwargs):
        app = cls(*args, **kwargs)
        return app.run()

    def __init__(self, embed=False, where=st, **kwargs):
        self._init_st = where
        self.st = where
        self.embed = embed
        self.css = kwargs.pop("css", not embed)
        self.logo = kwargs.pop("logo", not embed)

        # Generic properties
        self.title = _(kwargs.pop("title", self.title))
        self.description = _(kwargs.pop("description", self.title))

        # Other
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                raise TypeError(f"invalid argument: {k}")

    def __getattr__(self, item):
        if item.startswith("_"):
            raise AttributeError(item)
        return getattr(self.st, item)

    def __repr__(self):
        cls = type(self).__name__
        return f"{cls}(..., title={self.title!r})"

    @contextmanager
    def sidebar(self):
        """
        Rebinds streamlit context to the sidebar.
        """
        st = self._init_st
        with self.streamlit(getattr(st, "sidebar", st)) as new:
            yield new

    @contextmanager
    def streamlit(self, new) -> ContextManager:
        """
        Temporarily rebinds the internal streamlit target to the given location
        inside the with block.

        Examples:
            >>> with app.streamlit(st_mock):
            ...     app.do_something()
        """
        old = self._init_st
        self.st = new
        try:
            yield new
        finally:
            self.st = old

    @abstractmethod
    def ask(self):
        """
        Ask for user input and save values as properties in the app.

        The default implementation does nothing.
        """
        ...  # Implement in sub-classes

    @abstractmethod
    def show(self):
        """
        Runs simulations and display outputs.
        """
        self.st.markdown(_("`.show_outputs()` must be implemented in sub-classes"))

    def run(self):
        """
        Run application.
        """

        if self.css:
            self.st.css()
        if self.logo:
            with self.sidebar() as st:
                st.logo()
        if not self.embed and self.title:
            self.st.title(self.title)

        # Ask for inputs
        timer = Timer()
        with self.streamlit(self.st) if self.embed else self.sidebar():
            self.ask()
        interaction_time = timer.elapsed

        # Run simulations
        variables = dict(self.__dict__)
        log_entry = {
            "timestamp": datetime.datetime.now(),
            "state": variables,
            "results": timer.timed(self.show),
            "results_runtime": timer.cumulative(),
            "interaction_runtime": interaction_time,
        }
        if self.logging:
            self.log(log_entry)

    def log(self, entry):
        """
        Log events
        """
        log = getLogger("pydemic_ui")
        log.info(repr(entry))


class Timer:
    @property
    def elapsed(self):
        """
        Time elapsed since the creation of timer.
        """
        return self._timer_function() - self.start

    def __init__(self, timer=time.monotonic):
        self._timer_function = timer
        self.start = timer()
        self._events = []

    def timed(*args, **kwargs):
        """
        Time execution.

        Can be used as a context manager as in:

        >>> with timer.timed() as clock:
        ...     do_something_expansive()

        Or can be used to call a function:

        >>> timer.timed(fn, *args, **kwargs)
        <result>
        """

        if len(args) == 1:
            return args[0]._timed_context_manager()

        self, fn, *args = args
        start = self._timer_function()
        res = fn(*args, **kwargs)
        self._events.append(self._timer_function() - start)
        return res

    @contextmanager
    def _timed_contextmanager(self):
        def clock():
            if clock.stopped:
                return duration
            else:
                return clock.start - self._timer_function()

        try:
            clock.timer = self
            clock.start = self._timer_function()
            clock.stopped = False
            yield clock
        finally:
            duration = clock()
            self._events.append(duration)
            clock.stopped = True

    def cumulative(self):
        """
        Cumulative time spent after all calls to timed.
        """
        return sum(self._events, 0.0)

    def mean(self):
        """
        Mean duration of all events.
        """
        return self.cumulative() / len(self._events)

    def std(self):
        """
        Mean duration of all event durations.
        """
        ev2 = sum(x * x for x in self._events) / len(self._events)
        return math.sqrt(ev2 - self.mean() ** 2)
