# tpattern — input data structure

There is one fixed input structure. Any coding tool (Sportscode, OpenTag,
Nacsport, a spreadsheet) can produce it; the library does **not** parse or
interpret arbitrary formats — the user exports to these columns.

It is a flat table, **one row per event**:

| Column | Required | Meaning |
|---|---|---|
| `observation` | **yes** | the analysis unit the event belongs to (bout, possession, rally, match) |
| `event` | **yes** | the event/action code (e.g. `P1_CK`, `Home_Shot`) |
| `start` | **yes** | event start time, numeric (seconds or any consistent unit) |
| `end` | no | event end time; or give `duration` instead |
| `duration` | no | event duration (used for state durations / precision) |
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
