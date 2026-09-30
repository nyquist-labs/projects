"""eelab — shared engine for the Nyquist Labs projects.

Every project follows one method:  PREDICT (closed-form theory) -> SIMULATE / MEASURE
(an independent numerical model, a real dataset, or an HDL simulator) -> COMPARE
(percentage error) -> EXPLAIN the discrepancy.
"""
import numpy as np
from numpy import pi, sqrt, exp, log, log10, sin, cos, tan, arctan2
from .core import Project, db, undb, find_crossing, pct_err, rng
from .plot import COLORS, C_PRED, C_MEAS, style_axes
__all__ = ["np", "pi", "sqrt", "exp", "log", "log10", "sin", "cos", "tan", "arctan2",
           "Project", "db", "undb", "find_crossing", "pct_err", "rng",
           "COLORS", "C_PRED", "C_MEAS", "style_axes"]
