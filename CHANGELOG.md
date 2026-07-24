# Changelog

## 0.1.4 — 2026-07-22

Correctness: same-instant duplicate handling, and a fully characterised THEME reproduction.

- **`collapse_duplicates`** (default on) — two records of one event type at an identical
  timestamp are collapsed to a single point. In the point process the detector is defined on, the
  unit is (type, time): two records at Δt = 0 occupy one point (no ordering information), and
  retaining both inflates that type's rate in the NX/T baseline without changing window occupancy.
  Collapsing is the treatment consistent with that baseline; it also matches THEME's import. Turn
  it off only where timestamps are coarse enough that same-instant, same-type events may be
  genuinely distinct. Reported by `methods_text()`.
- **Effect on results** — Level-0 event counts now reproduce THEME's exactly on the World Cup data
  (the one affected type was challenge_pressure). The headline calibrated result is unchanged
  (cross-to-goal N = 14, q = .006). Only same-instant-duplicate-adjacent descriptive counts shift.

## 0.1.3 — 2026-07-20

Prevalence is now reported rather than filtered on, and the generated Methods
statement covers every setting that can change a result.

- **Bout support reported** — `patterns_table()` gains `bouts` (distinct observations
  a pattern spans) and `bout_support` (that as a fraction of the sample). Support is a
  prevalence property, not a significance test, so the library reports it and leaves any
  threshold to the reader, who can then apply their own bar instead of trusting a
  pre-applied cut-off. `CalibrationResult` carries `n_observations` so support is
  computable; pass `n_observations=` when tabulating a plain list of patterns.
- **`support_profile()`** — ranked prevalence plot of the calibrated survivors, with
  optional threshold reference lines annotated by how many patterns each would delete.
  `highlight="text"` (or a list) colours patterns whose signature contains that text, so
  the "does a family of events cluster at one end?" question works on any labelling
  scheme; `color_by=` takes a callable for groupings a substring cannot express. Note a
  knee in this profile separates common from rare, not real from chance, so it is a
  prevalence profile and not a selection device.
- **`methods_text()` completed** — now reports `collapse_equivalent`,
  `include_univariate`, and the caps on hierarchy depth and candidate window boundaries,
  and states the reduction switches whether or not they are left at their defaults. The
  de-duplication step was previously omitted from the generated Methods statement even
  though it changes both the reported counts and the size of the correction family.
- **Fix** — `examples/support_sensitivity.py` read its input with the default time unit
  and no observation window, so on millisecond data with real windows it silently
  rescaled every lag and inferred T from the first and last event. It now takes
  `--time-unit`, `--obs-start` and `--obs-end`, reports what it loaded, and warns when
  the window is being inferred.

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
