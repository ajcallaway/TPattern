# The analysis pipeline: read -> advise -> calibrate -> table / report ---------

#' Read an event table into tpattern
#'
#' Reads your events (one row per event) and runs tpattern's forgiving import,
#' which checks the file as it reads it and reports, in plain language, anything
#' wrong — rather than silently dropping rows.
#'
#' @param data Either a path to a CSV file, or an R `data.frame`. A data.frame is
#'   written to a temporary CSV and read back through the same validated path, so
#'   you get the same data checks either way.
#' @param time_unit Unit of your `start` column: `"ms"` (milliseconds, typical
#'   for frame-coded video) or `"s"` (seconds).
#' @param observation,event,start,end Names of the columns in *your* data. The
#'   defaults are the canonical names; override if your export differs (for
#'   example `start = "Start Time"`). `end` is optional.
#' @param sep Field separator for a CSV path (default `","`).
#' @param ... Further arguments passed to the Python `read_table()` (for example
#'   `obs_start`, `obs_end`, `build_event_from`).
#' @return A `tpattern_events` object to pass to [advise()] and
#'   [calibrate_patterns()].
#' @examples
#' \dontrun{
#' ev <- read_events("my_events.csv", time_unit = "ms")
#' # or from a data.frame already in R:
#' df <- data.frame(observation = "match1", event = c("cross", "shot"),
#'                  start = c(1000, 1200))
#' ev <- read_events(df, time_unit = "ms")
#' }
#' @export
read_events <- function(data, time_unit = c("ms", "s"),
                        observation = "observation", event = "event",
                        start = "start", end = "end", sep = ",", ...) {
  time_unit <- match.arg(time_unit)
  path <- if (is.data.frame(data)) {
    f <- tempfile(fileext = ".csv")
    utils::write.csv(data, f, row.names = FALSE, na = "")
    f
  } else if (is.character(data) && length(data) == 1L) {
    # Expand "~" and relative paths here: R understands them, but the Python
    # reader we hand the path to does not.
    data <- path.expand(data)
    if (!file.exists(data)) stop("File not found: ", data, call. = FALSE)
    data
  } else {
    stop("`data` must be a data.frame or a single path to a CSV file.",
         call. = FALSE)
  }
  obs <- tp()$read_table(path, observation = observation, event = event,
                         start = start, end = end, time_unit = time_unit,
                         sep = sep, ...)
  structure(list(py = obs), class = "tpattern_events")
}

#' Ask the advisor what settings to use (it recommends, you decide)
#'
#' The advisor inspects your data and recommends the analysis settings — which
#' surrogate null, whether to require a genuine inter-event lag, and which error
#' control — each with the reason it applies to *your* data. It advises; the
#' decision stays yours.
#'
#' By default the full, plain-text interpretation is printed. The same content
#' is also returned as a data.frame you can inspect or store, with the ready-to
#' -adapt Methods paragraph attached.
#'
#' @param events A `tpattern_events` object from [read_events()].
#' @param min_count Minimum occurrences of an event type before it is used in the
#'   data diagnostics (default 15).
#' @param uniformity_alpha Significance level for the within-type uniformity
#'   check that drives the null recommendation (default 0.05).
#' @param quiet If `TRUE`, do not print the interpretation (still returned).
#' @return Invisibly, a `data.frame` with one row per recommended setting
#'   (`setting`, `recommended`, `reason`, `plain`). `attr(x, "methods_text")`
#'   holds a Methods paragraph and `attr(x, "notes")` any extra notes.
#' @examples
#' \dontrun{
#' ev  <- read_events("my_events.csv", time_unit = "ms")
#' adv <- advise(ev)                 # prints the interpretation
#' adv                               # the structured table
#' cat(attr(adv, "methods_text"))    # paste-ready methods sentence(s)
#' }
#' @export
advise <- function(events, min_count = 15L, uniformity_alpha = 0.05,
                   quiet = FALSE) {
  rec <- tp()$recommend(.obs(events), min_count = as.integer(min_count),
                        uniformity_alpha = uniformity_alpha)
  if (!quiet) {
    # py_str() gives the library's own plain-text view: each setting, its
    # recommended value, and the wrapped reason. This is the "interpretation".
    cat(reticulate::py_str(rec), "\n", sep = "")
  }
  # Structured pull-through: one tidy row per recommended setting. reticulate
  # imports the module with convert = TRUE, so rec$choices is already an R list
  # (of Choice handles) and rec$notes an R vector -- no py_to_r/iterate needed.
  choices <- lapply(rec$choices, function(ch) list(
    setting     = ch$option,
    recommended = ch$recommended,
    reason      = ch$rationale,
    plain       = ch$plain
  ))
  df <- .rows_to_df(choices)
  attr(df, "methods_text") <- rec$methods_text()
  attr(df, "notes") <- tryCatch(as.character(unlist(rec$notes)),
                                error = function(e) character(0))
  attr(df, "recommendation") <- rec
  invisible(df)
}

