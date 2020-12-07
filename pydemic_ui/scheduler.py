from threading import Thread, Lock
from collections import deque
from time import time as _time, sleep, mktime
import datetime
from logging import getLogger

log = getLogger("pydemic")
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
        self._clock_tick = 0
        self._running = False
        self._stopped = False

    def start(self):
        """
        Start scheduler in the background.
        """
        if not self._running:
            self.thread = Thread(target=self.main_loop)
            self._running = True
            self.thread.start()

    def stop(self):
        """
        Stop all tasks and reset scheduler.
        """

        self.tasks = []
        self._running = False
        self.thread.join()

    def pause(self):
        """
        Temporarely stop tasks.
        """

        self._running = False

    def resume(self):

        self._running = True

    def list_all_tasks(self):
        """
        Return a list of all scheduled tasks
        """

        tasks = [
            (
                f"time = {t[0]}",
                f"id = {t[1]}",
                f"task = {t[2].__name__}",
                f"frequency = {t[3]}",
            )
            for t in self.tasks
        ]

        return tasks

    def main_loop(self):
        """
        Consume and wait for tasks.
        """
        sleep = self._sleep
        self._clock_tick = 0

        while True:
            if not self._running:
                break

            if not self.tasks:
                sleep()
                continue

            with self._lock:
                (time_to_run, _, task_to_run, frequency_to_repeat) = self.tasks[0]

                if self._clock.__name__ != "time":
                    clock = self._clock(self._clock_args) + self._clock_tick
                else:
                    clock = self._clock()

                if time_to_run > clock:
                    task_to_run = sleep
                else:
                    self.tasks.popleft()

                    if frequency_to_repeat == "daily":
                        self.__schedule_daily(task_to_run, time_to_run)

                    elif frequency_to_repeat == "weekly":
                        self.__schedule_weekly(task_to_run, time_to_run)

                    elif frequency_to_repeat == "monthly":
                        self.__schedule_monthly(task_to_run, time_to_run)

                self._clock_tick += 1

            try:
                task_to_run()
            except Exception as ex:
                name = task_to_run.__name__
                msg = f"error running task {name}:\n"
                msg += f"   {type(ex)}: {ex}"
                log.error(msg)

    def schedule(self, task_to_run, time_to_start, frequency_to_repeat=None):
        """
        Schedule task to run at some precise time.
        """

        # TODO: function should accept dates and datetimes
        if isinstance(time_to_start, datetime.datetime):
            time_to_start = datetime_to_time(time_to_start)

        self._id += 1
        self.tasks.append((time_to_start, self._id, task_to_run, frequency_to_repeat))
        self.tasks = deque(sorted(self.tasks))

    def schedule_now(self, task_to_schedule):
        return self.schedule_after(task_to_schedule, 0.0)

    def schedule_after(self, task_to_schedule, duration):
        """
        Schedule task to run after the given duration.
        """
        return self.schedule(task_to_schedule, _time() + duration)

    def schedule_daily(self, task_to_schedule, time_to_start):

        self.schedule(task_to_schedule, time_to_start, "daily")

    def __schedule_daily(self, task_to_schedule, time_to_start):

        self.schedule(task_to_schedule, time_to_start + 24 * 60 * 60, "daily")

    def schedule_weekly(self, task_to_schedule, time_to_start):

        self.schedule(task_to_schedule, time_to_start, "weekly")

    def __schedule_weekly(self, task_to_schedule, time_to_start):

        self.schedule(task_to_schedule, time_to_start + 7 * 24 * 60 * 60, "weekly")

    def schedule_monthly(self, task_to_schedule, time_to_start):

        self.schedule(task_to_schedule, time_to_start, "monthly")

    def __schedule_monthly(self, task_to_schedule, time_to_start):

        unix_time = unix_time_to_string(time_to_start)
        month = date_string_to_datetime(unix_time).month

        if month == 4 or month == 6 or month == 9 or month == 11:
            month_days = 30
        elif month == 2:
            month_days = 28
        else:
            month_days = 31

        self.schedule(task_to_schedule, time_to_start + month_days * 24 * 60 * 60, "monthly")

    def _schedule_at_interval(self, interval, task_to_schedule, time_to_start):
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


def unix_time_to_string(time):
    """
    Convert unix time to readable string in the format %Y-%m-%d %H:%M:%S
    """

    return datetime.datetime.utcfromtimestamp(int(time)).strftime("%Y-%m-%d %H:%M:%S")


def date_string_to_datetime(string):
    """
    Convert a date string in the format %Y-%m-%d %H:%M:%S to a datetime object
    """

    return datetime.datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
