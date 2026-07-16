# tpattern — open, auditable temporal & sequential analysis for sport and behaviour

`tpattern` detects recurring temporal patterns (T-patterns; Magnusson, 2000) in
timed event data, validates them properly against chance, and produces clean,
publication-ready output — tables, figures and pattern dendrograms. It is a free,
transparent, reproducible alternative to the THEME software, and the analysis
companion to the [OpenTag.Studio](https://opentag.studio) tagging tool.

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

From source (until published on PyPI):

```bash
git clone https://github.com/ajcallaway/TPattern.git
cd tpattern
pip install -e .
```

Requires Python ≥ 3.9 (depends on numpy, scipy, matplotlib).

## Quickstart

```python
from tpattern import read_table, Engine, Config, calibrate, report

# 1. read your events (one row per event: observation, event, start)
observations = read_table("events.csv")            # see SCHEMA.md

# 2. detect T-patterns
patterns = Engine(observations, Config()).detect()

# 3. test each pattern against a surrogate null, corrected for repeated testing
result = calibrate(observations, Config(), null="profile", B=200, q_target=0.05)
survivors = result.kept("fdr")

# 4. write a report: table (with FDR q-values) + dendrograms + summary
report(result, "report_out", title="My analysis")
```

A runnable, no-data-required demo is in [`examples/quickstart.py`](examples/quickstart.py):

```bash
pip install -e .
python examples/quickstart.py
```

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
4. **Detect** T-patterns, **validate** against a null with corrected significance,
   and **report**.

## Relationship to OpenTag.Studio

[OpenTag.Studio](https://opentag.studio) is a free, browser-based sports video
tagging tool. It is the natural front end for `tpattern`: tag your footage, export
a session, and analyse it here — no proprietary software anywhere in the pipeline.
OpenTag's **THEME & GSEQ setup guide** covers how to design a coding window so the
export is analysis-ready, and that guidance applies directly to `tpattern`
(`CODING_GUIDE.md` is the short bridge). Together they form a complete, open
tag → analysis pipeline.

## Documentation

- [`SCHEMA.md`](SCHEMA.md) — the input data structure (what your export must contain).
- [`CODING_GUIDE.md`](CODING_GUIDE.md) — how to set up a coding window to produce it.
- [`examples/`](examples/) — a runnable quickstart and the World Cup reproduction script.

## Tests

```bash
pip install -e .[test]
pytest -q
```

The synthetic ground-truth tests run anywhere. The THEME reproduction test skips
automatically unless the (non-redistributable) World Cup THEME files are present.

## Citation

If you use `tpattern` in research, please cite the software (a machine-readable
version is in [`CITATION.cff`](CITATION.cff)):

Callaway, A. (2026). *tpattern: open, auditable temporal & sequential analysis for
sport and behaviour* (Version 0.1.0) [Computer software].
https://github.com/ajcallaway/TPattern

And the method:

Magnusson, M. S. (2000). Discovering hidden time patterns in behavior: T-patterns
and their detection. *Behavior Research Methods, Instruments, & Computers*, 32(1),
93–110. https://doi.org/10.3758/BF03200792

## License

MIT — see [`LICENSE`](LICENSE).
