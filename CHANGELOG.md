# Changelog

## 0.1.11 — 2026-08-03

Report the temporal content, and a fuller default output set.

- **Observed timing is now reported for every pattern.** Each pattern occurrence has a
  start, end and duration (`end - start`); for a two-event pattern that is the lag from
  the first event to the second. `patterns_table` now carries `duration_median_ms`,
  `duration_iqr_ms` and `duration_range_ms`, the plain-English verdict states the median
  lag in words, and the dendrogram annotates each join with its **median** timing (with
  the critical interval shown smaller beneath). This is the temporal information the
  method computes but T-pattern reporting usually leaves buried — THEME exposes it only
  as an on-demand "Pattern Duration" export; here it is summarised and on by default, for
  significant and non-significant patterns alike, so a reader can weigh practical
  relevance themselves. No practical-importance threshold (MCID/MDC) is claimed; the
  descriptive timing and the statistical test are reported separately.
- **Units are labelled** everywhere (ms), fixing an interval printed without a unit.
- **New default tables**, reproducing the useful THEME "Generate Tables" exports but
  emitted by default: `pattern_durations()` (one row per occurrence), `event_type_roles()`
  (how often each type is first / inner / last in patterns), `connections()` (what follows
  what), and `data_summary()` (per-type counts, prevalence and rate before detection).
- **New figures**: `duration_plot()` (a pattern's temporal signature — the spread of its
  occurrence durations) and `occurrence_plot()` (when each event type occurs within its
  observation). Opt-in `interval_counts()` supports before/after-split phase analysis.
- **`report()` emits all of the above by default** (pass `observations=` for the data
  summary and occurrence plot).
- **Figures share a customisable style** (`tpattern.viz.STYLE`): colours, fonts, grid and
  resolution live in one dict a user can edit to restyle every plot without touching the
  plotting code.

## 0.1.10 — 2026-08-03

Read your own, un-cleaned data with plain-language feedback.

- **`read_table` now checks the data and explains what it finds.** Instead of silently
  dropping unusable rows, it runs a set of checks and reports, in plain language, what was
  found, how much of the file was affected (as a percentage), and how to fix it. Each check
  has a stable code: `E` codes stop the read (something must be fixed first) and raise the new
  **`DataFormatError`**; `W` codes are warnings (the data loads, but rows were left out or a
  label is ambiguous); `I` codes are information (nothing lost — e.g. the effective sample, a
  dominant event type, a high same-timestamp fraction). By default the report prints only when
  there is a warning or error to act on; pass `report="all"` to see the information notes too,
  or `report=False` to silence it. The clean-data path is unchanged, so existing analyses read
  byte-identically. A UTF-8 byte-order mark (Excel) is stripped automatically.
- **`DataFormatError`, `check_reference()` and `CHECKS`** are exported. `CHECKS` is the single
  registry the runtime messages and the tutorial's Appendix A are both generated from, so the
  paper and the software cannot drift apart.
- **`methods_text()` now reports the effective sample** — how many observations contained at
  least two events (and could host a pattern) alongside the number submitted — so a Methods
  statement cannot overstate what was analysed.

## 0.1.9 — 2026-07-28

`read_table` reads the schema it documents, with no arguments.

- **`end`, `obs_start`, `obs_end` now default to their conventional column names** (`"end"`,
  `"obs_start"`, `"obs_end"`) instead of `None`. A table that includes those columns — e.g.
  OpenTag.Studio's Research CSV export — is now read correctly by `read_table("file.csv")` with **no
  arguments**, including the real observation window (the `T = obs_end - obs_start` denominator of
  the NX/T baseline). Columns that are absent are ignored silently, so files without them fall back
  to the first/last event exactly as before, and passing explicit column names is unchanged.

## 0.1.8 — 2026-07-28

Read SOF-CODER / THEME data directly.

- **`read_sofcoder()`** — ingest a SOF-CODER / THEME `DATANAME, T, Events` data file (Jonsson et al.,
  2006). Each frame's comma-separated multi-criteria codes are exploded into co-timed events, each
  `DATANAME` becomes an `Observation`, and the `:` / `&` markers set the observation window (the NX/T
  denominator). The delimiter is auto-detected (tab or whitespace); an optional `frames_per_second`
  converts frames to milliseconds. This lets tpattern analyse data collected anywhere in the
  SOF-CODER/THEME ecosystem, not only newly-coded tables — complementing `read_table` (one row per
  event) for OpenTag, SportsCode and spreadsheet exports.

## 0.1.7 — 2026-07-27

Readability, and a clearer worked-example flow.

- **`recommend()` output reformatted.** `print(rec)` now prints each setting as its own block — the
  recommended value on its own line, the reason wrapped beneath it — instead of one run-on line. In
  notebooks (Colab/Jupyter), displaying the object (`rec` or `display(rec)`) renders a rich view with
  the **recommended value in bold** and the explanation in normal weight. The plain-text view stays
  markup-free so it can be pasted verbatim.
- `methods_text()` is unchanged (a clean single paragraph for pasting into a manuscript); wrap it
  with `textwrap.fill(...)` for on-screen reading.
- **Worked-example notebook reordered** so the settings drive the analysis: the settings panel now
  precedes the run, and the run, null comparison, and bout-support steps all consume the settings you
  set. Change a setting and re-run to watch the result — including the dendrogram — change.

## 0.1.6 — 2026-07-27

Bug fix.

- **Fix `report()` crash on a single composite pattern.** `patterns_overview` passed a NumPy axes
  array to `pattern_dendrogram` when exactly one composite pattern was present (with a two-column
  grid, `plt.subplots` returns an array even for one plot), raising
  `AttributeError: 'numpy.ndarray' object has no attribute 'plot'`. Now flattens the axes robustly.
  This affected the quickstart and any `report()` call whose calibrated set had one composite.

## 0.1.5 — 2026-07-24

Null comparison: run profile and rotation together and report the difference.

- **`compare_nulls()`** — calibrate one sample under several surrogate nulls and decompose the
  survivors into a *core* (patterns surviving every null: coupling beyond each event type's own
  timing) and, for the profile-vs-rotation pair, a *shell* (rotation-only patterns: co-occurrence
  driven by shared timing, not coordination). The difference between the nulls is the reported
  result, not either null alone. Returns a `NullComparison` (print for a table, or use `.rows()`,
  `.common`, `.unique`).
- **`null_comparison_plot()`** — a grid of which nulls each pattern survives, so the difference
  reads at a glance.
- **advisor** — the null recommendation now states the two questions the nulls answer (rotation:
  is there any temporal structure?; profile: coupling beyond each type's own timing?), so the
  choice is question-driven as well as data-driven.
- **`examples/reproduce_worldcup.py`** — adds the settings-sensitivity table (Table 6) under
  `--calibrate`: the raw count swings with settings while the calibrated headline does not.

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
