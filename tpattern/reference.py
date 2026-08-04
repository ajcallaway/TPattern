"""
One reference for every setting and every output column.
=========================================================

The problem this solves: a user meets these names in three places — the Python
`Config`, the Colab settings form, and the results table — and needs, for each, the
same four things: what it *is*, what range it takes, what value is *recommended*, and
what *higher or lower* does to the analysis. Rather than scatter that across
docstrings, a paper table and the advisor, it lives here once. Everything else is
generated from it: :func:`explain`, the ``PARAMETERS.md`` reference, the tutorial's
settings and output-column tables, and the plain-language field labels in the Colab
form. So the code, the paper and the notebook cannot drift.

Each setting record has:
  key        the ``Config`` (or read_table/calibrate) argument name
  form       the friendly name shown in the Colab form and the paper
  group      A = the data can decide it (the advisor recommends);
             B = your policy (the data cannot decide it);
             C = a structural input fixed before analysis
  does       what it does to the detection, in one line
  range      the values it accepts
  recommend  the recommended value, and when
  effect     what higher / lower (or on / off) means
"""

from __future__ import annotations

# --- settings ---------------------------------------------------------------
SETTINGS: list[dict] = [
    # A. the data can decide these (the advisor recommends them)
    dict(key="null", form="surrogate_null", group="A",
         does="Which chance model each detected pattern is tested against.",
         range="profile, rotation or shuffle.",
         recommend="profile when event types have their own timing (the advisor decides this from the conditional-uniformity check).",
         effect="profile tests coupling beyond each type's own timing; rotation and shuffle test whether any temporal structure is present at all."),
    dict(key="min_lag", form="minimum_lag_frames", group="A",
         does="The smallest genuine time gap required between two linked events.",
         range="a whole number of time units, 0 or more.",
         recommend="1 when many events share a timestamp (the advisor recommends it when more than ~10% of neighbouring events are co-timed); 0 to match THEME.",
         effect="higher treats more co-timed pairs as co-occurrence, not sequence; 0 lets co-timed events count as ordered (THEME-compatible, but sub-frame order is undefined)."),
    dict(key="freq_exclude", form="frequent_event_exclusion", group="A",
         does="Sets aside an over-common event type from building patterns (it is still counted in the baseline).",
         range="a positive number (mean occurrences per observation, under the default rule); off if empty.",
         recommend="the advisor flags a type averaging more than ~1.5 occurrences per observation.",
         effect="lower excludes more (rarer) types; off keeps every type eligible and can flood the results with 'this common event, then anything'."),
    dict(key="min_occurrence", form="minimum_occurrence", group="A",
         does="How many times a pattern must recur before it is tested.",
         range="a whole number, 2 or more (3 is the usual floor).",
         recommend="3, the floor at which the surrogate test can be calibrated.",
         effect="higher keeps only more frequent patterns; below 3 the chance test cannot resolve."),
    dict(key="error_control", form="error_control", group="A",
         does="Which multiple-testing correction is treated as primary.",
         range="fdr or fwer.",
         recommend="fdr to screen many patterns; fwer for a single confirmatory claim.",
         effect="fdr controls the expected share of false discoveries; fwer controls any false positive at all (stricter, and needs a large B)."),
    dict(key="B", form="surrogates_B", group="A",
         does="How many surrogate datasets are drawn for the Monte-Carlo p-value.",
         range="a whole number, typically hundreds to thousands.",
         recommend="200 to screen; 2000 or more for a confirmatory or family-wise claim (the smallest possible p is 1/(B+1)).",
         effect="higher gives a finer p-value and more confidence, at more compute."),
    # B. your policy (the data cannot decide these)
    dict(key="alpha", form="detection_alpha", group="B",
         does="The critical-interval acceptance threshold: a screening gate deciding which candidates are detected, not the basis of inference.",
         range="between 0 and 1, small (e.g. .005 to .05).",
         recommend=".005, a convention in sport T-pattern work; the surrogate calibration, not this threshold, is what a claim rests on.",
         effect="a looser value lets more candidates through to calibration, but does not change which patterns survive it."),
    dict(key="q_target", form="false_discovery_q", group="B",
         does="The false-discovery-rate threshold a pattern's q-value must clear.",
         range="between 0 and 1 (e.g. .05).",
         recommend=".05.",
         effect="lower is stricter (fewer patterns reported)."),
    dict(key="alpha_fwer", form="family_wise_alpha", group="B",
         does="The family-wise error rate used for confirmatory claims (Holm).",
         range="between 0 and 1 (e.g. .005).",
         recommend=".005; a family-wise claim needs B in the thousands to resolve.",
         effect="lower is stricter; too small a B cannot reach it."),
    dict(key="min_samples_frac", form="bout_support_percent", group="B",
         does="The minimum fraction of observations a pattern must appear in to be kept.",
         range="0 to 100 percent; 0 is off.",
         recommend="off. Report prevalence rather than filtering on it (Section 4.1 shows why a threshold cuts along the wrong axis).",
         effect="raising it deletes rare-but-genuine patterns, including well-evidenced ones specific to a subgroup."),
    dict(key="lumping_factor", form="lumping_factor", group="B",
         does="If one event nearly always follows another, treat the pair as a single unit so the combinations do not explode.",
         range="between 0 and 1; off when 0.",
         recommend="off. The THEME manual illustrates it with 0.9 (a near-deterministic link).",
         effect="a higher threshold lumps fewer pairs; used mainly to tame very dense data."),
    dict(key="completeness", form="completeness_competition", group="B",
         does="Drops a pattern whose every occurrence sits inside a longer detected pattern.",
         range="on or off.",
         recommend="on.",
         effect="off keeps redundant sub-patterns and inflates the counts."),
    dict(key="collapse_equivalent", form="collapse_equivalent_patterns", group="B",
         does="Merges patterns with an identical set of occurrences (the two directions of a co-timed pair, or different bracketings of one chain) to one representative.",
         range="on or off.",
         recommend="on.",
         effect="off double-counts perfectly-dependent duplicates and enlarges the multiple-comparison family."),
    dict(key="include_univariate", form="include_univariate_patterns", group="B",
         does="Keeps single-event-type entries (Level 0) in the output.",
         range="on or off.",
         recommend="on.",
         effect="off drops the univariate baseline rows."),
    dict(key="exclude_events", form="force_exclude_events", group="B",
         does="An explicit list of event types to bar from building patterns, overriding the frequency rule.",
         range="comma-separated type names, or empty.",
         recommend="empty, so the frequency rule applies.",
         effect="listing a type removes it from pattern-building whatever its frequency (used to reproduce a specific analysis)."),
    # C. structural inputs (fixed before analysis, change every result)
    dict(key="time_unit", form="time_unit", group="C",
         does="The unit of the time columns in your file.",
         range="s or ms.",
         recommend="whatever your data uses; times are held internally in milliseconds.",
         effect="sets the unit intervals are reported in; the wrong choice mis-scales every time."),
    dict(key="obs_window", form="use_observation_window_columns", group="C",
         does="Reads each observation's window from obs_start / obs_end columns instead of its first and last event.",
         range="on or off.",
         recommend="on when your observations have real bounds (a possession, rally or bout usually does).",
         effect="off takes the window from the events, which shifts every NX/T baseline probability."),
    dict(key="max_level", form="maximum_depth", group="C",
         does="A cap on how deep the pattern hierarchy can go.",
         range="a whole number, 1 or more.",
         recommend="8; it is rarely reached.",
         effect="lower yields fewer and simpler patterns and can prevent overload on dense data."),
    dict(key="collapse_duplicates", form="same_instant_duplicates", group="C",
         does="Collapses two records of the same event type at an identical timestamp to one point.",
         range="on or off.",
         recommend="on for finely-timed data (a double-entry is one point in time); off only on coarsely-timed data where two same-type events might genuinely share a coded time.",
         effect="off keeps both records, inflating that type's baseline rate."),
    dict(key="max_edges", form="candidate_edge_cap", group="C",
         does="A cap on candidate window boundaries per pair (an approximate search for very dense data).",
         range="a whole number, 0 or more; 0 means exact.",
         recommend="0 (exact). Set it only on very dense data where the exact search does not finish.",
         effect="lower is faster but makes the window search approximate rather than exhaustive."),
]

