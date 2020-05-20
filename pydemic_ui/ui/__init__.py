import sidekick as sk

from pydemic.models import Model
from .output_charts import (
    hospitalizations_chart,
    available_beds_chart,
    deaths_chart,
    population_info_chart,
)
from .output_components import (
    summary_cards,
    healthcare_parameters,
    epidemiological_parameters,
    ppe_demand,
)
from .ui_accessor import UI

Model.ui = sk.lazy(UI)
del sk, Model
