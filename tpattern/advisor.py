"""
Method advisor — inspect the data, recommend the choices, articulate the method.
================================================================================

The tool exposes exactly three *questions* (not tuning knobs): which null, whether
to require a genuine lag, and which error-rate control. Rather than leave the user
to guess (THEME's failing), the advisor measures the properties of THIS dataset
that determine each choice, recommends one, and writes the sentence that justifies
it — so the Methods section is generated from the data, not asserted.

  1. Null (N1 rotation/shuffle vs N2 profile-preserving)
     Driver: does each event type have its own marginal temporal profile?
     - Measured by conditional-uniformity (KS vs Uniform of within-window
       positions). If most types are non-uniform, marginal timing is real and
       would masquerade as coupling under N1, so N2 is required. If types are
       ~uniform, N1 and N2 coincide and the choice is moot.

  2. Minimum lag (0 = concurrency allowed vs >=1 = genuine sequence only)
     Driver: how often do consecutive events share a timestamp, and at what
     resolution? A high same-unit co-occurrence fraction means within-unit order
     is undefined, so directional patterns need a real lag.

  3. Error control (FWER confirmatory vs FDR exploratory)
     Driver: this is primarily the user's claim type, but sample size informs
     power. We report both and recommend FDR for discovery, FWER for a small
     number of strong confirmatory claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .diagnostics import within_type_diagnostics, summarise


@dataclass
class Choice:
    option: str
    recommended: str
    rationale: str                       # technical justification (for the methods)
    plain: str = ""                      # the same reason in plain English
    evidence: dict = field(default_factory=dict)


@dataclass
class Recommendation:
    n_obs: int
    n_events: int
    choices: list[Choice]
    notes: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = [f"Dataset: {self.n_obs} observations, {self.n_events} events\n"]
        for c in self.choices:
            lines.append(f"[{c.option}]  ->  {c.recommended}\n    {c.rationale}")
        for n in self.notes:
            lines.append(f"[note]  {n}")
        return "\n".join(lines)

    def methods_text(self) -> str:
        """A ready-to-adapt Methods paragraph, grounded in the measured values."""
        return " ".join(c.rationale for c in self.choices)


def _resolution_stats(observations) -> dict:
    """Timestamp resolution and same-unit co-occurrence rate."""
    min_gap = None
    same = 0
    total = 0
    for o in observations:
        ts = sorted(t for t, _ in o.events)
        for i in range(len(ts) - 1):
            total += 1
            d = ts[i + 1] - ts[i]
            if d == 0:
                same += 1
            elif min_gap is None or d < min_gap:
                min_gap = d
    return {
        "min_nonzero_gap": min_gap,
        "same_timestamp_frac": (same / total) if total else 0.0,
        "n_consecutive": total,
    }


def recommend(observations, *, min_count: int = 15,
              uniformity_alpha: float = 0.05) -> Recommendation:
    """Inspect the data and recommend null, min_lag and error-control, with text."""
    n_obs = len(observations)
    n_events = sum(len(o.events) for o in observations)

    # --- Null choice: marginal temporal structure? ---
    diag = within_type_diagnostics(observations, min_count=min_count)
    summ = summarise(diag, alpha=uniformity_alpha)
    frac_nu = summ.get("frac_non_uniform", 0.0)
    # illustrative extreme (type furthest from centred placement)
    extreme = max(diag, key=lambda d: abs(d.mean_u - 0.5), default=None)
    ex_txt = ""
    if extreme is not None:
        where = "late" if extreme.mean_u > 0.5 else "early"
        ex_txt = (f" (e.g. {extreme.event} concentrated {where} in the sequence, "
                  f"mean position {extreme.mean_u:.2f})")

    if summ["n_types_tested"] and frac_nu > 0.5:
        null_choice = Choice(
            "Null", "N2 profile-preserving",
            rationale=(f"{summ['n_non_uniform']} of {summ['n_types_tested']} event "
                       f"types deviated from uniform temporal placement "
                       f"(KS p<{uniformity_alpha}){ex_txt}, so the profile-preserving "
                       f"null (N2) was used to isolate cross-event coupling from each "
                       f"type's marginal timing; the rotation null (N1) is reported "
                       f"alongside to quantify the marginal-timing contribution. The "
                       f"two nulls also pose different questions: N1 tests whether any "
                       f"temporal structure is present, N2 whether events are coupled "
                       f"beyond their own timing (the usual T-pattern claim), so N2 is "
                       f"recommended here; choose N1 if your question is only whether "
                       f"structure exists."),
            plain=("<b>Testing patterns against chance — without being fooled by "
                   "timing.</b> Some actions naturally tend to happen at particular "
                   "points (for example, shots come late in a move), so two actions can "
                   "look 'linked' simply because they tend to occur at similar times — "
                   "not because one leads to the other. To guard against this, we "
                   "compare each of your patterns against many reshuffled copies of your "
                   "data that keep each action's own natural timing but scramble the "
                   "links between actions; a pattern is kept only if it happens more "
                   "often than in those reshuffles. <i>Why it's good:</i> the patterns "
                   "you end up with reflect genuine connections between actions, not "
                   "accidents of timing."),
            evidence={"frac_non_uniform": frac_nu, **summ},
        )
    else:
        null_choice = Choice(
            "Null", "N1 rotation (N2 confirms)",
            rationale=(f"Only {summ.get('n_non_uniform',0)} of "
                       f"{summ.get('n_types_tested',0)} event types showed marginal "
                       f"temporal structure, so the rotation (N1) and profile-preserving "
                       f"(N2) nulls effectively coincide; N1 was used with N2 reported "
                       f"to confirm equivalence."),
            plain=("How we test against chance: your actions are fairly evenly spread "
                   "in time, so we compare each pattern to simple time-shifted copies "
                   "of your data — a fair test when timing isn't skewed."),
            evidence={"frac_non_uniform": frac_nu, **summ},
        )

    # --- Minimum lag: resolution and co-occurrence ---
    res = _resolution_stats(observations)
    stf = res["same_timestamp_frac"]
    gap = res["min_nonzero_gap"]
    if stf > 0.10:
        lag_choice = Choice(
            "Minimum lag", "min_lag = 1 (require genuine lag)",
            rationale=(f"{stf:.0%} of consecutive events shared a timestamp at the "
                       f"data's resolution ({gap} time-units minimum gap), so order "
                       f"within a unit is undefined; a genuine lag was required "
                       f"(min_lag=1) and same-unit co-occurrences were tabulated "
                       f"separately as concurrency rather than sequence."),
            plain=(f"<b>Is it a sequence, or two things happening at once?</b> "
                   f"{stf:.0%} of your events share the exact same timestamp — coded at "
                   f"the same instant (e.g. the same video frame). <i>Why this "
                   f"matters:</i> when two actions happen at the same moment, there is no "
                   f"way to know which came first, so treating one as a 'follow-on' from "
                   f"the other would invent an order that isn't really in your data and "
                   f"could turn things-happening-together into fake sequences. <i>What we "
                   f"do:</i> we count one action as following another only when there is "
                   f"a real gap in time between them; same-instant actions are reported "
                   f"as happening together, not as a sequence. <i>Why it's good:</i> "
                   f"it's a safeguard — a few apparent patterns built only on "
                   f"same-instant events drop out (correctly, because they were never "
                   f"sequences), so your conclusions are stronger, not weaker."),
            evidence=res,
        )
    else:
        lag_choice = Choice(
            "Minimum lag", "min_lag = 0 (concurrency negligible)",
            rationale=(f"Only {stf:.0%} of consecutive events shared a timestamp, so "
                       f"concurrency is negligible and no minimum lag was imposed."),
            plain=(f"<b>Is it a sequence, or two things happening at once?</b> Only "
                   f"{stf:.0%} of your events share a timestamp, so their order is "
                   f"reliable — we can trust which came first — and every event is "
                   f"kept."),
            evidence=res,
        )

    # --- Error control ---
    err_choice = Choice(
        "Error control", "FDR primary, FWER reported",
        rationale=(f"Across {n_obs} observations, pattern significance was calibrated "
                   f"against the null and controlled by false-discovery rate "
                   f"(Benjamini-Hochberg, q=0.05) for discovery, with family-wise "
                   f"control (alpha=0.005) additionally reported for confirmatory claims."),
        plain=("<b>Guarding against false alarms.</b> When many patterns are tested at "
               "once, some will look 'significant' just by luck. We use the "
               "<b>false-discovery rate (FDR)</b> — a standard method that keeps the "
               "share of these lucky flukes among your flagged results low (under 5%). "
               "<i>Impact:</i> the patterns marked 'robust' are ones you can rely on, "
               "not chance findings. A stricter check (the family-wise rate) is also "
               "reported for when you want to be extra cautious about one specific "
               "pattern."),
        evidence={"n_obs": n_obs},
    )

    # --- Frequent-event exclusion (a detection-time choice; matches Config.freq_exclude) ---
    # A near-ubiquitous event type links to almost everything, so it acts as a universal
    # connector and inflates the pattern hierarchy. The default excludes any type whose mean
    # occurrences per observation exceed 1.50 from *building* patterns (they stay in Level 0).
    # This is consequential, so the advisor surfaces it rather than leaving it a silent default.
    threshold = 1.50
    totals: dict[str, int] = {}
    for o in observations:
        for _, ev in o.events:
            totals[ev] = totals.get(ev, 0) + 1
    means = {ev: totals[ev] / n_obs for ev in totals} if n_obs else {}
    frequent = sorted((ev for ev, m in means.items() if m > threshold),
                      key=lambda e: -means[e])
    if frequent:
        lst = ", ".join(f"{e} ({means[e]:.2f}/obs)" for e in frequent)
        freq_choice = Choice(
            "Frequent-event exclusion",
            f"exclude {len(frequent)} type(s) from pattern-building (default)",
            rationale=(f"{len(frequent)} event type(s) occur more than {threshold} times per "
                       f"observation on average and are excluded by default from building "
                       f"multi-event patterns (they remain in the Level-0 univariate set): "
                       f"{lst}. Excluding a near-ubiquitous event stops it acting as a universal "
                       f"connector and inflating the hierarchy; retaining it "
                       f"(Config(exclude_events=[]), or a higher freq_exclude) keeps its "
                       f"connector patterns at the cost of combinatorial growth. Because this "
                       f"materially changes the pattern set, it is reported here rather than "
                       f"applied silently."),
            plain=("<b>Very common events are set aside from pattern-building.</b> An event that "
                   "happens many times in almost every sequence (here: " + ", ".join(frequent) +
                   ") links to nearly everything, so leaving it in would flood the results with "
                   "patterns that are really just 'this common event, then anything'. By default "
                   "we keep such events in the counts but not in the built patterns. <i>Why it "
                   "matters:</i> it keeps the patterns meaningful; if that event is central to "
                   "your question you can choose to keep it in."),
            evidence={"threshold": threshold, "frequent": {e: means[e] for e in frequent}},
        )
    else:
        freq_choice = Choice(
            "Frequent-event exclusion", "none needed",
            rationale=(f"No event type exceeds {threshold} occurrences per observation on "
                       f"average, so none is excluded from pattern-building."),
            plain=("No single event is common enough to swamp the patterns, so every event type "
                   "is kept in the analysis."),
            evidence={"threshold": threshold, "frequent": {}},
        )

    # --- Minimum occurrence (detection floor; matches Config.min_occurrence) ---
    min_occ_choice = Choice(
        "Minimum occurrence", "3 (the field floor)",
        rationale=("A pattern is kept only if it recurs at least this many times (default 3, the "
                   "T-pattern convention); below three occurrences the occurrence-based surrogate "
                   "test is too coarse to calibrate. Impact of raising it: fewer but "
                   "better-supported patterns — it removes the near-threshold tail (which "
                   "calibration discards anyway) and shrinks the multiple-comparison family, at "
                   "the cost of missing genuinely rare structure. Lowering it below three is not "
                   "recommended."),
        plain=("<b>How many times a chain must repeat to count.</b> The default is three. "
               "<i>Raise it</i> to report only patterns that recur often and drop rare, borderline "
               "ones; <i>lowering</i> is not advised — two or three occurrences is already the "
               "smallest number the chance test can judge."),
        evidence={"min_occurrence": 3, "n_obs": n_obs},
    )

    # --- Number of surrogates B (Monte-Carlo resolution; matches calibrate's B) ---
    B_choice = Choice(
        "Number of surrogates (B)", "200 to screen; thousands to confirm one pattern",
        rationale=("The Monte-Carlo empirical p-value cannot fall below 1/(B+1), so B sets the "
                   "finest significance any single pattern can reach. B=200 is ample for "
                   "false-discovery screening; a family-wise confirmatory claim needs 1/(B+1) "
                   "below the family threshold alpha/m — i.e. B greater than m/alpha — which for a "
                   "typical pattern family is in the thousands. Impact of raising B: a lower "
                   "p-floor and a smoother empirical p, at a runtime cost that grows linearly in "
                   "B; too small a B silently caps significance and can leave a real pattern "
                   "unconfirmable."),
        plain=("<b>How many reshuffled datasets to test against.</b> More surrogates give a finer, "
               "more trustworthy p-value but are proportionally slower. <i>Use about 200</i> to "
               "screen many patterns; <i>raise into the thousands</i> to confirm one specific "
               "pattern, because the smallest possible p-value is 1 divided by (B+1)."),
        evidence={"floor_at_200": 1/201, "floor_at_2000": 1/2001},
    )

    # --- diagnostic (reported, not recommended): same-instant duplicate records ---
    notes = []
    n_dup = 0
    for o in observations:
        seen = set()
        for t, ev in o.events:
            if (ev, t) in seen:
                n_dup += 1
            else:
                seen.add((ev, t))
    if n_dup:
        res = _resolution_stats(observations)
        gap = res.get("min_nonzero_gap")
        coarse = (f" Your finest inter-event gap is {gap} time units, so if that resolution is "
                  f"coarse for your data these may be genuinely distinct events; set "
                  f"collapse_duplicates=False to keep them.") if gap and gap > 1 else ""
        notes.append(
            f"{n_dup} same-instant duplicate record(s) (same event type at an identical timestamp) "
            f"were found and are collapsed to one point by default (collapse_duplicates): two records "
            f"at the same instant occupy one point and retaining both would inflate that type's "
            f"baseline rate.{coarse}")

    return Recommendation(n_obs=n_obs, n_events=n_events,
                          choices=[freq_choice, min_occ_choice, null_choice, lag_choice,
                                   err_choice, B_choice],
                          notes=notes)
