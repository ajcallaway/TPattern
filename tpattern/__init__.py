"""tpattern — an auditable, open-source reimplementation of Magnusson's THEME
T-pattern detection, built to reproduce (and stress-test) THEME 8 results.

Reference: Magnusson, M. S. (2000). Discovering hidden time patterns in
behavior: T-patterns and their detection. Behavior Research Methods,
Instruments, & Computers, 32(1), 93-110.
"""

from .io import Observation, read_observation, read_sample, read_table
from .pattern import Instance, Pattern
from .ci import find_critical_interval, CIResult
from .detect import Config, Engine
from .randomise import run_null, NullResult, rotate, shuffle
from .significance import calibrate, CalibrationResult
from .report import patterns_table, forest_plot, report
from .viz import pattern_dendrogram, patterns_overview
from .advisor import recommend
from .methods import methods_text

__version__ = "0.1.0"

__all__ = [
    "Observation", "read_observation", "read_sample", "read_table",
    "Instance", "Pattern",
    "find_critical_interval", "CIResult",
    "Config", "Engine",
    "run_null", "NullResult", "rotate", "shuffle",
    "calibrate", "CalibrationResult",
    "patterns_table", "forest_plot", "report",
    "pattern_dendrogram", "patterns_overview",
    "recommend", "methods_text",
]
