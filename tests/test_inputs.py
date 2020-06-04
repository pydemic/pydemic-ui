import mundi
from pydemic.utils import today
from pydemic_ui.components import input
from pydemic_ui.runner import simple_runner
from pydemic_ui.st_logger import Driver, out, ask


class TestInput:
    def test_select_healthcare_params(self, en):
        br = mundi.region("BR")
        st = Driver(
            [
                out.header("Hospital capacity"),
                out.subheader("ICU beds"),
                ask.number_input[60_000](...),
                ask.number_input[30_000](...),
                ...,
                out.subheader("Clinical beds"),
                ask.number_input[500_000](...),
                ask.number_input[300_000](...),
                ...,
            ]
        )
        assert input.healthcare_params(br, where=st) == {
            "hospital_capacity": 200_000,
            "hospital_full_capacity": br.hospital_capacity,
            "icu_capacity": 30_000,
            "icu_full_capacity": br.icu_capacity,
        }

        assert st.is_empty()

    def test_select_region(self, en):
        st = Driver(
            [
                out.header("Location"),
                ask.selectbox["BR-1"](...),
                ask.selectbox["*BR-1"](...),
            ]
        )
        assert input.region_input("BR", where=st) == mundi.region("BR-1")
        assert st.is_empty()

    def test_simulation_params(self, en):
        br = mundi.region("BR")
        st = Driver(
            [
                out.header("Simulation options"),
                ask.slider[10](...),
                ask.date_input[today(10)](...),
                out.subheader("Cases"),
                ask.number_input[10](...),
                ask.slider[10](...),
            ]
        )
        assert input.simulation_params(br, where=st) == {
            "period": 70,
            "date": today(10),
            "daily_cases": 100,
        }
        assert st.is_empty()

    def test_epidemiological_params_simple(self, en):
        br = mundi.region("BR")
        st = Driver([out.header("Epidemiology"), ask.selectbox["std"](...)])
        assert input.epidemiological_params(br, where=st) == {}
        assert st.is_empty()

    def test_epidemiological_params_advanced(self, en):
        br = mundi.region("BR")
        st = Driver(
            [
                out.header("Epidemiology"),
                ask.selectbox["custom"](...),
                out.subheader(...),
                ask.slider[2.0](...),  # R0
                ask.slider[3.0](...),  # incubation period
                ask.slider[3.0](...),  # infectious period
                ask.slider[50](...),  # symptomatic cases
                out.subheader(...),
                ask.slider[5](...),  # prob_severe
                ask.slider[25](...),  # prob_critical
                ask.slider[10](...),  # hospitalization_period
                ask.slider[7](...),  # icu_period
            ]
        )
        assert input.epidemiological_params(br, where=st) == {
            "R0": 2.0,
            "severe_period": 10,
            "critical_period": 7,
            "incubation_period": 3.0,
            "infectious_period": 3.0,
            "prob_critical": 0.0125,
            "prob_severe": 0.05,
            "prob_symptoms": 0.5,
        }
        assert st.is_empty()

    def test_select_intervention_simple(self, en):
        br = mundi.region("BR")
        st = Driver([out.header("Intervention"), ask.selectbox["baseline"](...)])
        assert input.intervention_runner_input(br, where=st) == simple_runner()
        assert st.is_empty()
