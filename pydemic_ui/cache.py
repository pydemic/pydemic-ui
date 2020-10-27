import joblib
import time
from scheduler import scheduler

path = ".tmp/"
memory = joblib.Memory(path)


def cache_ttl(ttl, fasttrack=False, force_expiration=None, clock=time.time):
    """
    Create a cached function with a time to live expiration.

    Args:
        ttl:
            Time that results live in cache.
        fasttrack (bool):
            If true, return result in cache and schedule update in the
            background.
        force_expiration:
            If given, force cache update after the given expiration period.
            It has no effect if fasttrack is False.
    """

    def decorator(fn):
        def decorated(*args, **kwargs):
            ref = call_with_time.call_and_shelve(clock, fn, *args, **kwargs)
            (time_, result) = ref.get()

            if force_expiration:
                ...  # Tempo máximo de duração do cache. Força recálculo

            if time_ + ttl < clock():

                def run():
                    ref.clear()
                    return call_with_time(clock, fn, *args, **kwargs)[1]

                if fasttrack:
                    scheduler().schedule_now(run)
                else:
                    return run()

            return result

        return decorated

    return decorator


def cache_schedule(frequency, start=None):
    """
    Create a function that updates cache at the given frequency.

    Args:
        frequency:
            Frequency at which to update the cache.
            Can be a number of seconds or the strings "daily", "weekly" and "monthly"
        time:
            For daily, weekly and monthly updates, defines the time at which it schedule updates.

    Usage:
        >>> @cache_schedule('daily', time=...)
        ... def fn(x):
        ...    return x + 1

    """

    def decorator(fn):
        def decorated(*args, **kwargs):
            ...

        return decorated

    return decorator


@memory.cache
def call_with_time(*args, **kwargs):
    clock, fn, *args = args
    return (clock(), fn(*args, **kwargs))


@cache_schedule("daily", time=...)
def fn(x):
    return x + 1


@cache_ttl(30)
def fn(x):
    return x * 2
