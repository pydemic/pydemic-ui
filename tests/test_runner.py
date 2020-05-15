import pickle

import pandas as pd

from pydemic_ui import runner


class TestRunner:
    def test_can_pickle_and_unpickle_runners(self):
        date = pd.to_datetime("2020-01-01")
        r1 = runner.simple_runner()
        r2 = runner.R0_rate_runner(date, 0.5)
        r3 = runner.relax_intervention_runner(date, 0.7, 0.3)

        for r in [r1, r2, r3]:
            dump = pickle.dumps(r)
            assert pickle.loads(dump) == r
