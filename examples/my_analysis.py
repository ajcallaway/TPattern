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
print("\nDone. Open the my_output/ folder.")
