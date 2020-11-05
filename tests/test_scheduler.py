from pydemic_ui.scheduler import *


class TestScheduler:
    def test_if_a_task_is_scheduled(self):
        def say_hello():
            print("hello")

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 9, 15, 12, 30)
        agendador._sleep = lambda: sleep(0)

        agendador.start()
        data = datetime.datetime(2020, 9, 15, 12, 40, 3)
        agendador.schedule(say_hello, data)

        agendador.pause()

        assert unix_time_to_string(agendador.tasks[0][0]) == "2020-09-15 12:40:03"

    def test_if_scheduler_stops(self):
        def say_hello():
            print("hello")

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 9, 15, 12, 30)
        agendador._sleep = lambda: sleep(0)

        agendador.start()
        data = datetime.datetime(2020, 9, 15, 12, 40, 3)
        agendador.schedule(say_hello, data)

        agendador.stop()

        assert len(agendador.tasks) == 0

    def test_if_scheduler_pauses(self):
        def say_hello():
            print("hello")

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 9, 15, 12, 30)
        agendador._sleep = lambda: sleep(0)

        agendador.start()
        data = datetime.datetime(2020, 9, 15, 12, 40, 3)
        agendador.schedule(say_hello, data)

        agendador.pause()

        assert len(agendador.tasks) == 1

    def test_daily_schedule(self):
        def say_hello():
            print("hello")

        scheduled_dates = []
        expected_dates = []

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 10, 1, 13, 30)
        agendador._sleep = lambda: sleep(0)

        agendador.start()
        data = datetime.datetime(2020, 10, 1, 13, 30, 3)

        expected_dates.append("2020-10-01 13:30:03")
        agendador.schedule_daily(say_hello, data)

        scheduled_dates.append(unix_time_to_string(agendador.tasks[0][0]))

        day_counter = 1
        while day_counter < 5:
            if (
                unix_time_to_string(agendador.tasks[0][0])
                != f"2020-10-0{day_counter} 13:30:03"
            ):
                day_counter += 1

                agendador._clock_args = datetime.datetime(2020, 10, day_counter, 13, 30)
                agendador._clock_tick = 0

                expected_dates.append(f"2020-10-0{day_counter} 13:30:03")
                scheduled_dates.append(unix_time_to_string(agendador.tasks[0][0]))

        agendador.stop()

        assert scheduled_dates == expected_dates

    def test_weekly_schedule(self):
        def say_hello():
            print("hello")

        scheduled_dates = []
        expected_dates = []

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 10, 1, 13, 30)
        agendador._sleep = lambda: sleep(0)

        agendador.start()
        data = datetime.datetime(2020, 10, 1, 13, 30, 3)

        expected_dates.append("2020-10-01 13:30:03")
        agendador.schedule_weekly(say_hello, data)

        scheduled_dates.append(unix_time_to_string(agendador.tasks[0][0]))

        day_counter = 1
        while day_counter < 15:
            if (
                unix_time_to_string(agendador.tasks[0][0])
                != f"2020-10-0{day_counter} 13:30:03"
            ):
                day_counter += 7

                agendador._clock_args = datetime.datetime(2020, 10, day_counter, 13, 30)
                agendador._clock_tick = 0

                if day_counter >= 10:
                    expected_dates.append(f"2020-10-{day_counter} 13:30:03")
                else:
                    expected_dates.append(f"2020-10-0{day_counter} 13:30:03")
                scheduled_dates.append(unix_time_to_string(agendador.tasks[0][0]))

        agendador.stop()

        assert scheduled_dates == expected_dates

    def test_montly_schedule(self):
        def say_hello():
            return "hello"

        scheduled_dates = []
        expected_dates = []

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 3, 15, 13, 30)
        agendador._sleep = lambda: sleep(0)

        agendador.start()
        data = datetime.datetime(2020, 3, 15, 13, 30, 3)

        expected_dates.append("2020-03-15 13:30:03")
        agendador.schedule_montly(say_hello, data)

        scheduled_dates.append(unix_time_to_string(agendador.tasks[0][0]))

        month_counter = 3

        while month_counter < 10:
            if (
                unix_time_to_string(agendador.tasks[0][0])
                != f"2020-{month_counter}-15 13:30:03"
            ):

                month_counter += 1

                agendador._clock_args = datetime.datetime(
                    2020, month_counter, 15, 13, 30, 30
                )
                agendador._clock_tick = 0

                if month_counter > 8:
                    expected_dates.append(f"2020-{month_counter+1}-15 13:30:03")
                else:
                    expected_dates.append(f"2020-0{month_counter+1}-15 13:30:03")

                sleep(0.1)
                scheduled_dates.append(unix_time_to_string(agendador.tasks[0][0]))

        agendador.stop()

        assert scheduled_dates == expected_dates
