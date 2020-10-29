from pydemic_ui.scheduler import *

class TestScheduler:

    def test_if_a_task_is_scheduled(self):

        def say_hello():
            print('hello')

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 9, 15, 12, 30)
        agendador._sleep = lambda: sleep(0)
        
        agendador.start()
        data = datetime.datetime(2020, 9, 15, 12, 40, 3)
        agendador.schedule(say_hello, data)

        agendador.pause()

        assert unix_time_to_string(agendador.tasks[0][0]) == '2020-09-15 12:40:03'

    def test_if_scheduler_stops(self):
        def say_hello():
            print('hello')

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
            print('hello')

        agendador = Scheduler()
        agendador._clock = datetime_to_time
        agendador._clock_args = datetime.datetime(2020, 9, 15, 12, 30)
        agendador._sleep = lambda: sleep(0)
        
        agendador.start()
        data = datetime.datetime(2020, 9, 15, 12, 40, 3)
        agendador.schedule(say_hello, data)

        agendador.pause()

        assert len(agendador.tasks) == 1
