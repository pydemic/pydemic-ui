import pytest

from pydemic_ui import info


class TestUI:
    def test_something(self):
        return pytest.skip("Make tests!")

    def test_region_info(self):
        return pytest.skip("temporarely disabled")

        df = info.region_info("BR-DF")
        us = info.region_info("US")
        print(df)
        print(us)
        assert set(df) == {
            "age_pyramid",
            "age_distribution",
            "population",
            "seniors_population",
            "region",
        }
        assert 0
