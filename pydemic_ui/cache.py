import joblib
import time
from scheduler import scheduler

path = ".tmp/"
memory = joblib.Memory(path)


class Cache:
    @memory.cache
    def call_with_time(*args, **kwargs):
        clock, fn, *args = args
        return (clock(), fn(*args, **kwargs))

    class TTL:
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
        Usage:
            >>> @Cache.TTL(10, True, 30)
            ... def fn(x):
            ...    time.sleep(2.4)
            ...    return x * 2

        """

        def __init__(self, ttl, fasttrack=False, max_ttl=float("inf"), clock=time.time):
            self.ttl = ttl
            self.fasttrack = fasttrack
            self.max_ttl = max_ttl
            self.clock = clock

        def __call__(self, fn):
            def decorated(*args, **kwargs):
                def run():
                    return Cache.call_with_time.call_and_shelve(self.clock, fn, *args, **kwargs)

                ref = run()
                (time_, result) = ref.get()

                # checks if ttl has been reached
                if time_ + self.ttl < self.clock():

                    def update():
                        ref.clear()
                        return run().get()[1]

                    # checks if max_ttl has been reached
                    if self.fasttrack and (time_ + self.max_ttl > clock()):
                        scheduler().schedule_now(update)
                    else:
                        return update()
                return result
            return decorated

    class Schedule:
        """
        Create a function that updates cache at the given frequency.

        Args:
            frequency:
                Frequency at which to update the cache.
                Can be a number of seconds or the strings "daily", "weekly" and "monthly"
            time:
                For daily, weekly and monthly updates, defines the time at
                which it schedule updates.

        Usage:
            >>> @Cache.Schedule('daily', time=...)
            ... def fn(x):
            ...    return x + 1

        """
        def __init__(self, frequency, time=None, clock=time.time):
            self.frequency = frequency
            self.clock = clock
            self.time = time

        def __call__(self, fn):
            def decorated(*args, **kwargs):
                ref = Cache.call_with_time.call_and_shelve(self.clock, fn, *args, **kwargs)
                (time_, result) = ref.get()

                def update():
                    ref.clear()
                    return Cache.call_with_time.call_and_shelve(self.clock, fn, *args, **kwargs)

                if self.frequency == "daily":
                    scheduler().schedule_daily(update, self.time)
                elif self.frequency == "weekly":
                    scheduler().schedule_weekly(update, self.time)
                elif self.frequency == "monthly":
                    scheduler().schedule_monthly(update, self.time)

                return result

            return decorated


@Cache.TTL(10, True, 30)
def fn(x):
    time.sleep(2.4)
    return x * 2


@Cache.Schedule('daily', time=...)
def fn1(x):
    time.sleep(2.4)
    return x * 2
