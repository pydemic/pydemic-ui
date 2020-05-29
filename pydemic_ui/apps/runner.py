"""
Apps initialized from runner are slightly more efficient since it prevents
costs related to model parsing and initialization.
"""
import importlib
import os

app = os.environ.get("PYDEMIC_APP", "calc")
mod = importlib.import_module(f"pydemic_ui.apps.{app}")
mod.main()
