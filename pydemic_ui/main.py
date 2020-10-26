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
        self._clock_tick = 0
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
        Return a list of all scheduled tasks
        """

        tasks = [
            (f"time = {t[0]}", f"id = {t[1]}", f"task = {t[2].__name__}", f"frequency = {t[3]}") for t in self.tasks
        ]

        return tasks

    def main_loop(self):
        """
        Consume and wait for tasks.
        """
        sleep = self._sleep
        self._clock_tick = 0

        while True:
            if not self.tasks:
                sleep()
                continue

            with self._lock:
                (time, _, task, frequency) = self.tasks[0]
                
                if self._clock.__name__ != "time":
                    clock = self._clock(self._clock_args) + self._clock_tick
                else:
                    clock = self._clock()
                
                if time > clock:
                    task = sleep
                else:
                    self.tasks.popleft()

                    if frequency == "daily":
                        self.schedule(task, time+24*60*60, 'daily')
                    
                    elif frequency == 'weekly':
                        self.schedule(task, time+7*24*60*60, 'weekly') 

                    elif frequency == 'monthly':
                        data = unix_time_to_string(time)
                        month = date_string_to_datetime(data).month

                        if month == 4 or month == 6 or month == 9 or month == 11:
                            month_days = 30
                        elif month == 2:
                            month_days = 28
                        else:
                            month_days = 31

                        self.schedule(task, time+month_days*24*60*60, 'monthly')

                self._clock_tick += 1

            try:
                task()
            except Exception as ex:
                name = task.__name__
                msg = f'error running task {name}:\n'
                msg += f'   {type(ex)}: {ex}'
                log.error(msg)
            
    def schedule(self, task, time, frequency=None):
        """
        Schedule task to run at some precise time.
        """

        # TODO: function should accept dates and datetimes
        if isinstance(time, datetime.datetime):
            time = datetime_to_time(time)

        # with self._lock:
        self._id += 1
        self.tasks.append((time, self._id, task, frequency))
        self.tasks = deque(sorted(self.tasks))

    def schedule_now(self, task):
        return self.schedule_after(task, 0.0)

    def schedule_after(self, task, duration):
        """
        Schedule task to run after the given duration.
        """
        return self.schedule(task, _time() + duration)

    def schedule_daily(self, task, time):
        
        self.schedule(task, time, 'daily')

    def schedule_weekly(self, task, time):
        
        self.schedule(task, time, 'weekly')
    
    def schedule_montly(self, task, time):
        
        self.schedule(task, time, 'monthly')

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


def unix_time_to_string(time):
    """
    Convert unix time to readable string in the format %Y-%m-%d %H:%M:%S
    """

    return datetime.datetime.utcfromtimestamp(int(time)).strftime('%Y-%m-%d %H:%M:%S')


def date_string_to_datetime(string):
    """
    Convert a date string in the format %Y-%m-%d %H:%M:%S to a datetime object
    """

    return datetime.datetime.strptime(string, '%Y-%m-%d %H:%M:%S')
