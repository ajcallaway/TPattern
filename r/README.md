# tpattern (R)

An R interface to the [`tpattern`](https://github.com/ajcallaway/TPattern) Python
library — open, auditable T-pattern analysis (Magnusson, 2000). The detection
algorithm and statistics live in Python and are driven from R through
[`reticulate`](https://rstudio.github.io/reticulate/), so your results in R match
the Python package, the Colab notebooks and the published paper exactly. One
source of truth, no reimplementation to drift.

## Install

```r
# install.packages("remotes")
remotes::install_github("ajcallaway/TPattern", subdir = "r")

library(tpattern)
install_tpattern()   # once: sets up a Python environment R can use
# (restart R after the very first Python setup)
```

Once on CRAN:

```r
install.packages("tpattern")
```

## Do everything in one line

```r
library(tpattern)
out <- tpattern_analysis("my_events.csv", time_unit = "ms")
out$table            # the results, one row per pattern
```

`tpattern_analysis()` reads your events, **prints what the advisor recommends**,
calibrates every pattern against chance, writes a report folder, and returns the
table.

## Or step by step

```r
ev  <- read_events("my_events.csv", time_unit = "ms")  # forgiving import + checks
adv <- advise(ev)                    # advisor recommends settings, with reasons
cal <- calibrate_patterns(ev, null = "profile", B = 2000, min_lag = 1)
results_table(cal)                   # data.frame: monte_carlo_p, fdr_q, ...
tpattern_report(cal, "output")       # tables, dendrograms, methods paragraph
cat(tpattern_methods(cal))           # paste-ready Methods paragraph
explain("min_lag")                   # what any setting or column means
```

Prefer a script to adapt? `new_analysis()` writes a heavily-commented
`my_analysis.R` you edit and run.

Your data: one row per event, with columns `observation`, `event`, `start`
(and optional `end`) — see the main
[`SCHEMA.md`](https://github.com/ajcallaway/TPattern/blob/main/SCHEMA.md).

## Citation

Cite the software and the method — see the main repository's `CITATION.cff` and
README. The R interface calls the same engine, so cite the `tpattern` version
`tpattern_version()` reports.
