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
