# Changelog

## 0.1.2 — 2026-07-19

Correctness and transparency pass following external maths-panel review. The
detection changes alter the reported pattern counts (fewer, because perfectly
dependent duplicates are now collapsed); the headline calibrated result is
unchanged.

- **De-duplication of occurrence-equivalent patterns** (`collapse_equivalent`,
  default on) — patterns sharing the same occurrence set (the two directions of a
  co-timed pair, or different bracketings of one chain) are collapsed to a single
  representative before counting and before multiple-comparison correction, so the
  family reflects distinct hypotheses rather than perfectly-dependent duplicates.
  Applied once at the end of `detect()`, so real and surrogate detections collapse
  identically and calibration stays consistent.
- **Deterministic surrogate seeding** — `run_null` now derives its per-method seed
  from a fixed offset (`rotation`/`shuffling`) instead of a salted `hash()`, so runs
  are reproducible across processes.
- **Advisor** — `recommend()` now advises the full data-driven set (frequent-event
  exclusion, minimum occurrence, surrogate null, minimum lag, error-rate control,
  number of surrogates B), each with its rationale and the impact of changing it.
- **Documentation** — every editable setting now carries its mathematical reason and
  the effect of changing it, in the `Config`/`calibrate` docstrings and in the paper's
  settings reference. Family-wise α default (0.005) documented.
- **Fixes** — profile-surrogate probability clamped to [0, 1]; dead code removed;
  `methods_text` version now sourced from the package version (no skew).

## 0.1.1 — 2026-07-16

- Packaging and metadata for the PyPI release (`pip install tpattern`): classifiers,
  project URLs, Zenodo archive DOI. No functional change to detection or calibration.

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
