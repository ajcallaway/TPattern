"""
Group contrast — does a pattern occur more in one group than another?
=====================================================================

Promotes the recurring "winner vs loser" / "goal vs non-goal" analysis to a
one-call library function. Detects T-patterns on the pooled sample, then for each
pattern counts the observations in each group that contain it and tests the
difference with Fisher's exact test and an odds ratio with a 95% confidence
interval. The output feeds `forest_plot` directly.

    from tpattern import group_contrast, forest_plot
    rows = group_contrast(observations, group_of=winner_or_loser)
    forest_plot(contrast_items(rows), "contrast.png")

`group_of` is either a dict {observation_name: label} or a callable taking an
Observation and returning its label. Exactly two groups are compared.
"""

from __future__ import annotations

import math

from .detect import Config, Engine


def _or_ci(a, b, c, d):
    """Odds ratio and 95% CI for the 2x2 table [[a, b], [c, d]] with a Haldane
    +0.5 correction so zero cells don't blow up."""
    a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    orr = (a * d) / (b * c)
    se = math.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return orr, math.exp(math.log(orr) - 1.96 * se), math.exp(math.log(orr) + 1.96 * se)


def group_contrast(observations, group_of, config: Config | None = None, *,
                   groups=None, min_count: int = 5):
    """Compare T-pattern occurrence between two groups of observations.

    Returns a list of row dicts (one per pattern), sorted by p-value, each with
    the per-group counts, odds ratio, 95% CI, Fisher p, and which group the
    pattern is more common in. Counts are of *observations* containing the pattern
    at least once (not raw occurrences), so the comparison is a clean 2x2.
    """
    try:
        from scipy.stats import fisher_exact
    except ImportError as e:  # pragma: no cover
        raise ImportError("group_contrast needs scipy") from e
    config = config or Config()

    def label(i):
        o = observations[i]
        return group_of(o) if callable(group_of) else group_of.get(o.name)

    labels = [label(i) for i in range(len(observations))]
    present = [g for g in dict.fromkeys(labels) if g is not None]
    groups = groups or sorted(present, key=str)
    if len(groups) != 2:
        raise ValueError(f"group_contrast compares exactly two groups; found {groups}. "
                         "Give a group_of that yields two labels (others -> None).")
    gA, gB = groups
    nA = sum(1 for x in labels if x == gA)
    nB = sum(1 for x in labels if x == gB)
    if not nA or not nB:
        raise ValueError(f"a group is empty ({gA}: {nA}, {gB}: {nB}).")

    pats = [p for p in Engine(observations, config).detect() if p.level >= 1]
    rows = []
    for p in pats:
        if p.N < min_count:
            continue
        obs_with = {inst.obs for inst in p.instances}
        a = sum(1 for i in obs_with if labels[i] == gA)
        b = sum(1 for i in obs_with if labels[i] == gB)
        orr, lo, hi = _or_ci(a, nA - a, b, nB - b)
        _, pval = fisher_exact([[a, nA - a], [b, nB - b]])
        rows.append({
            "pattern": str(p), "signature": p.signature(), "N": p.N,
            f"{gA}": f"{a}/{nA}", f"{gB}": f"{b}/{nB}",
            "odds_ratio": round(orr, 2), "ci_low": round(lo, 2),
            "ci_high": round(hi, 2), "p": round(pval, 4),
            "more_common_in": gA if orr > 1 else gB,
        })
    rows.sort(key=lambda r: r["p"])
    return rows


def contrast_items(rows, top: int = 15):
    """Turn group_contrast rows into the item list forest_plot expects."""
    return [{"label": r["pattern"][:42], "or": r["odds_ratio"], "lo": r["ci_low"],
             "hi": r["ci_high"], "p": r["p"]} for r in rows[:top]]
