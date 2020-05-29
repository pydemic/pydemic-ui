from . import components as ui
from . import plotting as plt
from .base import UIBaseProperty
from .sidebar import UISidebarProperty
from .utils import bind_function
from .. import st


class UIProperty(UIBaseProperty):
    """
    Property implementation for the <Model.ui> attribute.
    """

    module = st

    @property
    def sidebar(self):
        return UISidebarProperty(self._object)

    def params_summary(self):
        params = self._object.disease_params
        st.write({k: getattr(params, k) for k in params})

    # Charts
    hospitalizations_chart = bind_function(plt.hospitalizations_chart)
    available_beds_chart = bind_function(plt.available_beds_chart)
    deaths_chart = bind_function(plt.deaths_chart)

    # Other components
    summary_cards = bind_function(ui.summary_cards)
    summary_table = bind_function(ui.summary_table)
    epidemiological_parameters = bind_function(ui.epidemiological_parameters)
    ppe_demand_table = bind_function(ui.ppe_demand_table)
