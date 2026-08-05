"""
Starting points students can copy and adapt.
=============================================

The tutorial teaches the method on the worked example; this gives a learner a clean
template for their *own* data. `new_analysis()` writes a heavily commented starter
script, with every line to change marked and pointers to `explain()` for each setting.
Three flavours cover the common designs:

    new_analysis()                          # one group: detect, calibrate, report
    new_analysis(template="two_groups")     # compare two groups (odds ratios + forest plot)
    new_analysis(template="null_choice")    # core vs shell: which null a pattern survives

It is the "now do it on your own research" bridge.
"""

from __future__ import annotations

from pathlib import Path

_BASIC = '''\
"""
My T-pattern analysis.  (tpattern.new_analysis — copy and adapt.)

Point this at your own event table and run it. Every line to change is marked # <-- EDIT.
For any setting, see what it does, its range and the recommended value with:
    from tpattern import explain;  print(explain("min_lag"))
Your data: one row per event, with columns  observation, event, start
(which session/rally/bout the event belongs to, what happened, and when). See SCHEMA.md
and the tutorial paper for the full walk-through.
"""
from tpattern import read_table, recommend, Config, calibrate, report, explain

# 1. LOAD -----------------------------------------------------------------------
DATA_FILE = "my_events.csv"     # <-- EDIT: your event table (CSV)
TIME_UNIT = "ms"                # <-- EDIT: "s" or "ms", the unit of your start column
observations = read_table(DATA_FILE, time_unit=TIME_UNIT, report="all")
# read_table checks the file as it reads it and prints any problems by code (Appendix A).

# 2. INSPECT + RECOMMEND --------------------------------------------------------
# The advisor inspects your data and recommends the null, the minimum lag and the error
# control, each with its reason. Read it, then decide (you are not obliged to follow it).
print(recommend(observations))

# 3. CONFIGURE ------------------------------------------------------------------
# Start from the advisor's recommendation. To understand any setting, print its help:
#   print(explain("min_lag"))   print(explain("surrogate_null"))   print(explain("frequent_event_exclusion"))
cfg = Config(
    min_lag=1,          # <-- 1 requires a genuine time gap (recommended for frame-coded data); 0 = THEME-style
    freq_exclude=1.5,   # <-- set a very common event aside from pattern-building (kept in the counts)
    # everything else is left at sensible defaults; run explain() to see them
)
NULL = "profile"        # <-- "profile" tests coupling beyond each type's own timing (the usual choice)
B = 2000                # <-- surrogates: 200 to screen many patterns, 2000+ for a confirmatory claim

# 4. CALIBRATE + REPORT ---------------------------------------------------------
result = calibrate(observations, cfg, null=NULL, B=B, q_target=0.05)
report(result, "my_output", observations=observations, title="My analysis")

# my_output/ now holds the results table (patterns_table.csv, with monte_carlo_p, fdr_q and
# survives_fwer_holm), the pattern dendrograms, the temporal-signature plot, the event-type
# roles and connections tables, and a plain-text SUMMARY. Each pattern's "interpretation"
# column reads it in plain English. To understand a column:  print(explain("fdr_q"))
print("\\nDone. Open the my_output/ folder.")
'''

_TWO_GROUPS = '''\
"""
My T-pattern group comparison.  (tpattern.new_analysis(template="two_groups"))

Do patterns occur differently between two groups (winners vs losers, condition A vs B,
goals vs non-goals)? For each pattern this tests its occurrence between the groups
(Fisher's exact test, odds ratio with a 95% confidence interval) and draws a forest plot.
Lines to change are marked # <-- EDIT. Run explain("min_lag") etc. for any setting.
"""
import csv
from tpattern import read_table, Config, group_contrast, forest_plot

# 1. LOAD your events (one row per event: observation, event, start).
DATA_FILE = "my_events.csv"     # <-- EDIT
TIME_UNIT = "ms"                # <-- EDIT: "s" or "ms"
observations = read_table(DATA_FILE, time_unit=TIME_UNIT, report="all")

# 2. GROUP each observation. group_of maps an observation's name to its group label.
#    Easiest: a two-column CSV (observation,group). <-- EDIT the path and column names.
group_of = {row["observation"]: row["group"]
            for row in csv.DictReader(open("my_groups.csv"))}

# 3. CONTRAST: detect patterns and compare their occurrence between the two groups.
#    min_count drops patterns too rare to compare; raise it to be more conservative.
items = group_contrast(observations, group_of, Config(min_lag=1), min_count=5)

# 4. PLOT the odds ratios with 95% CIs (a point whose CI excludes 1 differs between groups).
forest_plot(items, "group_contrast.png", title="Pattern occurrence: group comparison")
print("wrote group_contrast.png (odds ratios with 95% confidence intervals)")
'''

_NULL_CHOICE = '''\
"""
My null-choice comparison.  (tpattern.new_analysis(template="null_choice"))

Which patterns are genuine coupling, and which are just shared timing? This calibrates
your data under two nulls and splits the survivors into the CORE (survives both nulls =
coupling beyond each event's own timing) and the SHELL (survives the rotation null only =
co-occurrence driven by shared timing). Lines to change are marked # <-- EDIT.
"""
from tpattern import read_table, Config, compare_nulls, null_comparison_plot

DATA_FILE = "my_events.csv"     # <-- EDIT
TIME_UNIT = "ms"                # <-- EDIT: "s" or "ms"
observations = read_table(DATA_FILE, time_unit=TIME_UNIT, report="all")

# Compare the profile-preserving null (coupling) against the rotation null (any structure).
# B = 2000 gives a fine Monte-Carlo p; use 200 to explore quickly first.
cmp = compare_nulls(observations, Config(min_lag=1), nulls=("profile", "rotation"), B=2000)
print(cmp)   # lists the core and the shell, with each pattern's q under each null

null_comparison_plot(cmp, "null_comparison.png")
print("\\nwrote null_comparison.png  (core = survives both nulls; shell = rotation only)")
'''

TEMPLATES = {"basic": _BASIC, "two_groups": _TWO_GROUPS, "null_choice": _NULL_CHOICE}
_DEFAULT_NAME = {"basic": "my_analysis.py", "two_groups": "my_group_comparison.py",
                 "null_choice": "my_null_choice.py"}

# kept for backward compatibility (0.1.12 exported TEMPLATE)
TEMPLATE = _BASIC


def new_analysis(path: str | Path | None = None, *, template: str = "basic",
                 overwrite: bool = False) -> str:
    """Write a copy-and-adapt analysis template to `path`. Returns the path written.

    `template` is one of ``"basic"`` (one group), ``"two_groups"`` (compare two groups),
    or ``"null_choice"`` (core vs shell). If `path` is omitted a sensible filename is used.

    >>> from tpattern import new_analysis
    >>> new_analysis()                          # writes ./my_analysis.py
    >>> new_analysis(template="two_groups")     # writes ./my_group_comparison.py
    """
    if template not in TEMPLATES:
        raise ValueError(f"template must be one of {sorted(TEMPLATES)}, got {template!r}")
    p = Path(path) if path is not None else Path(_DEFAULT_NAME[template])
    if p.exists() and not overwrite:
        raise FileExistsError(f"{p} already exists; pass overwrite=True to replace it.")
    p.write_text(TEMPLATES[template])
    return str(p)
