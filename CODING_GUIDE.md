# Coding for tpattern — how to tag so the analysis works

This complements OpenTag's **THEME & GSEQ Setup Guide** (`dist/tools/lsa-guide.html`),
which already covers the essentials — the events-vs-attributes principle, the three
code-window designs, naming rules, frame-precise timestamps, session boundaries, and
the ≥ 20-instances-per-code volume rule. All of that applies unchanged.

This note adds only the conventions that unlock the tpattern engine's outcome and
group analyses (which OpenTag exports feed directly, no THEME/GSEQ round-trip).

## Use Design 2 (one event per action) for temporal analysis

Tag each action as its own timestamped event. Bundling actions as attributes on one
episode gives ordinal order only. One event per action gives genuine inter-action
timing — the input the engine needs.

## Four conventions that turn on the powerful analyses

Follow these and the recurring analyses become one-line calls rather than bespoke work:

1. **Prefix every code by actor/team** — `P1_`, `P2_` (or `Home_`, `Away_`).
   → enables per-actor and cross-actor analysis.
2. **Group codes by role**, in the order they occur:
   *Attack Initiator → Opponent Reaction → Follow-up Action → Outcome*.
   → enables phrase analysis (initiator → reaction → follow-up → outcome), the design
   that produced the confirmed winner-vs-loser findings in the taekwondo study.
3. **Give outcomes their own explicit codes** — every score type **and** an explicit
   `NoScore`. → enables outcome-linkage (which sequences score) and correct base rates.
   Don't leave "no score" implicit; the engine needs it to compute a denominator.
4. **Delimit each unit with `Start` / `End`** (whistle → resolution).
   → defines the observation; the winner/loser or goal/non-goal group label is then
   derived per unit (e.g. by summing points).

## Worked example (taekwondo)

```
Start                              — referee reset
Attack Initiator:  P1_CK, P2_DA…   — one code per attacking action
Opponent Reaction: P1_GR, P2_CA…   — one code per reaction
Follow-up Action:  P1_DC, P2_FK, …, P1_NoFollowUp
Outcome:           P1_1Pt…P1_4Pt, P1_GamjeomPlus/Minus, P1_NoScore
End                                — after the point is resolved
```

From this alone the engine derives: attacking phrases, who initiated, whether the
initiator scored / was countered / no score, and the bout winner (from summed
points) — i.e. everything in the phrase-based tactical analysis, automatically.

## What each convention maps to

| Convention | Engine capability |
|---|---|
| actor prefix | per-actor detection, cross-actor exchanges |
| role grouping | phrase / structured-sequence analysis |
| explicit outcomes | outcome-linkage, scoring base rate |
| Start/End units + derived label | winner-vs-loser (group) contrast |

Nothing here conflicts with THEME/GSEQ export — a window built this way works for
both the tpattern engine and the existing OpenTag converter.
