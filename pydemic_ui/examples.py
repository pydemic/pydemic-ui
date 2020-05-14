import mundi_healthcare as mhc
from pydemic.diseases import covid19
from pydemic.models import SEAIR
from . import info


def seir(run=120, region="BR", disease=covid19, **kwargs):
    """
    A simple SEIR example.
    """

    m = SEAIR(region=region, disease=disease, **kwargs)
    m.set_ic(cases=1e-6 * m.population)
    m.run(run)
    return m.clinical.overflow_model()


def seir_info(**kwargs):
    """
    Return the info dicto from given model.
    """

    m = seir(**kwargs)
    return info.full_info(m)
