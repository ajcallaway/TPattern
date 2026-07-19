# tpattern — open, auditable analysis of recurring patterns in event sequences

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/ajcallaway/TPattern/blob/main/colab/tpattern_guided_analysis.ipynb)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21397543.svg)](https://doi.org/10.5281/zenodo.21397543)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`tpattern` detects recurring temporal patterns (T-patterns; Magnusson, 2000) in
**any sequence of timed, labelled events** — behaviour, sport, clinical or
physiological logs, interaction data — validates them properly against chance, and
produces clean, publication-ready output (tables, figures, pattern dendrograms). It
is a free, transparent, reproducible alternative to the THEME software, and the
analysis companion to the [OpenTag.Studio](https://opentag.studio) tagging tool.

## Two ways to use it

- 🚀 **Google Colab — no coding.** [**Open the guided notebook in Colab**](https://colab.research.google.com/github/ajcallaway/TPattern/blob/main/colab/tpattern_guided_analysis.ipynb): upload your events, follow the guided steps, download a report with a plain-English verdict for every pattern and a paste-ready Methods paragraph. See [`colab/`](colab/).
- 🐍 **Python library.** `pip install` and script it — see [Quickstart](#quickstart) and [`examples/`](examples/).

Bring your own data (one row per event — see [`SCHEMA.md`](SCHEMA.md)) or try the
included [`data/`](data/) example.

## Why it exists

T-pattern analysis finds behaviourally meaningful structure that event counts and 
simple transition tables miss. It is most established through Magnusson's THEME
software, the reference implementation. `tpattern` is an open, complementary
implementation that reproduces THEME's detection and adds a reproducible chance
model and clear reporting:

- **reproduces** THEME's core detection (critical intervals, Nx/T baseline,
  completeness competition) — validated to the pattern for published datasets;
- **adds a chance model** — every pattern is tested against a surrogate null, with
  p-values **corrected for repeated testing** (false-discovery rate and
  family-wise);
- **handles concurrency explicitly** — events sharing a timestamp are treated as
  co-occurrence rather than sequence;
- **reports clearly** — tidy tables, effect sizes with confidence intervals,
  purposeful figures, and clean **dendrograms** of the detected patterns.

## Installation

```bash
pip install tpattern
```

Add the guided-wizard extras with `pip install tpattern[gui]`. To work from source
instead (for development or to run the reproduction scripts and shipped data):

```bash
git clone https://github.com/ajcallaway/TPattern.git
cd tpattern
pip install -e .
```

Requires Python ≥ 3.9 (depends on numpy, scipy, matplotlib).

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

# 4. Report: a tidy table (with q-values), pattern dendrograms and a summary —
#    plus a paste-ready Methods paragraph stating every setting and what it does.
report(result, "report_out", title="My analysis")
print(methods_text(Config(), observations=observations, calibration=result))
```

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
the groups (Fisher's exact test, odds ratio + 95% CI) and feeds `forest_plot`.

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
- [`data/`](data/) — the derived World Cup sequences, in the canonical format.
- [`examples/`](examples/) — a runnable quickstart and the reproduction script.

## Tests

```bash
pip install -e .[test]
pytest -q
```

Both the synthetic ground-truth tests and the THEME reproduction tests run
everywhere — the latter check the detector still reproduces THEME's published
occurrence counts to the exact N.

## Citation

If you use `tpattern` in research, please cite the software (a machine-readable
version is in [`CITATION.cff`](CITATION.cff)):

Callaway, A. (2026). *tpattern: open, auditable temporal & sequential analysis for
sport and behaviour* [Computer software]. Zenodo.
https://doi.org/10.5281/zenodo.21397543

This DOI is permanent and always resolves to the current release. To pin a specific
version instead, use that release's own DOI, listed on the Zenodo record.

And the method:

Magnusson, M. S. (2000). Discovering hidden time patterns in behavior: T-patterns
and their detection. *Behavior Research Methods, Instruments, & Computers*, 32(1),
93–110. https://doi.org/10.3758/BF03200792

## License

MIT — see [`LICENSE`](LICENSE).