# --- output columns ---------------------------------------------------------
COLUMNS: list[dict] = [
    dict(key="pattern", does="The pattern as text (the signature is its canonical bracketed form)."),
    dict(key="N", does="Number of occurrences of the pattern across all observations."),
    dict(key="bouts", does="Number of distinct observations the pattern occurs in."),
    dict(key="bout_support", does="bouts as a fraction of all observations (the pattern's prevalence)."),
    dict(key="length", does="Number of event types in the pattern."),
    dict(key="level", does="Hierarchy depth: 0 is a single event type, 1 a pair, higher levels longer chains."),
    dict(key="loop", does="1 if the pattern repeats an event type, otherwise 0."),
    dict(key="critical_interval", does="The accepted time window [d1, d2] within which the later event follows the earlier."),
    dict(key="duration_median_ms", does="The observed timing of the occurrences: the median gap (with duration_iqr_ms giving the middle half), in milliseconds."),
    dict(key="monte_carlo_p", does="The Monte-Carlo empirical p-value: the fraction of surrogate datasets in which the pattern is as strong or stronger."),
    dict(key="fdr_q", does="The Benjamini-Hochberg false-discovery q-value (the screening decision)."),
    dict(key="survives_fwer_holm", does="The Holm family-wise decision: 1 if the pattern survives family-wise control, 0 if not."),
]

