# tpattern — input data structure

There is one fixed input structure. Any coding tool (Sportscode, OpenTag,
Nacsport, a spreadsheet) can produce it; the library does **not** parse or
interpret arbitrary formats — the user exports to these columns.

A minimal valid file looks like this — copy it and adapt (each row is one event;
one `observation` per analysis unit):

```csv
observation,event,start
rally01,Serve_Flat,0.0
rally01,Return_Deep,1.2
rally01,Winner_Forehand,3.4
rally02,Serve_Wide,0.0
rally02,Return_Net,0.9
```

```python
from tpattern import read_table
obs = read_table("events.csv")     # times in seconds; add time_unit="ms" if milliseconds
```

If your analysis unit has real bounds (a possession, rally or bout — the whistle
goes before the first event and after the last), add `obs_start`/`obs_end` too
(see below). The full column set:

It is a flat table, **one row per event**:

| Column | Required | Meaning |
|---|---|---|
| `observation` | **yes** | the analysis unit the event belongs to (bout, possession, rally, match) |
| `event` | **yes** | the event/action code (e.g. `P1_CK`, `Home_Shot`) |
| `start` | **yes** | event start time, numeric (seconds or any consistent unit) |
| `end` | no | event end time; or give `duration` instead |
| `duration` | no | event duration (used for state durations / precision) |
| `obs_start`, `obs_end` | no | the **observation window** (same value on every row of an observation) — see below |
| *label columns* | no | any extra columns = descriptor dimensions (role, actor, outcome…) |
| *meta columns* | no | session-level descriptors (round, date, group label…) |

Confirmed identical across sources — only the column names differ:

| Canonical | Sportscode export | OpenTag (CSV / JSON) |
|---|---|---|
| `observation` | `Bout_ID` | `session_id` / one session file |
| `event` | `Row` | `event` / `eventName` |
| `start` | `Start time` | `start_s` / `timestamp` |
| `end` / `duration` | `Duration` | `end_s`,`duration_s` / `endTime` |
| labels | label-group columns | attribute-group columns / `attributes` |
| meta | `Competition_Round`, `Bout_Round` | sport, date, home, away, … |

## The two things the user decides when setting up their coding

These are not parsed — they are how the user structures the export:

1. **The observation unit** is whatever they put in `observation` (a bout, a
   possession, a Start→End sequence). One id per unit.
2. **The event code** is the `event` column, used as-is (one code per action —
   the recommended design). If instead the code should be built from several
   descriptor columns, those columns are named and joined at load time.

## Optional descriptor columns — what they unlock

Supplying these (as label/attribute columns) turns recurring analyses on:

| Column meaning | Unlocks |
|---|---|
| `actor` (or a `P1_`/`Home_` prefix on the code) | per-actor / cross-actor analysis |
| `role` (Initiator / Reaction / Follow-up / Outcome) | phrase / structured-sequence analysis |
| `outcome` (explicit score / no-score codes) | outcome-linkage + scoring base rate |
| `group` (session-level, e.g. winner/loser, goal/non-goal) | group contrast |

## The observation window (`obs_start` / `obs_end`)

Give these whenever the analysis unit has **real bounds that extend beyond its first
and last event** — a possession, rally or bout usually does (the whistle goes before
the first action and after the last).

This is not cosmetic. The window length `T = obs_end - obs_start` is the denominator
of the NX/T baseline probability, so every significance test depends on it. If the
window is left out, it falls back to the first/last event time, which shortens T and
shifts every baseline. In the shipped World Cup goals sample the difference is
1,064,634 ms (true) versus 1,064,358 ms (inferred) — enough to move borderline
patterns. Store it explicitly if you have it.

```python
obs = read_table("events.csv", obs_start="obs_start", obs_end="obs_end", time_unit="ms")
```

## Notes

- Provide `end` or `duration` if event ordering/timing matters. If events are
  coded to a coarse frame, many share a `start` and their order is undefined
  (seen in 30 Hz football data — ~half of consecutive events tied). Code at the
  finest resolution the question needs.
- The library reads this table into its internal `Observation` objects (one per
  `observation` id) and everything downstream — detection, significance, the
  phrase / outcome / group analyses — is unchanged regardless of source.

See `CODING_GUIDE.md` for how to set up a coding window (in any software) to
produce this structure.
