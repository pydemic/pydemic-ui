import joblib
import time
from scheduler import scheduler

path = ".tmp/"
memory = joblib.Memory(path)


def cache_ttl(ttl, fasttrack=False, max_ttl=float("inf"), clock=time.time):
    """
    Create a cached function with a time to live expiration.

    Args:
        ttl:
            Time that results live in cache.
        fasttrack (bool):
            If true, return result in cache and schedule update in the
            background.
        max_ttl:
            If given, force cache update after the given expiration period.
            It has no effect if fasttrack is False.
    """

    def decorator(fn):
        def decorated(*args, **kwargs):
            def run():
                return call_with_time.call_and_shelve(clock, fn, *args, **kwargs)

            ref = run()
            (time_, result) = ref.get()

            # checks if ttl has been reached
            if time_ + ttl < clock():

                def update():
                    ref.clear()
                    return run().get()[1]

                # checks if max_ttl has been reached
                if fasttrack and (time_ + max_ttl > clock()):
                    scheduler().schedule_now(update)
                else:
                    return update()

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

            frequency, time, *args = args

            ref = call_with_time.call_and_shelve(clock, fn, *args, **kwargs)
            (time_, result) = ref.get()

            def update():
                ref.clear()
                return call_with_time.call_and_shelve(clock, fn, *args, **kwargs)

            if frequency == "daily":
                scheduler().schedule_daily(update, time)
            elif frequency == "weekly":
                scheduler().schedule_weekly(update, time)
            elif frequency == "monthly":
                scheduler().schedule_monthly(update, time)

            return result

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
