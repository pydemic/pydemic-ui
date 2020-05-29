from mundi import Region
from pydemic.region import RegionProperty, RegionT
from pydemic.utils import fmt
from . import st
from .i18n import _, __


class UiProperty(RegionProperty):
    """
    Implements the Region.ui property.
    """

    __slots__ = ()
    region: RegionT

    def region_summary(self, where=st):
        """
        Display basic information about region.
        """
        st = where
        region = self.region

        st.title(f"{region.name} ({region.id})")
        st.header(_("Basic information"))

        extra = {}
        if region.icu_capacity is not None:
            extra[_("ICU beds")] = fmt(region.icu_capacity)
        if region.hospital_capacity is not None:
            extra[_("Hospital beds")] = fmt(region.icu_capacity)

        st.cards({_("Population"): fmt(region.population), **extra})

    def epidemic_summary(self, disease=None, where=st, **kwargs):
        """
        Basic summary of epidemic variables.
        """
        region = self.region
        st = where

        curves = region.pydemic.epidemic_curve(disease, **kwargs)
        final = curves.index[-1]
        cases = curves.loc[final, "cases"]
        deaths = curves.loc[final, "deaths"]

        st.cards({_("Cases*"): fmt(cases), _("Deaths"): fmt(deaths)}, color="st-red")
        st.html(_("&ast; As measured at {date}.").format(date=final.strftime("%x")))

    def epidemic_curves(
        self, disease=None, title=__("Cases and deaths"), where=st, **kwargs
    ):
        """
        Return epidemic curves for region.
        """
        st = where
        region = self.region

        if title:
            st.subheader(str(title))

        ax = region.plot.cases_and_deaths(disease, **kwargs)
        st.pyplot(ax.get_figure())

    def weekday_rate(
        self, disease=None, title=__("Cases per weekday"), where=st, **kwargs
    ):
        """
        Show rate of notification by weekday.
        """
        st = where
        region = self.region

        if title:
            st.subheader(str(title))

        ax = region.plot.weekday_rate(disease, **kwargs)
        st.pyplot(ax.get_figure())


def patch_region():
    Region.ui = property(UiProperty)
