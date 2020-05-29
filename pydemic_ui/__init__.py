"""
Pydemic Web interface
"""
__author__ = "Fábio Mendes"
__version__ = "0.1.0"

from . import model
from . import st
from . import ui
from .i18n import run
from .region import patch_region

patch_region()
run()
del run, patch_region
