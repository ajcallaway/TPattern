# From tagging to tpattern — a practical setup guide

This is the short bridge between coding your video and running the analysis. It
pairs with OpenTag's fuller **THEME & GSEQ Setup Guide**
([opentag.studio](https://opentag.studio) → Research → LSA tools), which covers the
observational-design detail; here we focus on getting clean data **straight into
`tpattern`** in three steps.

## The three steps

### 1. Set up the code window — one event per action

Tag **each action as its own timestamped event** (OpenTag "Design 2": every action
type is its own code button; attributes/labels are descriptors that share the
event's time). This is the one decision that matters: one event per action gives
genuine inter-action timing — the input T-pattern detection needs — whereas bundling
actions as attributes on a single episode gives ordinal order only.

Delimit each analysis unit with **`Start` / `End`** buttons (whistle → resolution).
Each `Start`→`End` block becomes one **observation** (a possession, rally, bout).

Follow the naming rules (no spaces, hyphens, brackets or commas in codes) so the
export is clean — e.g. `P1_CutKick`, not `P1 Cut-Kick`.

### 2. Export from OpenTag

Export the session (OpenTag CSV/JSON). Each event carries a **start time**, an
**event code**, and its **session/sequence id** — everything `tpattern` needs. The
columns map directly onto the canonical table:

| tpattern column | OpenTag field | Sportscode field |
|---|---|---|
| `observation` | session / sequence id (the `Start`→`End` block) | `Bout_ID` |
| `event` | `eventName` | `Row` |
| `start` | `start_s` / `timestamp` | `Start time` |
| `end` / `duration` *(optional)* | `endTime` / `duration_s` | `Duration` |
| `obs_start` / `obs_end` *(optional)* | the sequence's window bounds | — |

### 3. Read it into tpattern

If your export already uses the column names `observation, event, start`:

```python
from tpattern import read_table, recommend, calibrate, report
obs = read_table("opentag_export.csv")        # add time_unit="ms" if times are in ms
```

If the columns are named differently, just say so — no reformatting needed:

```python
obs = read_table("opentag_export.csv",
                 observation="session_id", event="eventName", start="start_s")
```

Then run the analysis (the tool will recommend the settings from your data):

```python
print(recommend(obs))                          # data-driven method suggestion
result = calibrate(obs, null="profile", B=200) # detect + test against a null
report(result, "output")                       # tables, dendrograms, summary
```

Or use the guided wizard (`from tpattern import launch; launch()`) — see
`examples/guided_colab.py`.

## Optional conventions that unlock the built-in analyses

The three steps above are enough for T-pattern detection. Adding these turns on the
richer analyses as one-line calls rather than bespoke work:

1. **Prefix every code by actor/team** — `P1_`, `P2_` (or `Home_`, `Away_`).
   → per-actor and cross-actor analysis.
2. **Group codes by role**, in the order they occur — *Attack Initiator → Opponent
   Reaction → Follow-up Action → Outcome*. → phrase analysis (the design behind the
   winner-vs-loser taekwondo findings).
3. **Give outcomes explicit codes** — every score type **and** an explicit `NoScore`.
   → outcome-linkage and correct base rates (the engine needs the denominator).
4. **Derive a group label per unit** (e.g. winner/loser from summed points, or
   goal/non-goal). → group contrast.

| Convention | Unlocks |
|---|---|
| actor prefix | per-actor detection, cross-actor exchanges |
| role grouping | phrase / structured-sequence analysis |
| explicit outcomes | outcome-linkage, scoring base rate |
| Start/End units + group label | winner-vs-loser (group) contrast |

## Ready-made: the PFF football panel

If you tag football and want data that matches the PFF World Cup scheme used in the
validation study, OpenTag.Studio ships a ready-made coding panel that replicates it 1:1.
Open it directly with the deep link **`https://opentag.studio/?panel=pff`** (also reachable
from the Research tab), tag your video, and **Export → Research CSV**. The panel is 9 event
buttons (Pass, Cross, Challenge, Shot, Clearance, Touch, BallCarry, Recovery, Interception)
plus two linked dropdowns, `Pressure` and `Outcome`, that attach only to the events they
belong to — so the export is correctly scoped (Interception carries no pressure, Challenge
no outcome, and so on).

Read the Research CSV straight in — the compound `EventType_Outcome_PressureContext` codes
are built from the three columns:

```python
from tpattern import read_table

obs = read_table(
    "match_research.csv",
    observation="session_id",                           # the sequence / match id
    start="start_s",                                    # tag time, in seconds
    build_event_from=["event", "Outcome", "Pressure"],  # → Cross_Incomplete_NoPressure, etc.
    time_unit="s",
)
```

The extra descriptive columns in the Research CSV (`sport, date, home, …`) are ignored;
`build_event_from` skips empty parts, so a Challenge reads as `Challenge_Pressure` and an
Interception as `Interception`. This reproduces the exact code set of the validation study,
with no proprietary software anywhere in the pipeline.

## Worked example (taekwondo)

```
Start                              — referee reset
P1_CK, P2_DA…                      — one event per attacking action
P1_GR, P2_CA…                      — one event per reaction
P1_DC, P2_FK, …, P1_NoFollowUp     — follow-ups
P1_1Pt…P1_4Pt, P1_GamjeomMinus, P1_NoScore   — outcomes
End                                — after the point is resolved
```

From this alone the engine derives the attacking phrases, who initiated, whether the
initiator scored / was countered / did not score, and the bout winner (from summed
points).

---

The same code window feeds THEME and GSEQ too (via the OpenTag LSA Converter), so
nothing here locks you in — `tpattern` is simply the open, calibrated route that
reads the export directly, with no proprietary software in the pipeline.
