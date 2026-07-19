# Run tpattern in Google Colab — no installation, no coding

Find recurring temporal patterns in any sequence of timed, labelled events —
sport, behaviour, clinical or physiological logs, interaction data — test them
against chance, and get a plain-English report. All in your browser.

## Open a notebook

Click the badge in the [main README](../README.md#two-ways-to-use-it), or in Colab
use **File → Upload notebook** and choose one of:

- **`tpattern_guided_analysis.ipynb`** — recommended. Installs tpattern from GitHub,
  so you always get the latest version.
- **`tpattern_guided_analysis_offline.ipynb`** — no install; the package is bundled
  inside the notebook (a snapshot). Use this if you can't install from GitHub.
- **`tpattern_worked_example.ipynb`** — the companion to the tutorial paper. Runs the
  worked example (load → inspect → recommend → calibrate → report) on the shipped
  World Cup goal sequences, cell by cell, so you can follow the analysis and then
  swap in your own data.

## What happens

The notebook opens a guided panel — four steps:

1. **Upload** your events CSV (one row per event: `observation, event, start`).
2. **Inspect** — the tool checks your data and shows what it recommends, and *why*.
3. The recommended **settings appear**, pre-set from your data (override if you wish).
4. **Run** — you get, inline and as a downloadable zip:
   - a colour-coded results table with a plain-English verdict for every pattern
     (🟢 robust · 🟡 borderline · ⚪ likely chance),
   - the pattern dendrograms,
   - the code to redraw or restyle them,
   - a ready-to-paste **Methods** paragraph.

## Data format

One row per event. See [`../SCHEMA.md`](../SCHEMA.md). No data of your own yet? Try
[`../data/worldcup_goals.csv`](../data/worldcup_goals.csv) — select **ms** for the
time unit.

---

*Maintainers: rebuild the offline notebook after changing the package with
`python build_offline_notebook.py`.*