_GROUP = {"A": "The data can decide it (the advisor recommends)",
          "B": "Your policy (the data cannot decide it)",
          "C": "Structural input (fixed before analysis)"}


def explain(name: str | None = None) -> str:
    """Plain-language reference for a setting or output column, or for everything.

    ``explain("min_lag")`` (or its form name ``"minimum_lag_frames"``) describes one
    setting; ``explain("fdr_q")`` an output column; ``explain()`` prints them all.
    """
    if name is None:
        return explain_settings() + "\n\n" + explain_columns()
    for s in SETTINGS:
        if name in (s["key"], s["form"]):
            return (f"{s['form']} (Config: {s['key']})  [{_GROUP[s['group']]}]\n"
                    f"  what it does : {s['does']}\n"
                    f"  range        : {s['range']}\n"
                    f"  recommended  : {s['recommend']}\n"
                    f"  higher/lower : {s['effect']}")
    for c in COLUMNS:
        if name == c["key"]:
            return f"{c['key']}  —  {c['does']}"
    return f"No setting or column named {name!r}. Try explain() to list them all."


def explain_settings() -> str:
    out = ["SETTINGS"]
    for g in ("A", "B", "C"):
        out.append(f"\n[{g}] {_GROUP[g]}")
        for s in SETTINGS:
            if s["group"] == g:
                out.append(f"  {s['form']:28s} {s['does']}")
                out.append(f"  {'':28s} range: {s['range']}  recommended: {s['recommend']}")
    return "\n".join(out)


def explain_columns() -> str:
    return "OUTPUT COLUMNS\n" + "\n".join(f"  {c['key']:22s} {c['does']}" for c in COLUMNS)


def parameters_markdown() -> str:
    """The full reference as Markdown (used to write PARAMETERS.md)."""
    L = ["# tpattern parameters and outputs",
         "",
         "Every setting and output column, with what it does, its range, the recommended "
         "value, and what higher or lower means. Generated from `tpattern/reference.py`, "
         "which is also the source for the tutorial's tables, the Colab form labels and "
         "`tpattern.explain()`.", ""]
    for g in ("A", "B", "C"):
        L += [f"## {_GROUP[g]}", "",
              "| Setting (form name / `Config`) | What it does | Range | Recommended | Higher / lower |",
              "|---|---|---|---|---|"]
        for s in SETTINGS:
            if s["group"] == g:
                L.append(f"| **{s['form']}** / `{s['key']}` | {s['does']} | {s['range']} "
                         f"| {s['recommend']} | {s['effect']} |")
        L.append("")
    L += ["## Output columns", "",
          "| Column | What it is |", "|---|---|"]
    for c in COLUMNS:
        L.append(f"| `{c['key']}` | {c['does']} |")
    L.append("")
    return "\n".join(L)
