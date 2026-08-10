# One-time setup and version helpers -------------------------------------------

#' Install the Python `tpattern` package so R can use it
#'
#' Run this once. It pip-installs `tpattern` into a Python environment that
#' `reticulate` manages for you, so you never have to touch a terminal. If you
#' already keep a Python environment for R work, pass its name as `envname` and
#' it goes there instead.
#'
#' @param envname Optional name of a virtual or conda environment to install
#'   into. `NULL` (default) uses reticulate's automatically managed environment.
#' @param method Installation method passed to [reticulate::py_install()]:
#'   `"auto"` (default), `"virtualenv"` or `"conda"`.
#' @param gui Install the guided-panel extras (`tpattern[gui]`)? `TRUE` (default)
#'   matches the Python install used in the Colab notebooks. Set `FALSE` for the
#'   lean install if you only need the scripting functions.
#' @param ... Further arguments passed to [reticulate::py_install()].
#' @return Invisibly `TRUE` on success.
#' @examples
#' \dontrun{
#' install_tpattern()                 # simplest: managed environment
#' install_tpattern(envname = "r-tpattern", method = "virtualenv")
#' }
#' @export
install_tpattern <- function(envname = NULL, method = "auto", gui = TRUE, ...) {
  pkg <- if (isTRUE(gui)) "tpattern[gui]" else "tpattern"
  reticulate::py_install(packages = pkg, envname = envname, method = method,
                         pip = TRUE, ...)
  message("Installed the Python 'tpattern' package. Restart R if this is your ",
          "first Python setup, then you are ready to analyse.")
  invisible(TRUE)
}

#' Is the Python `tpattern` package available to R?
#'
#' @return `TRUE` if the Python package can be imported, `FALSE` otherwise.
#'   Handy at the top of a script to prompt [install_tpattern()] if needed.
#' @export
tpattern_available <- function() {
  isTRUE(reticulate::py_module_available("tpattern"))
}

#' Version of the underlying Python `tpattern` package
#'
#' @return The Python package version string (e.g. `"0.1.14"`). This is the
#'   version that actually did your analysis; cite it in your methods.
#' @export
tpattern_version <- function() {
  tp()$`__version__`
}
