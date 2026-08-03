Report the temporal content, and a fuller default output set.

T-pattern analysis computes rich temporal information but reporting usually leaves it buried. 0.1.11 surfaces it, and adds the useful THEME "Generate Tables" exports as **default** outputs.

### Timing, reported by default
Every pattern occurrence has a start, end and duration (`end - start`); for a two-event pattern that is the lag from the first event to the second.

- `patterns_table` now carries `duration_median_ms`, `duration_iqr_ms`, `duration_range_ms`.
- The plain-English verdict states the median lag in words.
- **The dendrogram annotates each join with its median timing** (critical interval shown smaller beneath).
- Reported for **every** pattern, significant or not, so a reader can weigh practical relevance. No practical-importance threshold (MCID/MDC) is claimed — descriptive timing and the statistical test are reported separately.
- All times are labelled in ms (fixing an interval previously printed with no unit).

THEME exposes occurrence timing only as an on-demand "Pattern Duration" export; here it is summarised (median, spread) and on by default.

### New default tables
- `pattern_durations()` — one row per occurrence (start, end, duration)
- `event_type_roles()` — how often each event type is first / inner / last in patterns
- `connections()` — what follows what
- `data_summary()` — per-type counts, prevalence and rate before detection

### New figures
- `duration_plot()` — a pattern's temporal signature (spread of its occurrence durations)
- `occurrence_plot()` — when each event type occurs within its observation
- opt-in `interval_counts()` — before/after-split phase analysis

`report()` emits all of the above by default (pass `observations=` for the data summary and occurrence plot).

### Customisable figures
All plots read one style dict, `tpattern.viz.STYLE` — edit colours, fonts, grid and resolution in one place to restyle every figure without touching the plotting code.
