# tpattern — open, auditable analysis of recurring patterns in event sequences

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ajcallaway/TPattern/blob/main/colab/tpattern_guided_analysis.ipynb)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.21397543-1682D4.svg)](https://doi.org/10.5281/zenodo.21397543)
[![R interface](https://img.shields.io/badge/R-interface-276DC3?logo=r&logoColor=white)](#using-tpattern-from-r)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`tpattern` detects recurring temporal patterns (T-patterns; Magnusson, 2000) in
**any sequence of timed, labelled events** — behaviour, sport, clinical or
physiological logs, interaction data — validates them properly against chance, and
produces clean, publication-ready output (tables, figures, pattern dendrograms). It
implements the published T-pattern detection algorithm (Magnusson, 2000) as free,
auditable code — the same critical-interval method the THEME software applies (see
[The method it implements](#the-method-it-implements)) — and is the analysis
companion to the [OpenTag.Studio](https://opentag.studio) tagging tool.

## Three ways to use it

### 🚀 In your browser — Google Colab, no install, no coding

Open a guided notebook, upload your events CSV, and it walks you through four steps —
**upload → inspect → the recommended settings appear → run** — then hands back a full
report inline and as a downloadable zip: a colour-coded results table with a
plain-English verdict for every pattern (🟢 robust · 🟡 borderline · ⚪ likely chance),
the pattern dendrograms, the code to restyle them, and a paste-ready Methods paragraph.
No data of your own yet? Point it at [`data/worldcup_goals.csv`](data/worldcup_goals.csv)
(choose **ms** for the time unit).

Three notebooks (all in [`colab/`](colab/)):

- [**Guided analysis**](https://colab.research.google.com/github/ajcallaway/TPattern/blob/main/colab/tpattern_guided_analysis.ipynb) — **recommended.** Installs the latest `tpattern` from PyPI and opens the guided panel. This is the one the badge above opens.
- **Guided analysis (offline)** — the package source is bundled inside the notebook itself, so it runs standalone with nothing to install and nothing to download: use it on locked-down machines, behind restrictive networks, or anywhere `pip` is unavailable. The bundle is a snapshot of the source at the last release, so pin your citation to the version it reports. Open `colab/tpattern_guided_analysis_offline.ipynb` via **File → Upload notebook**.
- **Worked example** — the companion to the tutorial paper. Runs the load → inspect → recommend → calibrate → report walk-through on the shipped World Cup goal sequences, cell by cell, so you can follow the whole analysis and then swap in your own data (`colab/tpattern_worked_example.ipynb`).

### 🐍 As a Python library

`pip install tpattern` and script it — see [Getting started](#getting-started-in-a-minute), [Quickstart](#quickstart) and [`examples/`](examples/).

### 📊 From R

R users (common in psychology and behavioural science) can drive the **same
engine** via [`reticulate`](https://rstudio.github.io/reticulate/) — the algorithm
stays in Python, so results match exactly. Install with
`remotes::install_github("ajcallaway/TPattern", subdir = "r")`, then run the whole
analysis in one call: `tpattern_analysis("events.csv")`. See
[Using tpattern from R](#using-tpattern-from-r).

Bring your own data (one row per event — see [`SCHEMA.md`](SCHEMA.md)) or try the
included [`data/`](data/) example.

## Getting started in a minute

Install, generate a starter script, point it at your data, run it:

```bash
pip install tpattern
python -c "import tpattern; tpattern.new_analysis()"   # writes my_analysis.py
```

Open `my_analysis.py`, change the two lines marked `# <-- EDIT` (your file and its time
unit), and run `python my_analysis.py`. It loads your events, **checks the file and tells
you in plain language about any problem**, recommends the analysis settings with reasons,
calibrates every pattern against a chance model, and writes a folder of results with a
plain-English verdict for each pattern.

Doing something more specific? Generate a template for it:

```python
from tpattern import new_analysis
new_analysis()                        # one group: detect, calibrate, report
new_analysis(template="two_groups")   # compare two groups (odds ratios + forest plot)
new_analysis(template="null_choice")  # core vs shell: which null a pattern survives
```

Not sure what a setting means? Ask the code — every setting and output column is documented:

```python
from tpattern import explain
print(explain("min_lag"))    # what it does, its range, the recommended value, higher vs lower
print(explain("fdr_q"))      # what an output column means
```

## What you get

- **Forgiving data import.** `read_table` checks your file as it reads it and reports, in
  plain language, any problem, how much of the file it affects, and how to fix it — instead
  of silently dropping rows. Each check has a stable code (Appendix A of the tutorial; also
  [`PARAMETERS.md`](PARAMETERS.md)).
- **A proper chance model.** Every pattern is tested against a surrogate null, with p-values
  corrected for repeated testing (Benjamini–Hochberg FDR for screening,
  Benjamini–Yekutieli for dependence-robust FDR, Holm family-wise for confirmatory
  claims), stratified by hierarchy level.
- **Temporal reporting.** Beyond *which* patterns are real, the output says *when*: each
  pattern's occurrence timing (median lag and spread) is reported by default — on the
  dendrogram, in the table, and in the plain-English verdict — for every pattern.
- **Readable output.** Results-table columns are named for what they are (`monte_carlo_p`,
  `fdr_q`, `survives_fwer_holm`, `bout_support`, `duration_median_ms`), and each pattern
  carries a plain-English `interpretation`. `explain()` documents every setting and column;
  the full reference is in [`PARAMETERS.md`](PARAMETERS.md).
- **One reference, everywhere.** Settings and columns live in one registry that generates the
  code's `explain()`, `PARAMETERS.md`, the Colab form labels, and the tutorial's tables — so
  the software, the paper and the notebook can't drift apart.
- **Clean figures** — dendrograms, temporal signatures, forest plots — that share one
  customisable style (`tpattern.viz.STYLE`).

## The method it implements

T-pattern analysis (Magnusson, 1996, 2000, 2019) finds behaviourally meaningful
structure that event counts and simple transition tables miss: event types that
recur in the same order, separated by statistically consistent time intervals, more
often than chance predicts. `tpattern` implements the algorithm exactly as published,
in auditable code:

- **Critical-interval detection.** For an ordered pair of event types (A, B) it
  searches for the time window after A within which B follows more often than B's
  overall rate would predict. Significance is the **upper-tail binomial** probability
  of the observed number of A→B matches, evaluated against that baseline rate (B's
  occurrences spread over the observation length — the *NX/T* baseline), thresholded
  at α (default 0.005). This is the critical-interval test set out in Magnusson (2000)
  and the THEME manual.
- **Free search, one-to-one matching, distinct tokens.** A free search selects the
  largest significant interval; occurrences are matched one-to-one by the greedy
  procedure the algorithm specifies; a pattern must be built from distinct event
  tokens.
- **Bottom-up hierarchy with completeness competition.** Patterns are grown level by
  level, longer patterns competing with their sub-patterns so that only the most
  complete survive.

On top of the published detection, `tpattern` adds what the method has historically
lacked:

- **a proper chance model** — every detected pattern is tested against a surrogate
  null, with p-values **corrected for repeated testing** (Benjamini–Hochberg FDR
  for screening, Benjamini–Yekutieli where the p-values are dependent, Holm
  family-wise for confirmatory claims), stratified by level;
- **explicit concurrency handling** — events sharing a timestamp are reported as
  co-occurrence rather than sequence;
- **clear reporting** — tidy tables, effect sizes with confidence intervals,
  purposeful figures, and clean **dendrograms** of the detected patterns.

The reference software for this method is THEME (PatternVision Ltd), with **SOF-CODER**
(Jonsson et al., 2006) as its coding front end. `tpattern` reads that ecosystem
directly — `read_sofcoder` ingests SOF-CODER/THEME (`DATANAME, T, Events`) files — so
existing THEME datasets can be re-analysed with the surrogate calibration, and
[OpenTag.Studio](https://opentag.studio) can play, for `tpattern`, the role SOF-CODER
plays for THEME.

## Installation

```bash
pip install tpattern
```

Add the guided-wizard extras with `pip install tpattern[gui]`. To work from source
instead (for development or to run the reproduction scripts and shipped data):

```bash
git clone https://github.com/ajcallaway/TPattern.git
cd TPattern
pip install -e .
```

Requires Python ≥ 3.10 (depends on numpy, scipy, matplotlib).

## Quickstart

```python
from tpattern import read_table, Config, recommend, calibrate, report, methods_text

# 1. Load your events — one row per event (observation, event, start).
#    Pass time_unit="ms" if your times are in milliseconds (default is seconds).
#    See SCHEMA.md for the (simple) required format.
observations = read_table("events.csv", time_unit="s")

# 2. Let the tool inspect the data and recommend the method — which surrogate
#    null, whether to require a genuine lag, which error control — with reasons.
print(recommend(observations))

# 3. Detect and calibrate in one call: every pattern is tested against a
#    surrogate null with correction for repeated testing.
#    (calibrate() runs the detection for you — you don't call detect() first.)
result = calibrate(observations, Config(), null="profile", B=200, q_target=0.05)
survivors = result.kept("fdr")     # patterns that survive false-discovery control

# 4. Report: a tidy results table (monte_carlo_p, fdr_q, survives_fwer_holm, the observed
#    timing, and a plain-English `interpretation` per pattern), pattern dendrograms, the
#    temporal-signature and occurrence plots, the event-type roles/connections tables, and a
#    paste-ready Methods paragraph stating every setting and what it does.
report(result, "report_out", observations=observations, title="My analysis")
print(methods_text(Config(), observations=observations, calibration=result))
```

Prefer not to write the pipeline yourself? `python -c "import tpattern;
tpattern.new_analysis()"` writes a commented [`my_analysis.py`](examples/my_analysis.py)
you edit and run (see [Getting started](#getting-started-in-a-minute)).

Two runnable examples:

```bash
pip install -e .
python examples/quickstart.py          # no data needed (synthetic ground-truth demo)
python examples/reproduce_worldcup.py  # a real read_table + full analysis on shipped data
```

Just want the detected patterns without calibration? `Engine(observations,
Config()).detect()` returns them directly.

**Comparing two groups** (winner vs loser, goal vs non-goal, condition A vs B)?
`group_contrast(observations, group_of)` tests each pattern's occurrence between
the groups (Fisher's exact test, odds ratio + 95% CI) and feeds `forest_plot` — or run
`new_analysis(template="two_groups")` for a ready-made script.

## Using tpattern from R

R users (common in psychology and behavioural science) can drive the **same
engine** from R — the algorithm stays in Python, called through
[`reticulate`](https://rstudio.github.io/reticulate/), so results match this
package and the paper exactly. The R interface lives in [`r/`](r/):

```r
# install.packages("remotes")
remotes::install_github("ajcallaway/TPattern", subdir = "r")

library(tpattern)
install_tpattern()        # once: sets up a Python environment R can use

# the whole analysis in one call — prints what the advisor recommends,
# calibrates every pattern, writes a report, returns the table:
out <- tpattern_analysis("my_events.csv", time_unit = "ms")
out$table
```

Or step by step: `read_events()` → `advise()` (the advisor, pulled through in
full) → `calibrate_patterns()` → `results_table()` / `tpattern_report()`, with
`explain()` for any setting and `new_analysis()` to write a commented starter
script. See [`r/README.md`](r/README.md). (CRAN release to follow, then
`install.packages("tpattern")`.)

## The workflow

```
   tag events            export             analyse                    report
 (OpenTag / Sportscode) ──────▶ standard ──▶ tpattern ──▶ tables · figures · dendrograms
                                 table         (detect · validate ·
                                               calibrate)
```

1. **Tag** your video/events in any coding tool.
2. **Export** to the standard input structure — one row per event
   (`observation, event, start`, plus optional `end`, descriptor and group
   columns). See [`SCHEMA.md`](SCHEMA.md).
3. **Set up your coding** so the export is analysis-ready — one event per action,
   explicit outcomes, unit boundaries. See [`CODING_GUIDE.md`](CODING_GUIDE.md).
4. **Detect** T-patterns, **validate** them against a surrogate null with corrected
   significance (`recommend` advises the settings; `calibrate` runs it), and
   **report** (tables, dendrograms, and a `methods_text` Methods paragraph).

## Relationship to OpenTag.Studio

[OpenTag.Studio](https://opentag.studio) is a free, browser-based sports video
tagging tool. It is the natural front end for `tpattern`: tag your footage, export
a session, and analyse it here — no proprietary software anywhere in the pipeline.
OpenTag's **THEME & GSEQ setup guide** covers how to design a coding window so the
export is analysis-ready, and that guidance applies directly to `tpattern`
(`CODING_GUIDE.md` is the short bridge). Together they form a complete, open
tag → analysis pipeline.

## Reproducing the published results

The derived 2022 World Cup event sequences ship in [`data/`](data/), so the
published analyses reproduce from this repository alone:

```bash
python examples/reproduce_worldcup.py              # concordance, exclusion, concurrency (~5 s)
python examples/reproduce_worldcup.py --calibrate  # also the surrogate null (~10 min)
```

This regenerates the tpattern-vs-THEME pattern counts by level, the interception
exclusion divergence, the co-occurrence-vs-sequence analysis, and how many patterns
survive the surrogate null. All seeded and deterministic. See
[`data/README.md`](data/README.md) for provenance and how the data was derived.

## Documentation

- [`SCHEMA.md`](SCHEMA.md) — the input data structure (what your export must contain).
- [`CODING_GUIDE.md`](CODING_GUIDE.md) — how to set up a coding window to produce it.
- [`data/`](data/) — the derived World Cup sequences, in the canonical format, plus
  `data/theme_inputs/`, the THEME Edu v6 observation files behind the fidelity comparison.
- [`examples/`](examples/) — a runnable quickstart, the reproduction script, and the
  `my_analysis.py` / `my_group_comparison.py` / `my_null_choice.py` starter templates.
- [`PARAMETERS.md`](PARAMETERS.md) — every setting and output column, with range, recommended
  value, and what higher/lower does (generated from the code, so it never drifts).

## Tests

```bash
pip install -e .[test]
pytest -q
```

Both the synthetic ground-truth tests and the reproduction tests run everywhere —
the latter check the detector still reproduces the occurrence counts published for
the reference datasets to the exact N.

## Citation

If you use `tpattern` in research, please cite the software (a machine-readable
version is in [`CITATION.cff`](CITATION.cff)):

Callaway, A. (2026). *tpattern: open, auditable temporal & sequential analysis for
sport and behaviour* [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.21397543

This DOI is permanent and always resolves to the current release. To pin a specific
version instead, use that release's own DOI, listed on the Zenodo record.

And the method it implements:

Magnusson, M. S. (2000). Discovering hidden time patterns in behavior: T-patterns
and their detection. *Behavior Research Methods, Instruments, & Computers*, 32(1),
93–110. https://doi.org/10.3758/BF03200792

The reference software for the method, and its coding front end:

Magnusson, M. S. (2019). T-pattern detection and analysis (TPA) with THEME: A mixed
methods approach. *Frontiers in Psychology*, 10, 2663.
https://doi.org/10.3389/fpsyg.2019.02663

Jonsson, G. K., Anguera, M. T., Blanco-Villaseñor, Á., Losada, J. L.,
Hernández-Mendo, A., Ardá, T., Camerino, O., & Castellano, J. (2006). Hidden
patterns of play interaction in soccer using SOF-CODER. *Behavior Research Methods*,
38(3), 372–381. https://doi.org/10.3758/BF03192790

## License

MIT — see [`LICENSE`](LICENSE).