#' Detect T-patterns and calibrate each one against chance
#'
#' The main analysis call. It runs the detection for you (you do not call a
#' separate detect step) and tests every detected pattern against a surrogate
#' null, correcting the p-values for repeated testing.
#'
#' @param events A `tpattern_events` object from [read_events()].
#' @param null Surrogate null: `"profile"` (profile-preserving — tests coupling
#'   beyond each type's own timing; the usual choice) or `"rotation"`.
#' @param B Number of surrogate datasets. Use ~200 to screen many patterns,
#'   2000+ for a confirmatory claim (the empirical p cannot fall below
#'   1/(B+1), so B must clear your alpha).
#' @param min_lag Minimum inter-event lag, in frames. `1` requires a genuine gap
#'   (recommended for frame-coded video: co-timed events are co-occurrence, not
#'   sequence); `0` reproduces THEME's behaviour. The advisor recommends this.
#' @param freq_exclude Optional: set a near-ubiquitous event type aside from
#'   *building* patterns (it is still counted). Mean occurrences per observation
#'   above which a type is excluded.
#' @param min_occurrence Optional: fewest times a chain must recur to be kept.
#' @param q_target False-discovery-rate target for screening (default 0.05).
#' @param alpha Per-interval significance for detection (default 0.005).
#' @param seed Random seed, fixed so runs are reproducible (default 20260714).
#' @return A `tpattern_calibration` object; pass it to [results_table()],
#'   [tpattern_report()] and [tpattern_methods()].
#' @examples
#' \dontrun{
#' ev  <- read_events("my_events.csv", time_unit = "ms")
#' cal <- calibrate_patterns(ev, null = "profile", B = 2000, min_lag = 1)
#' results_table(cal)
#' }
#' @export
calibrate_patterns <- function(events, null = "profile", B = 200L, min_lag = 1L,
                               freq_exclude = NULL, min_occurrence = NULL,
                               q_target = 0.05, alpha = 0.005, seed = 20260714L) {
  cfg_args <- list(min_lag = as.integer(min_lag))
  if (!is.null(freq_exclude))   cfg_args$freq_exclude   <- freq_exclude
  if (!is.null(min_occurrence)) cfg_args$min_occurrence <- as.integer(min_occurrence)
  config <- do.call(tp()$Config, cfg_args)
  result <- tp()$calibrate(.obs(events), config, null = null,
                           B = as.integer(B), alpha = alpha,
                           q_target = q_target, seed = as.integer(seed))
  structure(list(result = result, config = config, events = .obs(events)),
            class = "tpattern_calibration")
}

#' The results table as a data.frame
#'
#' One row per calibrated pattern, with the readable columns `monte_carlo_p`,
#' `fdr_q`, `survives_fwer_holm`, `bout_support`, the observed timing and a
#' plain-English `interpretation`. Prevalence is reported, not filtered on, so
#' you can apply whatever support threshold you judge appropriate.
#'
#' @param x A `tpattern_calibration` from [calibrate_patterns()].
#' @param ci_unit Time unit for the reported critical intervals (default `"ms"`).
#' @return A `data.frame`, sorted by Monte-Carlo p.
#' @export
results_table <- function(x, ci_unit = "ms") {
  res <- if (inherits(x, "tpattern_calibration")) x$result else x
  # Already converted to an R list of named lists (convert = TRUE).
  rows <- tp()$patterns_table(res, ci_unit = ci_unit)
  .rows_to_df(rows)
}

#' Write a full report folder (tables, dendrograms, methods paragraph)
#'
#' @param x A `tpattern_calibration` from [calibrate_patterns()].
#' @param outdir Directory to write into (created if needed).
#' @param title Title used in the report.
#' @param ci_unit Time unit for critical intervals (default `"ms"`).
#' @return Invisibly, a character vector of the file paths written.
#' @export
tpattern_report <- function(x, outdir, title = "T-pattern report", ci_unit = "ms") {
  stopifnot(inherits(x, "tpattern_calibration"))
  paths <- tp()$report(x$result, outdir, ci_unit = ci_unit, title = title,
                       observations = x$events)
  invisible(paths)
}

#' A ready-to-paste Methods paragraph for your analysis
#'
#' @param x A `tpattern_calibration` from [calibrate_patterns()].
#' @return A character string stating every setting used and what it does,
#'   grounded in your data.
#' @export
tpattern_methods <- function(x) {
  stopifnot(inherits(x, "tpattern_calibration"))
  tp()$methods_text(x$config, observations = x$events, calibration = x$result)
}

