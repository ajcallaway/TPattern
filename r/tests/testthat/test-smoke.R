# These tests run everywhere. The ones that need the Python engine skip cleanly
# when it is not installed (e.g. on a fresh CRAN machine), so the package still
# checks green without a Python setup.

test_that("exported functions are present", {
  for (fn in c("install_tpattern", "tpattern_available", "read_events",
               "advise", "calibrate_patterns", "results_table",
               "tpattern_report", "tpattern_methods", "compare_groups",
               "explain", "new_analysis", "tpattern_analysis")) {
    expect_true(is.function(get(fn)), info = fn)
  }
})

test_that("new_analysis() writes the starter script", {
  skip_if_not(nzchar(system.file("examples", "my_analysis.R", package = "tpattern")))
  tmp <- file.path(tempdir(), "starter_test.R")
  on.exit(unlink(tmp), add = TRUE)
  new_analysis(tmp, overwrite = TRUE)
  expect_true(file.exists(tmp))
  expect_true(any(grepl("# <-- EDIT", readLines(tmp))))
})

test_that("read_events errors clearly on a missing file", {
  expect_error(read_events("definitely_not_a_file_12345.csv"),
               "not found", ignore.case = TRUE)
})

test_that("a minimal analysis runs when the Python engine is available", {
  skip_if_not(tpattern_available(), "Python 'tpattern' not installed")
  # Two short observations with a repeating X -> Y pair.
  df <- data.frame(
    observation = rep(c("a", "b"), each = 4L),
    event       = rep(c("X", "Y"), times = 4L),
    start       = c(0, 1, 2, 3, 0, 1, 2, 3)
  )
  ev <- read_events(df, time_unit = "s")
  expect_s3_class(ev, "tpattern_events")

  adv <- advise(ev, quiet = TRUE)
  expect_s3_class(adv, "data.frame")
  expect_true("recommended" %in% names(adv))

  cal <- calibrate_patterns(ev, B = 50L, min_lag = 1L)
  expect_s3_class(cal, "tpattern_calibration")
  expect_s3_class(results_table(cal), "data.frame")
  expect_type(tpattern_methods(cal), "character")
})
