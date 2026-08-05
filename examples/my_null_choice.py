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
print("\nwrote null_comparison.png  (core = survives both nulls; shell = rotation only)")