#' Compare pattern occurrence between two groups
#'
#' For each pattern, tests whether it occurs in a different proportion of
#' observations between two groups (Fisher's exact test, odds ratio + 95% CI).
#'
#' @param events A `tpattern_events` object from [read_events()].
#' @param group Either a named character vector mapping each observation name to
#'   its group label, or a `data.frame` with columns `observation` and `group`.
#' @param min_lag Minimum inter-event lag in frames (see [calibrate_patterns()]).
#' @param min_count Drop patterns occurring in fewer than this many observations
#'   before comparing (default 5).
#' @return A `data.frame`, one row per pattern, with per-group counts, odds
#'   ratio, 95% CI, Fisher p, and which group it favours.
#' @export
compare_groups <- function(events, group, min_lag = 1L, min_count = 5L) {
  if (is.data.frame(group)) {
    if (!all(c("observation", "group") %in% names(group))) {
      stop("A data.frame `group` needs columns 'observation' and 'group'.",
           call. = FALSE)
    }
    group_of <- stats::setNames(as.character(group$group),
                                as.character(group$observation))
  } else if (!is.null(names(group))) {
    group_of <- stats::setNames(as.character(group), names(group))
  } else {
    stop("`group` must be a named vector (observation -> group) or a data.frame ",
         "with 'observation' and 'group' columns.", call. = FALSE)
  }
  py_map <- reticulate::dict(as.list(group_of))
  config <- tp()$Config(min_lag = as.integer(min_lag))
  rows <- tp()$group_contrast(.obs(events), py_map, config,
                              min_count = as.integer(min_count))
  .rows_to_df(rows)
}

#' Explain a setting or an output column, in plain language
#'
#' @param name A setting or column name (e.g. `"min_lag"`, `"fdr_q"`). `NULL`
#'   prints them all.
#' @return Invisibly `NULL`; called for the printed explanation.
#' @examples
#' \dontrun{
#' explain("min_lag")
#' explain("fdr_q")
#' }
#' @export
explain <- function(name = NULL) {
  cat(tp()$explain(name), "\n", sep = "")
  invisible(NULL)
}

#' Run the whole analysis in one call
#'
#' Convenience wrapper that reads your events, prints what the advisor
#' recommends, calibrates every pattern against chance, writes a report folder,
#' and returns the results table — the same steps as the commented starter
#' script from [new_analysis()], in one line.
#'
#' The advisor's recommendation is always shown so you can see whether the
#' settings suit your data; the defaults here (`min_lag = 1`, `null = "profile"`)
#' are the ones it recommends for frame-coded event data. Override them if the
#' advisor, or your judgement, points elsewhere.
#'
#' @param data A CSV path or a `data.frame` (see [read_events()]).
#' @param time_unit `"ms"` or `"s"` (see [read_events()]).
#' @param outdir Directory for the report (default `"tpattern_output"`).
#' @param null,B,min_lag,q_target Passed to [calibrate_patterns()].
#' @param title Report title.
#' @param quiet Suppress the advisor print-out and progress messages.
#' @return Invisibly, a list with `advice`, `table`, `calibration` and `paths`.
#' @examples
#' \dontrun{
#' out <- tpattern_analysis("my_events.csv", time_unit = "ms")
#' out$table
#' }
#' @export
tpattern_analysis <- function(data, time_unit = "ms", outdir = "tpattern_output",
                              null = "profile", B = 200L, min_lag = 1L,
                              q_target = 0.05, title = "My analysis",
                              quiet = FALSE) {
  events <- read_events(data, time_unit = time_unit)
  if (!quiet) message("\n--- What the advisor recommends (it advises; you decide) ---")
  advice <- advise(events, quiet = quiet)
  cal <- calibrate_patterns(events, null = null, B = B, min_lag = min_lag,
                            q_target = q_target)
  tbl <- results_table(cal)
  paths <- tpattern_report(cal, outdir, title = title)
  if (!quiet) {
    message(sprintf("\nDetected %d calibrated pattern(s). Wrote %d file(s) to '%s/'.",
                    nrow(tbl), length(paths), outdir))
    message("The results table is returned (element $table); ",
            "tpattern_methods() gives a paste-ready Methods paragraph.")
  }
  invisible(list(advice = advice, table = tbl, calibration = cal, paths = paths))
}

# Print methods ----------------------------------------------------------------

#' @export
print.tpattern_events <- function(x, ...) {
  n <- tryCatch(length(x$py), error = function(e) NA)
  cat(sprintf("<tpattern events: %s observation(s)> - pass to advise() or calibrate_patterns()\n", n))
  invisible(x)
}

#' @export
print.tpattern_calibration <- function(x, ...) {
  cat("<tpattern calibration> - use results_table(), tpattern_report(), tpattern_methods()\n")
  invisible(x)
}
