#' tpattern: open, auditable T-pattern analysis in R
#'
#' An idiomatic R interface to the `tpattern` Python library. The detection
#' algorithm (critical-interval T-patterns; Magnusson, 2000) and all of the
#' statistics live in Python, so what you get in R matches the Python package,
#' the Colab notebooks and the published paper exactly — one source of truth,
#' no drift.
#'
#' The whole flow is four steps:
#' [read_events()] -> [advise()] (the advisor recommends settings, you decide)
#' -> [calibrate_patterns()] -> [results_table()] / [tpattern_report()].
#' Or run the lot in one call with [tpattern_analysis()], or write yourself a
#' commented starter script with [new_analysis()].
#'
#' First time only: run [install_tpattern()] to set up a Python environment R
#' can use.
#'
#' @keywords internal
"_PACKAGE"

# Internal package state: a lazily-bound handle to the Python `tpattern` module.
# We import with delay_load = TRUE so the R package loads even if Python has not
# been configured yet (the user can call install_tpattern() first).
.tp_state <- new.env(parent = emptyenv())

.onLoad <- function(libname, pkgname) {
  .tp_state$module <- reticulate::import("tpattern", delay_load = TRUE)
}

# Return the Python module, with a friendly, actionable error if it is missing.
# Every exported function goes through this, so the "you need to install it"
# message is shown once, consistently, wherever the user starts.
tp <- function() {
  if (!reticulate::py_module_available("tpattern")) {
    stop(
      "The Python 'tpattern' package is not available to R yet.\n",
      "Set it up once with:  install_tpattern()\n",
      "That creates (or reuses) a Python environment and pip-installs tpattern.\n",
      "See ?install_tpattern for options (e.g. a named conda/virtual env).",
      call. = FALSE
    )
  }
  .tp_state$module
}

# Accept either a `tpattern_events` wrapper (what read_events() returns) or a
# raw reticulate handle, and hand back the underlying Python observations object.
.obs <- function(x) if (inherits(x, "tpattern_events")) x$py else x

# Turn a list of rows (each a named R list, e.g. from a Python list-of-dicts)
# into a plain data.frame: union the columns, map Python None / missing to NA,
# and keep each column atomic where possible, else character. Base R only, so
# the package carries no extra dependency for a tibble.
.rows_to_df <- function(rows) {
  rows <- Filter(Negate(is.null), rows)
  if (!length(rows)) return(data.frame())
  cols <- unique(unlist(lapply(rows, names)))
  df <- data.frame(row.names = seq_along(rows))
  for (cn in cols) {
    vals <- lapply(rows, function(r) {
      v <- r[[cn]]
      if (is.null(v) || length(v) == 0) NA else v[[1]]
    })
    simple <- tryCatch(unlist(vals, use.names = FALSE), error = function(e) NULL)
    df[[cn]] <- if (!is.null(simple) && length(simple) == length(rows)) {
      simple
    } else {
      vapply(vals, function(v) as.character(v), character(1))
    }
  }
  df
}
