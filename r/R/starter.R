#' Write a commented starter analysis script you can adapt
#'
#' Copies a heavily-commented R script into your working directory. It walks
#' through the whole analysis — load, advise, configure, calibrate, report — with
#' every line to change marked `# <-- EDIT` and pointers to [explain()] for each
#' setting. It is the "now do it on your own data" bridge: open it, change two
#' lines, and run it.
#'
#' @param path Where to write the script (default `"my_analysis.R"`).
#' @param overwrite Overwrite `path` if it already exists? Default `FALSE`.
#' @return Invisibly, the path written.
#' @examples
#' \dontrun{
#' new_analysis()                       # writes my_analysis.R
#' new_analysis("acl_study.R")
#' }
#' @export
new_analysis <- function(path = "my_analysis.R", overwrite = FALSE) {
  if (file.exists(path) && !overwrite) {
    stop(path, " already exists; pass overwrite = TRUE to replace it.",
         call. = FALSE)
  }
  src <- system.file("examples", "my_analysis.R", package = "tpattern")
  if (!nzchar(src)) {
    stop("Could not locate the bundled starter script. Is the package ",
         "installed correctly?", call. = FALSE)
  }
  ok <- file.copy(src, path, overwrite = overwrite)
  if (!ok) stop("Failed to write ", path, call. = FALSE)
  message("Wrote ", path,
          " - open it, change the two lines marked '# <-- EDIT', and run it.")
  invisible(path)
}
