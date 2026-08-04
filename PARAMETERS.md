# tpattern parameters and outputs

Every setting and output column, with what it does, its range, the recommended value, and what higher or lower means. Generated from `tpattern/reference.py`, which is also the source for the tutorial's tables, the Colab form labels and `tpattern.explain()`.

## The data can decide it (the advisor recommends)

| Setting (form name / `Config`) | What it does | Range | Recommended | Higher / lower |
|---|---|---|---|---|
| **surrogate_null** / `null` | Which chance model each detected pattern is tested against. | profile, rotation or shuffle. | profile when event types have their own timing (the advisor decides this from the conditional-uniformity check). | profile tests coupling beyond each type's own timing; rotation and shuffle test whether any temporal structure is present at all. |
| **minimum_lag_frames** / `min_lag` | The smallest genuine time gap required between two linked events. | a whole number of time units, 0 or more. | 1 when many events share a timestamp (the advisor recommends it when more than ~10% of neighbouring events are co-timed); 0 to match THEME. | higher treats more co-timed pairs as co-occurrence, not sequence; 0 lets co-timed events count as ordered (THEME-compatible, but sub-frame order is undefined). |
| **frequent_event_exclusion** / `freq_exclude` | Sets aside an over-common event type from building patterns (it is still counted in the baseline). | a positive number (mean occurrences per observation, under the default rule); off if empty. | the advisor flags a type averaging more than ~1.5 occurrences per observation. | lower excludes more (rarer) types; off keeps every type eligible and can flood the results with 'this common event, then anything'. |
| **minimum_occurrence** / `min_occurrence` | How many times a pattern must recur before it is tested. | a whole number, 2 or more (3 is the usual floor). | 3, the floor at which the surrogate test can be calibrated. | higher keeps only more frequent patterns; below 3 the chance test cannot resolve. |
| **error_control** / `error_control` | Which multiple-testing correction is treated as primary. | fdr or fwer. | fdr to screen many patterns; fwer for a single confirmatory claim. | fdr controls the expected share of false discoveries; fwer controls any false positive at all (stricter, and needs a large B). |
| **surrogates_B** / `B` | How many surrogate datasets are drawn for the Monte-Carlo p-value. | a whole number, typically hundreds to thousands. | 200 to screen; 2000 or more for a confirmatory or family-wise claim (the smallest possible p is 1/(B+1)). | higher gives a finer p-value and more confidence, at more compute. |

## Your policy (the data cannot decide it)

| Setting (form name / `Config`) | What it does | Range | Recommended | Higher / lower |
|---|---|---|---|---|
| **detection_alpha** / `alpha` | The critical-interval acceptance threshold: a screening gate deciding which candidates are detected, not the basis of inference. | between 0 and 1, small (e.g. .005 to .05). | .005, a convention in sport T-pattern work; the surrogate calibration, not this threshold, is what a claim rests on. | a looser value lets more candidates through to calibration, but does not change which patterns survive it. |
| **false_discovery_q** / `q_target` | The false-discovery-rate threshold a pattern's q-value must clear. | between 0 and 1 (e.g. .05). | .05. | lower is stricter (fewer patterns reported). |
| **family_wise_alpha** / `alpha_fwer` | The family-wise error rate used for confirmatory claims (Holm). | between 0 and 1 (e.g. .005). | .005; a family-wise claim needs B in the thousands to resolve. | lower is stricter; too small a B cannot reach it. |
| **bout_support_percent** / `min_samples_frac` | The minimum fraction of observations a pattern must appear in to be kept. | 0 to 100 percent; 0 is off. | off. Report prevalence rather than filtering on it (Section 4.1 shows why a threshold cuts along the wrong axis). | raising it deletes rare-but-genuine patterns, including well-evidenced ones specific to a subgroup. |
| **lumping_factor** / `lumping_factor` | If one event nearly always follows another, treat the pair as a single unit so the combinations do not explode. | between 0 and 1; off when 0. | off. The THEME manual illustrates it with 0.9 (a near-deterministic link). | a higher threshold lumps fewer pairs; used mainly to tame very dense data. |
| **completeness_competition** / `completeness` | Drops a pattern whose every occurrence sits inside a longer detected pattern. | on or off. | on. | off keeps redundant sub-patterns and inflates the counts. |
| **collapse_equivalent_patterns** / `collapse_equivalent` | Merges patterns with an identical set of occurrences (the two directions of a co-timed pair, or different bracketings of one chain) to one representative. | on or off. | on. | off double-counts perfectly-dependent duplicates and enlarges the multiple-comparison family. |
| **include_univariate_patterns** / `include_univariate` | Keeps single-event-type entries (Level 0) in the output. | on or off. | on. | off drops the univariate baseline rows. |
| **force_exclude_events** / `exclude_events` | An explicit list of event types to bar from building patterns, overriding the frequency rule. | comma-separated type names, or empty. | empty, so the frequency rule applies. | listing a type removes it from pattern-building whatever its frequency (used to reproduce a specific analysis). |

## Structural input (fixed before analysis)

| Setting (form name / `Config`) | What it does | Range | Recommended | Higher / lower |
|---|---|---|---|---|
| **time_unit** / `time_unit` | The unit of the time columns in your file. | s or ms. | whatever your data uses; times are held internally in milliseconds. | sets the unit intervals are reported in; the wrong choice mis-scales every time. |
| **use_observation_window_columns** / `obs_window` | Reads each observation's window from obs_start / obs_end columns instead of its first and last event. | on or off. | on when your observations have real bounds (a possession, rally or bout usually does). | off takes the window from the events, which shifts every NX/T baseline probability. |
| **maximum_depth** / `max_level` | A cap on how deep the pattern hierarchy can go. | a whole number, 1 or more. | 8; it is rarely reached. | lower yields fewer and simpler patterns and can prevent overload on dense data. |
| **same_instant_duplicates** / `collapse_duplicates` | Collapses two records of the same event type at an identical timestamp to one point. | on or off. | on for finely-timed data (a double-entry is one point in time); off only on coarsely-timed data where two same-type events might genuinely share a coded time. | off keeps both records, inflating that type's baseline rate. |
| **candidate_edge_cap** / `max_edges` | A cap on candidate window boundaries per pair (an approximate search for very dense data). | a whole number, 0 or more; 0 means exact. | 0 (exact). Set it only on very dense data where the exact search does not finish. | lower is faster but makes the window search approximate rather than exhaustive. |

## Output columns

| Column | What it is |
|---|---|
| `pattern` | The pattern as text (the signature is its canonical bracketed form). |
| `N` | Number of occurrences of the pattern across all observations. |
| `bouts` | Number of distinct observations the pattern occurs in. |
| `bout_support` | bouts as a fraction of all observations (the pattern's prevalence). |
| `length` | Number of event types in the pattern. |
| `level` | Hierarchy depth: 0 is a single event type, 1 a pair, higher levels longer chains. |
| `loop` | 1 if the pattern repeats an event type, otherwise 0. |
| `critical_interval` | The accepted time window [d1, d2] within which the later event follows the earlier. |
| `duration_median_ms` | The observed timing of the occurrences: the median gap (with duration_iqr_ms giving the middle half), in milliseconds. |
| `monte_carlo_p` | The Monte-Carlo empirical p-value: the fraction of surrogate datasets in which the pattern is as strong or stronger. |
| `fdr_q` | The Benjamini-Hochberg false-discovery q-value (the screening decision). |
| `survives_fwer_holm` | The Holm family-wise decision: 1 if the pattern survives family-wise control, 0 if not. |
