# THEME Edu v6 input files — observation data for the fidelity comparison

Deposit accompanying: *Implementation Fidelity and Surrogate-Based Statistical
Inference in an Open T-pattern Analysis Library* (Callaway).

## What this is
The exact observation files given to **THEME Edu v6** (PatternVision;
patternvision.com) for the THEME-versus-`tpattern` comparison reported in
Section 3.1 and Table 1, together with THEME's event-vocabulary definition.

One plain-text file per sequence, tab-separated:

```
time	event
1	:
2	Pass_Complete_NoPressure
1303	Shot_Goal_Pressure
1304	&
```

`:` and `&` are THEME's observation start and end delimiters. `vvt.vvt` in each
folder lists the event vocabulary (the variable/value type definition).

| folder | group | sequences | events |
|---|---|---:|---:|
| `THEME_Goals` | Goals | 163 | 1,001 |
| `THEME_NonGoals` | Non-goals | 1,299 | 6,555 |
| `THEME_Saved` | Defensive recovery (saved-or-blocked shots) | 676 | 3,504 |

Goals + non-goals = the 1,462 shot-ending sequences; defensive recovery is the
676-sequence subgroup analysed separately. Derived from the openly released PFF FC
2022 FIFA World Cup event data (PFF FC, 2023).

A small number of rows carry a timestamp but no event code (23 in non-goals, 15 in
defensive recovery). They are malformed/empty rows, not events, and are excluded
by both tools.

## THEME settings used
Significance .005, minimum occurrence 3, minimum lag 0 (same-timestamp
co-occurrence permitted). THEME's frequent-event exclusion removed
`interception` and `pass_complete_nopressure` in goals and non-goals, and removed
no type in defensive recovery, as recorded in its own output; the `tpattern`
reproduction matched this per-group treatment.

## Why these files are deposited
**THEME's per-pattern output is not re-derivable from this archive.** It was
produced in the THEME Edu v6 interface, which is closed proprietary software, and
the per-pattern export was not retained. The per-pattern counts in Table 1 and
Section 3.1 are therefore reported *as recorded from that run*.

Depositing the inputs makes the THEME side of the comparison reproducible by
anyone holding a THEME licence: load these files with the settings above and the
comparison can be repeated independently.

## The input side IS verified
Both tools demonstrably read the same events. The derived event tables in the
`tpattern` repository (`data/worldcup_*.csv`) use these filenames as their
`observation` values, so the correspondence is one-to-one, and it has been checked
on sequence identity, event times and event types:

```
python examples/verify_theme_inputs.py --theme-root <this directory>

group          sequences   events  blank rows        result
Goals                163     1001           0         EXACT
NonGoals            1299     6555          23         EXACT
DefRecovery          676     3504          15         EXACT

All 2138 sequences match exactly: same sequence identifiers, same event times,
same event types. THEME and tpattern were given identical input.
```

That script ships in the `tpattern` repository, so the check is re-runnable rather
than asserted.

## Licence
The derived event sequences are released under the same terms as the rest of the
`tpattern` materials (MIT). The underlying PFF FC event data is the property of
PFF FC and was made freely available for research.
