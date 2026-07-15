# Changelog

## 0.1.0 — 2026-07-15

Initial public release.

- **Detection** — faithful reimplementation of the T-pattern algorithm (Magnusson,
  2000): critical-interval test (binomial tail on the NX/T baseline), largest-
  significant-interval free search, greedy one-to-one occurrence matching,
  distinct-token rule, completeness competition, bottom-up hierarchy. Validated
  against fixed occurrence counts.
- **Calibration** — profile-preserving and rotation/shuffle surrogate nulls; per-
  pattern Monte-Carlo empirical p-values; Benjamini–Hochberg FDR and Holm FWER,
  stratified by level.
- **Concurrency** — `min_lag` separates genuine temporal sequence from same-
  timestamp co-occurrence.
- **Diagnostics & advisor** — conditional-uniformity checks; a `recommend()`
  helper that inspects the data and suggests null / min-lag / error-control choices.
- **Reporting** — results tables (with corrected p-values), pattern dendrograms,
  effect-size forest plots, and a one-call `report()`.
- **Input** — a single canonical flat event table via `read_table()`; integrates
  with OpenTag.Studio as a tagging front-end.
- **Synthetic** — ground-truth generators for power / false-positive validation.
