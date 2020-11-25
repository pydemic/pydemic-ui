import joblib
import time
from pydemic_ui.scheduler import scheduler

path = ".tmp/"
memory = joblib.Memory(path)


class Cache:
    @memory.cache
    def call_with_time(*args, **kwargs):
        clock, fn, *args = args
        return (clock(), fn(*args, **kwargs))

    class TTL:
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
@joblib.wrap_non_picklable_objects
def fn(x):
    time.sleep(2.4)
    return x * 2

@Cache.Schedule('daily', time=...)
@joblib.wrap_non_picklable_objects
def fn1(x):
    time.sleep(2.4)
    return x * 2

fn1(5)