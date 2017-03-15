"""plotters module of the psy-strat psyplot plugin

This module defines the plotters for the psy-strat package.
"""
from psyplot.plotter import Formatoption, Plotter


# -----------------------------------------------------------------------------
# ---------------------------- Formatoptions ----------------------------------
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# ------------------------------ Plotters -------------------------------------
# -----------------------------------------------------------------------------


class StratPlotter(Plotter):

    _rcparams_string = ['plotter.strat.']
