import importlib

import streamlit as st

from pydemic.logging import log
from pydemic.utils import to_json
from .i18n import _


class Runner:
    """
    Wraps a function to gain a to_json() method and being pickable.
    """

    @property
    def name(self):
        return f"{self.func.__module__}.{self.func.__qualname__}"

    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def __call__(self, model, days):
        log.info("Runner: %s" % self)
        return self.func(*self.args, **self.kwargs)(model, days)

    def __repr__(self):
        return f"<Runner object for {self}>"

    def __str__(self):
        args = [*map(repr, self.args)]
        args.extend(f"{k}={v!r}" for k, v in self.kwargs.items())
        args = ", ".join(args)
        return f"{self.name}({args})"

    def __getstate__(self):
        return self.name, self.args, self.kwargs

    def __setstate__(self, state):
        name, self.args, self.kwargs = state
        mod_name, _, func_name = name.rpartition(".")
        mod = importlib.import_module(mod_name)
        factory = getattr(mod, func_name)
        self.func = getattr(factory, "runner_function", factory)

    def __eq__(self, other):
        if isinstance(other, Runner):
            return self.__getstate__() == other.__getstate__()
        return NotImplemented

    def to_json(self):
        return {
            "runner": self.name,
            "args": to_json(self.args),
            "kwargs": to_json(self.kwargs),
        }


def runner(fn):
    """
    Decorates runner functions.
    """
    out = lambda *args, **kwargs: Runner(fn, *args, **kwargs)
    out.runner_function = fn
    return out


def run(model, days):
    """
    Runs the given model by the selected number of days
    """
    model.run(days)
    return model


#
# Runner objects
#
@runner
def simple_runner():
    """
    Simply execute the "run" function.
    """
    return run


@runner
def stage_runner(stages):
    """
    Model with multiple stages of social distancing.
    """

    def fn(model, days):
        R0 = model.R0
        model.initialize()

        for dt, rate in stages:
            model.R0 = R0 * rate

            duration = min(dt, days)
            if duration:
                log.debug(f"stage_runner: Running {duration} steps with R0={model.R0}")
                model.run(duration)

            days -= dt
            if days <= 0:
                break

        return run(model, days) if days > 0 else model

    return fn


@runner
def R0_rate_runner(date, rate):
    """
    Multiply R0 by the given rate after some days of simulation.
    """

    def fn(model, days):
        start_date = model.to_date(0)
        if date < start_date:
            st.warning(_("Intervention starts prior to simulation"))
            model.R0 *= rate
            model.run(days)
            return model
        else:
            t0 = (date - start_date).days
            R0_final = model.R0 * rate
            model = run(model, t0)
            model.R0 = R0_final
            return run(model, days - t0)

    return fn


@runner
def relax_intervention_runner(date, rate0, rate1):
    """
    Multiply R0 by the given rate after some days of simulation.
    """

    e = 1e-3
    fn_rate = R0_rate_runner(date, (1 - rate1 + e) / (1 - rate0 + e))

    def fn(model, days):
        model.R0 *= 1 - rate0
        return fn_rate(model, days)

    return fn
