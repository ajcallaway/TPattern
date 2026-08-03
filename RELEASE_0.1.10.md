Forgiving data import with plain-language feedback.

`read_table` now checks your file as it reads it and tells you, in plain language, what it found, **how much of the file it affects**, and how to fix it (with an example) — instead of silently dropping unusable rows. Each check has a stable code: a code beginning **E** stops the read (something must be fixed first); **W** is a warning (the data loads, but rows were left out or a label is ambiguous); **I** is information (nothing lost). The clean-data path is byte-identical, so existing analyses reproduce exactly.

### The data-check codes

| Code | Type | What it means | How to fix | Example |
|------|------|---------------|-----------|---------|
| E01 | **Error** — stops | A column the analysis needs is not in the file. | Rename the column, or tell read_table its name. | `read_table("events.csv", start="Start Time")` |
| E02 | **Error** — stops | The file read as a single column, so it is probably not comma-separated. | Re-save it as a comma-separated CSV, or pass the separator. | `read_table("events.csv", sep=";")` |
| E03 | **Error** — stops | The file has a header row but no data under it (or is empty). | Check the export actually contains events, then re-run. | `a data row looks like: p1,pass,0` |
| E04 | **Error** — stops | Every row was unusable, so there was nothing to load. | Open the file and check the observation, event and start columns are filled in. | `p1,pass,0 (a value in observation, event and start)` |
| E05 | **Error** — stops | No observation has at least two events, so no pattern can form. | Check the observation column groups events correctly; a pattern needs two or more events in the same observation. | `two rows sharing an id: p1,pass,0 and p1,shot,3` |
| W10 | Warning — loads | Some start times are not numbers, so those rows were left out. | Times must be numbers. If yours is a mm:ss clock, convert it to seconds first. | `01:23 → 83` |
| W11 | Warning — loads | Some rows have a blank observation id and were left out. | Fill in the observation column, or remove the empty rows. | `,pass,0 → p1,pass,0` |
| W12 | Warning — loads | Some rows have a blank event label and were left out. | Fill in the event column, or remove the empty rows. | `p1,,0 → p1,pass,0` |
| W13 | Warning — loads | Two or more event labels differ only by capitalisation or spacing. | They are counted as different events. Merge them if they mean the same thing. | `Pass and pass → both Pass` |
| W14 | Warning — loads | Some events fall outside their observation's window, or a window has end at or before start. | Check the obs_start / obs_end columns; the window should contain all of the observation's events. | `event at 620 with window 0-600 → set obs_end ≥ 620` |
| W15 | Warning — loads | The time values look like they might be in the other unit. | Check time_unit: pass "s" for seconds or "ms" for milliseconds. | `read_table("events.csv", time_unit="s")` |
| I20 | Info — loads | Some observations have fewer than two events. | None needed. They set the baseline event rates but cannot themselves contain a pattern; the Methods text reports both counts. | `Methods reports "163 observations, 131 with ≥2 events"` |
| I21 | Info — loads | The file contains only one observation. | None needed, but check it is intended: patterns are counted across observations, so a single time-line will detect little. | `is the observation column accidentally a constant?` |
| I22 | Info — loads | One event type makes up a large share of all events. | None needed. A very common event can link to almost everything; the advisor may suggest setting it aside from pattern-building. | `exclude_events=["Interception"]` |
| I23 | Info — loads | A high fraction of neighbouring events share an identical time. | None needed. The advisor will likely suggest requiring a genuine gap so co-timed events are read as co-occurrence, not sequence. | `Config(min_lag=1)` |
| I24 | Info — loads | Some rows are exact duplicates (same observation, event and time). | None needed by default: identical same-time events are counted once. If they are double entries and you turned that collapsing off, remove the copies. | `keep collapse_duplicates on (the default)` |

### Also in this release

- **`methods_text()` reports the effective sample** — how many observations could actually contain a pattern, alongside the number submitted — so a Methods statement cannot overstate what was analysed.
- **`DataFormatError`, `CHECKS` and `check_reference()`** are exported. `CHECKS` is the single registry that generates *both* the console messages and the tutorial's Appendix A, so they can never disagree.
- **Colab** — the worked-example notebook gains a one-click upload cell and clear "edit these lines" instructions for running on your own data; the offline notebook is re-embedded with the updated source (no install needed).
- 13 new tests (53 total pass); a UTF-8 byte-order mark (Excel) is stripped automatically.

Full details: [CHANGELOG](https://github.com/ajcallaway/TPattern/blob/main/CHANGELOG.md).