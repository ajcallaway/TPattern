# Data — 2022 FIFA World Cup shot-ending possession sequences

The derived event sequences used in the technical note and the applied paper. They
ship here so the analyses can be **reproduced from this repository alone**:

```bash
python examples/reproduce_worldcup.py
```

## Files

| File | Sequences | Description |
|---|---|---|
| `worldcup_goals.csv` | 163 | shot-ending sequences that ended in a goal |
| `worldcup_nongoals.csv` | 1,299 | all non-scoring shot-ending sequences |
| `worldcup_defensive_recovery.csv` | 676 | saved-or-blocked shots (a subgroup of the non-goals) |

## Format

The library's canonical event table (see [`../SCHEMA.md`](../SCHEMA.md)) — one row
per event:

```csv
observation,event,start,obs_start,obs_end
G001,Pass_Complete_NoPressure,2,1,1304
G001,Challenge_Pressure,1301,1,1304
G001,Shot_Goal_Pressure,1303,1,1304
```

- `observation` — one shot-ending possession sequence
- `event` — compound code: event type + context (pressure status / ball-flight)
- `start` — event time in **milliseconds**, relative to the sequence
- `obs_start`, `obs_end` — the **observation window**. This matters: the window
  length `T = obs_end - obs_start` is the denominator of the NX/T baseline, so it
  is stored explicitly rather than inferred from the first/last event. Inferring it
  would shift the baseline (total window time 1,064,634 ms vs 1,064,358 ms for the
  goals sample) and change borderline results.

Read them with:

```python
from tpattern import read_table
obs = read_table("data/worldcup_goals.csv",
                 obs_start="obs_start", obs_end="obs_end", time_unit="ms")
```

## Provenance and derivation

Source: **PFF Sports / Gradient Sports 2022 FIFA World Cup dataset**, released free
for research (PFF Sports, 2022). These files are **not** that dataset. They are a
derived analytical representation produced by:

1. extracting the possession sequence preceding every open-play shot (continuous
   possession logic, 60 s lookback, truncated at the prior shot, interception-delimited);
2. applying the exclusion funnel (1,559 → 1,462 shots);
3. coding each event with a compound label (event type + pressure/ball-flight context);
4. reducing each sequence to event codes with millisecond timestamps relative to the
   sequence.

They therefore contain **no player names, team names, match identifiers, pitch
coordinates, tracking data, or PFF grades** — nothing of the source dataset is
reproduced. The coding scheme, extraction logic and sequence construction are the
authors' own.

The exact derivation code — the script that reads the raw PFF event JSONs and
produces these sequences (steps 1–4 above) — is provided in
[`derivation/`](derivation/), so the full pipeline from the open source data to the
analysed sequences is documented and reproducible.

Timestamps are frame-quantised (broadcast tracking at 29.97 fps), which is why
roughly half of consecutive events share a timestamp. That is a property of the
source coding, not an artefact of this derivation — and it is exactly what the
concurrency analysis in the technical note addresses.

If you want the underlying event and tracking data, request it directly from
[PFF FC / Gradient Sports](https://www.blog.fc.pff.com/blog/pff-fc-release-2022-world-cup-data).

## Citation

Cite the software (see [`../CITATION.cff`](../CITATION.cff)) and the source dataset:

PFF Sports. (2022). *2022 FIFA World Cup event data* [Dataset]. PFF Sports.
