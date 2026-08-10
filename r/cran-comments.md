## Test environments
* local: macOS, R 4.1.2
* (recommended before submitting: win-builder devel + release via devtools::check_win_devel())

## R CMD check results
0 errors | 0 warnings | 1 note

* This is a new submission.
* The CRAN incoming spell-check flags two words in DESCRIPTION: "Colab" (Google
  Colab, a product name) and "Magnusson" (the surname of the method's author,
  M. S. Magnusson). Both are spelled correctly.
* The one local NOTE, "unable to verify current time", is a clock/NTP quirk on the
  build machine and does not occur on CRAN's servers.

## Notes for the reviewer
* This package is a thin interface to the 'tpattern' Python library, called through
  'reticulate'. It requires no Python at build/check time: all examples are wrapped in
  \dontrun{}, and the tests skip when Python is unavailable (as on CRAN), so the package
  checks green without a Python installation. Python is declared in SystemRequirements and
  installed for the user by the exported install_tpattern() helper.
