import joblib
import time
from pydemic_ui.scheduler import scheduler
from pydemic_ui.cache import Cache

path = ".tmp/"
memory = joblib.Memory(path)


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


fn(5)
fn1(5)
