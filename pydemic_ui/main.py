from threading import Thread, Lock
from collections import deque
from time import time as _time, sleep, mktime
import datetime
from logging import getLogger

log = getLogger('pydemic')
SCHEDULER = None


class Scheduler:
    """
    Schedule tasks to run on the background.
    """

    def __init__(self, clock=_time, sleep=sleep):
        self.tasks = deque()
        self._lock = Lock()
        self._id = 0
        self._sleep = lambda: sleep(1.0)
        self._clock = clock
        self._clock_args = None
        self._running = False
        self._stopped = False

    def start(self):
        """
        Start scheduler in the background.
        """
        if not self._running:
            thread = Thread(target=self.main_loop)
            thread.start()
            self._running = True

    def stop(self):
        """
        Stop all tasks and reset scheduler.
        """

    def pause(self):
        """
        Temporarely stop tasks.
        """

    def list_all_tasks(self):
        """
        Returns a list of all scheduled tasks
        """

        tasks = [
            (f"time = {t[0]}", f"id = {t[1]}", f"task = {t[2].__name__}") for t in self.tasks
        ]

        return tasks

    def main_loop(self):
        """
        Consume and wait for tasks.
        """
        sleep = self._sleep
        clock_increment = 0

        while True:
            if not self.tasks:
                sleep()
                continue

            with self._lock:
                (time, _, task) = self.tasks[0]
                
                if self._clock.__name__ != "time":
                    clock = self._clock(self._clock_args) + clock_increment
                else:
                    clock = self._clock()
                
                if time > clock:
                    task = sleep
                else:
                    self.tasks.popleft()

                clock_increment += 1

            try:
                task()
            except Exception as ex:
                name = task.__name__
                msg = f'error running task {name}:\n'
                msg += f'   {type(ex)}: {ex}'
                log.error(msg)
            
    def schedule(self, task, time):
        """
        Schedule task to run at some precise time.
        """
        # TODO: function should accept dates and datetimes
        if isinstance(time, (datetime.date, datetime.datetime)):
            time = datetime_to_time(time)

        with self._lock:
            self._id += 1
            self.tasks.append((time, self._id, task))
            self.tasks = deque(sorted(self.tasks))

    def schedule_now(self, task):
        return self.schedule_after(task, 0.0)

    def schedule_after(self, task, duration):
        """
        Schedule task to run after the given duration.
        """
        return self.schedule(task, _time() + duration)

    def schedule_daily(self, task, time=datetime.time()):
        unix_time = ...
        interval = 24 * 60 * 60

        def run_and_schedule():
            nonlocal unix_time
            try:
                unix_time += interval
                self.schedule(run_and_schedule, unix_time)
            finally:
                task()

        self.schedule(run_and_schedule, unix_time)

    def schedule_weekly(self, task, time=datetime.time()):
        ...
    
    def schedule_montly(self, task, time=datetime.time()):
        ...

    def _schedule_at_interval(self, interval, task, time):
        ...


def scheduler():
    """
    Return the main scheduler.
    """
    global SCHEDULER

    if SCHEDULER is None:
        SCHEDULER = Scheduler()
    return SCHEDULER


def datetime_to_time(dt):
    """
    Convert date or datetime objects to unix time.
    """

    return mktime(dt.timetuple())
