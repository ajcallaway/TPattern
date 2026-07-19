# Deriving the World Cup sequences from the raw PFF data

This folder holds the **original derivation code of record** — the script that turns
the openly released PFF FC 2022 FIFA World Cup event data into the analysis-ready
event-sequence tables shipped in [`../`](../).

## Source data

The analysis uses the **PFF FC 2022 FIFA World Cup event dataset**, released free for
research (PFF Sports, 2022). The raw event JSONs are **not** redistributed here (they
are large and are PFF's release to make); obtain them from PFF's open research
release — see the paper's data-availability statement for the access URL. The
**derived** sequences *are* shipped in [`../`](../), so every reported analysis
reproduces from this repository alone; this script documents exactly how they were
produced.

## The script

`Temporal_Step1_ExtractSequences.m` (MATLAB, developed on R2022a) reads a folder of
PFF event JSONs and writes the shot-ending possession sequences. It is the verified
derivation used for the paper — column-checked against the parallel shot-extraction
pipeline. Set the two paths at the top (`CONFIG.event_folder`, `CONFIG.output_folder`)
and run.

**What it does** (see the header comment for the full specification):

1. **Sequence definition** — for every eligible open-play shot, walk backwards
   through the event stream collecting consecutive same-team events, stopping at a
   possession change, a 60 s lookback cap, or a >5 s stoppage gap.
2. **Shot eligibility** — the exclusion funnel (missing ball coordinates, own-half
   shots, ball beyond the goal line, penalties, shots ≥ 55 m).
3. **Event coding** — each event gets a compound descriptive code (`event_code_L2`),
   e.g. `Cross_Incomplete_NoPressure`, `Shot_Goal_Pressure` — event type plus
   pressure / ball-flight context.

**Outputs**

- `Temporal_Sequences.csv` — one row per event within a sequence.
- `Temporal_SequenceSummary.csv` — one row per sequence (per shot).
- `Temporal_THEME_Goals.obs`, `..._NonGoals.obs`, `..._Saved.obs` — THEME-format
  sequence files (tab-separated `sequence_id  time_s  event_code_L2`).

## From these outputs to the shipped CSVs

The shipped [`../worldcup_goals.csv`](../worldcup_goals.csv),
[`../worldcup_nongoals.csv`](../worldcup_nongoals.csv) and
[`../worldcup_defensive_recovery.csv`](../worldcup_defensive_recovery.csv) are these
per-group sequences in the library's canonical flat format — one row per event
(`observation, event, start, obs_start, obs_end`), with `start` in **milliseconds**
relative to each sequence. See [`../README.md`](../README.md) for the format and the
observation-window (`T = obs_end − obs_start`) rationale.
