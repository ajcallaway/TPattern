# =============================================================================
# My T-pattern analysis  (tpattern for R — copy this and adapt it)
# =============================================================================
#
# WHAT THIS DOES, AND WHY
# -----------------------
# It finds recurring temporal patterns in a sequence of timed, labelled events
# (behaviour, sport, clinical or physiological logs, interaction data) and tests
# each one against chance. The heavy lifting is done by the tpattern engine; this
# script is just the friendly, commented walk-through you edit for your own data.
#
# The analysis is five steps:
#   1. LOAD      your events, with automatic data checks in plain English
#   2. ADVISE    the advisor inspects your data and recommends the settings, with
#                reasons — it advises, YOU decide
#   3. CONFIGURE the analysis (start from the advice; comments explain each knob)
#   4. CALIBRATE detect the patterns and test every one against chance
#   5. REPORT    a results table, a folder of figures, and a Methods paragraph
#
# Every line you might change is marked with:  # <-- EDIT
# To understand any setting or output column, ask the code:  explain("min_lag")
# =============================================================================

library(tpattern)

# --- 0. SETUP (first run only) -----------------------------------------------
# tpattern's engine is a Python package that R drives for you. The first time,
# install it once — this sets up a Python environment for you, no terminal
# needed. After that, this block does nothing.
if (!tpattern_available()) {
  install_tpattern()
  stop("Python 'tpattern' was just installed. Please RESTART R, then run this ",
       "script again.")
}

# --- 1. LOAD -----------------------------------------------------------------
DATA_FILE <- "my_events.csv"   # <-- EDIT: path to your event table (one row per event)
TIME_UNIT <- "ms"              # <-- EDIT: "ms" (video frames) or "s" (seconds)
# Your file needs three columns: observation, event, start
#   observation = which session / rally / match the event belongs to
#   event       = what happened (the label)
#   start       = when it happened (in TIME_UNIT)
# If your columns are named differently, pass e.g. start = "Start Time" below.
events <- read_events(DATA_FILE, time_unit = TIME_UNIT)
# read_events checks the file as it reads it and tells you, in plain language,
# about anything wrong — instead of silently dropping rows.

# --- 2. ADVISE (the advisor recommends; you decide) --------------------------
# This prints a short report: for each setting it gives the recommended value and
# the reason it applies to YOUR data. Read it, then choose in step 3. You are not
# obliged to follow it — it is guidance, not a verdict.
advice <- advise(events)
# `advice` is also a table you can inspect: advice$setting, advice$recommended,
# advice$reason. A ready-to-adapt Methods sentence is attached too:
#   cat(attr(advice, "methods_text"))

# --- 3. CONFIGURE ------------------------------------------------------------
# Start from the advisor's recommendation. To understand any of these, run e.g.
#   explain("min_lag");  explain("surrogate_null");  explain("frequent_event_exclusion")
MIN_LAG <- 1          # <-- EDIT: 1 requires a genuine time gap (recommended for
                      #     frame-coded video: co-timed events are co-occurrence,
                      #     not sequence). 0 reproduces THEME's behaviour.
NULL_MODEL <- "profile"  # <-- EDIT: "profile" tests coupling beyond each event
                         #     type's own timing (the usual choice); "rotation"
                         #     asks only whether any temporal structure exists.
B <- 200              # <-- EDIT: number of surrogate datasets. 200 screens many
                      #     patterns quickly (seconds); raise to 2000+ for a
                      #     confirmatory single-pattern claim (the p-value cannot
                      #     fall below 1/(B+1), so B must clear your threshold).

# --- 4. CALIBRATE ------------------------------------------------------------
# Detects the patterns AND tests each against the chosen null, with the p-values
# corrected for repeated testing. Reproducible: the seed is fixed inside.
cal <- calibrate_patterns(events, null = NULL_MODEL, B = B, min_lag = MIN_LAG,
                          q_target = 0.05)

# --- 5. REPORT ---------------------------------------------------------------
# The results table, one row per pattern. Key columns (ask explain() about any):
#   monte_carlo_p      = p-value against the surrogate null
#   fdr_q              = false-discovery-controlled q-value (use for screening)
#   survives_fwer_holm = passes the strict family-wise test (confirmatory claims)
#   bout_support       = fraction of observations the pattern occurs in
#   interpretation     = a plain-English reading of the row
patterns <- results_table(cal)
print(head(patterns, 20))     # <-- EDIT: show as many rows as you like

# Write the full report (table + dendrograms + a Methods paragraph) to a folder.
paths <- tpattern_report(cal, outdir = "tpattern_output", title = "My analysis")
message("Wrote ", length(paths), " file(s) to tpattern_output/.")

# A paste-ready Methods paragraph, stating every setting and what it does:
cat("\n", tpattern_methods(cal), "\n", sep = "")

# Save the table for your own plots / stats:
write.csv(patterns, "my_patterns.csv", row.names = FALSE)   # <-- EDIT: filename

# -----------------------------------------------------------------------------
# COMPARING TWO GROUPS?  (e.g. wins vs losses, condition A vs B)
# Give each observation a group label and test each pattern between the groups:
#
#   groups <- data.frame(observation = c("match1", "match2"),
#                        group       = c("win",    "loss"))
#   diff <- compare_groups(events, groups, min_lag = MIN_LAG)
#   print(head(diff))   # odds ratios with 95% CIs; a CI excluding 1 differs
# -----------------------------------------------------------------------------
