"""
Machine-generated Methods statement — the settings *and their semantics*.
=========================================================================

The single most transparent thing an open implementation can do is state, in full,
not only *which* settings were used but *what each one does*. Reporting a value
("frequent-event exclusion = 1.50") does not make a result reproducible if the
value's behaviour is hidden — two tools can read the same number and act
differently (see the note's Section 3.1). So `methods_text()` emits a complete,
paste-ready Methods paragraph in which every parameter is accompanied by its
operational definition, generated from the actual `Config` that was run.

    from tpattern import methods_text
    print(methods_text(config, observations=obs, calibration=result))
"""

from __future__ import annotations

from . import __version__ as VERSION   # single source of truth (pyproject/__init__)
CONCEPT_DOI = "10.5281/zenodo.21397543"


def methods_text(config, *, observations=None, calibration=None,
                 cite: bool = True) -> str:
    """Return a Methods-section description of a tpattern analysis.

    Every setting is stated with its operational definition, so the parameter
    *semantics* travel with the analysis, not merely their values. Pass the
    `observations` to include the sample size and total observation time, and a
    `CalibrationResult` to describe the surrogate null and error control.
    """
    s = []

    # --- provenance ---
    if cite:
        s.append(
            f"T-pattern detection was performed with tpattern (v{VERSION}; "
            f"Callaway, 2026; https://doi.org/{CONCEPT_DOI}), an open-source "
            f"implementation of Magnusson's (2000) T-pattern algorithm.")
    else:
        s.append("T-pattern detection was performed with tpattern, an open-source "
                 "implementation of Magnusson's (2000) T-pattern algorithm.")

    # --- data ---
    if observations is not None:
        n_obs = len(observations)
        n_ev = sum(len(o.events) for o in observations)
        T = sum(max(o.end - o.start, 1) for o in observations)
        s.append(f"The sample comprised {n_obs} observations containing {n_ev} "
                 f"event occurrences over {T} time units of total observation window.")

    # --- core detection ---
    s.append(
        f"For each ordered pair of event types (A, B), the critical interval was the "
        f"largest time window in which B followed A more often than expected under the "
        f"NX/T baseline, where the baseline is the probability of at least one B in a "
        f"window of that width given B's overall rate; significance was the upper-tail "
        f"binomial probability of the observed number of A-to-B matches, thresholded at "
        f"α = {config.alpha}. Occurrences were matched one to one by greedy interval "
        f"scheduling, and each event occurrence could fill at most one role within a "
        f"pattern (distinct-token rule). Patterns were built bottom-up into a binary "
        f"hierarchy and were required to recur at least {config.min_occurrence} times.")

    # --- frequent-event exclusion (the setting whose semantics matter most) ---
    if getattr(config, "exclude_events", None) is not None:
        ex = config.exclude_events
        if ex:
            s.append(f"The following event types were excluded from pattern "
                     f"construction (retained for baseline counts only): "
                     f"{', '.join(ex)}.")
        else:
            s.append("No event types were excluded from pattern construction.")
    elif getattr(config, "freq_exclude", None) is not None:
        s.append(
            f"Event types whose mean number of occurrences per observation exceeded "
            f"{config.freq_exclude} were excluded from building patterns (the "
            f"frequent-event exclusion); they were retained in the univariate baseline "
            f"counts. Note that this threshold is defined on mean occurrences per "
            f"observation.")
    else:
        s.append("No frequent-event exclusion was applied; all event types were "
                 "eligible to build patterns.")

    # --- concurrency handling ---
    if getattr(config, "min_lag", 0) and config.min_lag >= 1:
        s.append(
            f"A genuine temporal gap of at least {config.min_lag} time unit(s) was "
            f"required between two linked events (min_lag = {config.min_lag}); events "
            f"sharing a timestamp were therefore treated as co-occurrence and excluded "
            f"from directional pattern detection.")
    else:
        s.append(
            "Events sharing a timestamp were permitted to form directional links "
            "(min_lag = 0); where timestamps are coarsely resolved this treats "
            "co-timed events as ordered, and such links should be read as "
            "co-occurrence rather than sequence.")

    # --- reduction / pruning options ---
    if getattr(config, "completeness", True):
        s.append("Patterns whose every occurrence was contained within a longer "
                 "detected pattern were removed (completeness competition).")
    if getattr(config, "lumping_factor", None) is not None:
        s.append(f"A lumping factor of {config.lumping_factor} was applied: when a "
                 f"pair (A, B) formed with a forward conditional probability above this "
                 f"value, the dependent terminal was removed from the remaining search.")
    if getattr(config, "min_samples_frac", None) is not None:
        s.append(f"Patterns were additionally required to occur in at least "
                 f"{config.min_samples_frac:.0%} of observations.")

    # --- calibration / significance ---
    if calibration is not None:
        null_name = {"profile": "profile-preserving", "rotation": "rotation",
                     "shuffle": "shuffling"}.get(calibration.null, calibration.null)
        s.append(
            f"Every detected pattern was then tested against a {null_name} surrogate "
            f"null: {calibration.B} surrogate datasets were generated and run through "
            f"the identical detection pipeline, giving a Monte-Carlo empirical p-value "
            f"per pattern (so the test is automatically corrected for the selection "
            f"over candidate intervals). Because the empirical p-value cannot fall "
            f"below 1/({calibration.B}+1), family-wise claims require the surrogate "
            f"count to be raised accordingly. Multiplicity was controlled by the "
            f"Benjamini-Hochberg false-discovery rate (q ≤ {calibration.q_target}) "
            f"and, for confirmatory claims, the Holm family-wise error rate "
            f"(α = {calibration.alpha}), each stratified by pattern level.")

    if cite:
        s.append(
            f"The analysis is fully reproducible from the archived software "
            f"(https://doi.org/{CONCEPT_DOI}); the settings above, including each "
            f"parameter's operational definition, are emitted by the software itself.")

    return " ".join(s)
