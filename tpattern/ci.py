"""
The critical-interval (CI) test — the mathematical core.
========================================================

This is the single statistical test that the whole method is built on. It asks,
for two patterns A and B:

    "Is there a time window [d1, d2] such that, after an occurrence of A, an
     occurrence of B follows within that window *more often than chance would
     predict*?"

If yes, (A B) is a real T-pattern and [d1, d2] is its **critical interval**.

The null hypothesis (Magnusson, 2000)
-------------------------------------
Under H0, A and B are unrelated and B is scattered at random over the observed
time. THEME's "NX/T" baseline states the density of B directly from the data:

    p1 = N_B / T          (probability B occupies any given 1 ms time unit)

    where  N_B = total occurrences of B across the whole sample
           T   = total observed time across the whole sample (sum of windows)

For a candidate window of width  w = d2 - d1 + 1  placed just after an A, the
probability that *at least one* B lands inside it is

    p_hit = 1 - (1 - p1) ** w                                            (Eq. 1)

If A occurs N_A times, and the A's were unrelated to the B's, then the number k
of A's that happen to be followed by a B in the window is Binomial(N_A, p_hit).
So the chance of seeing k *or more* hits by luck is the upper tail

    p_value = P(X >= k),   X ~ Binomial(N_A, p_hit)                      (Eq. 2)

Among all windows whose p_value is below the significance level (0.005 here) and
which contain at least `min_occurrence` hits, we keep the one capturing the
**most occurrences** — the *largest significant* critical interval. This is
Magnusson's notion of the critical interval: the widest window within which B
still follows A significantly more often than chance. It yields the most
*complete* pattern (all real instances), rather than the tightest sub-window.
The significance test itself guards against runaway widening: a wider window has
a higher chance baseline `p_hit`, so it can only stay significant while genuine
hits keep pace. Ties in occurrence-count are broken toward the more significant,
then tighter, interval.

"Free" critical-interval search
-------------------------------
THEME offers "Fast" (d1 forced to 0, only d2 searched) and "Free" (both edges
searched). The paper used Free, so both d1 and d2 range over the set of observed
A→B gaps. Only real observed gaps can change k, so they are the only candidate
edges we ever need to try — this makes the "search all windows" exact, not a
grid approximation.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

import numpy as np
from scipy.special import betainc

from .pattern import Instance, Pattern


def binom_sf(k: int, n: int, p: float) -> float:
    """Upper-tail binomial probability P(X >= k) for X ~ Binomial(n, p).

    Uses the regularised incomplete beta identity
        P(X >= k) = I_p(k, n - k + 1)
    which is a single scalar C call, ~30x faster than scipy.stats.binom.sf and
    numerically identical for our purposes.
    """
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    return float(betainc(k, n - k + 1, p))


@dataclass
class CIResult:
    """Outcome of a successful critical-interval search."""

    d1: int
    d2: int
    p_value: float
    instances: list[Instance]           # the matched (A→B) occurrences

    @property
    def N(self) -> int:
        return len(self.instances)


def _match_obs(a_ends, a_tok, b_ends, b_starts, b_tok, d1, d2, collect):
    """Greedy one-to-one A→B matching within a single observation's window.

    Interval-scheduling greedy: walk A's in end-time order and give each the
    earliest still-unused B whose start lies in [a.end+d1, a.end+d2]. Every event
    is consumed at most once (tracked with a `used` bitmask, allocation-free).

    `used` bit j marks B index j taken. Because A-ends are ascending, the lower
    scan pointer `j0` only moves forward across A's. The distinct-token check is
    only needed when gap == 0 (a B strictly after A's end cannot share an event
    with A); this fast-path skips the frozenset test for the common case.

    If `collect` is False we only count; if True we also return the (start, end,
    tokens) of each matched occurrence.
    """
    nb = len(b_starts)
    used = 0
    j0 = 0
    count = 0
    matched = [] if collect else None
    for ai in range(len(a_ends)):
        ae = a_ends[ai]
        lo = ae + d1
        hi = ae + d2
        while j0 < nb and b_starts[j0] < lo:
            j0 += 1
        j = j0
        while j < nb and b_starts[j] <= hi:
            if not (used >> j) & 1:
                if b_starts[j] > ae or a_tok[ai].isdisjoint(b_tok[j]):
                    used |= 1 << j
                    count += 1
                    if collect:
                        matched.append((ae, ai, j))
                    break
            j += 1
    return (count, matched) if collect else count


def find_critical_interval(
    a: Pattern,
    b: Pattern,
    obs_index: dict[int, tuple],
    total_time: int,
    alpha: float = 0.005,
    min_occurrence: int = 3,
    min_lag: int = 0,
    max_edges: int | None = None,
) -> CIResult | None:
    """Search for the most significant critical interval linking A then B.

    Parameters
    ----------
    a, b : Pattern
        The two patterns to test for an ``A -> B`` relationship.
    obs_index : dict[obs_id -> (a_in_obs, b_in_obs)]
        A- and B-instances grouped by observation, each list sorted by time.
        Grouping by observation enforces that a pattern never spans two files.
    total_time : int
        Sum of all observation window lengths T (denominator of the baseline).
    alpha, min_occurrence : float, int
        THEME's Significance Level and Minimum Occurrence.

    Returns
    -------
    CIResult | None
        The best significant interval, or None if no window qualifies.
    """
    N_A = a.N
    N_B = b.N
    if N_A < min_occurrence or N_B < min_occurrence:
        return None

    p1 = N_B / total_time                          # NX/T baseline density
    if p1 <= 0 or p1 >= 1:
        return None
    # Baseline assumptions (all standard for the analytic T-pattern test, and all
    # relaxed by the surrogate calibration in significance.py, where this p-value
    # serves only as a strength-ordering statistic):
    #   * Homogeneous-Poisson null: p_hit = 1-(1-p1)^w is the discrete-Bernoulli
    #     form of 1-exp(-p1*w); it assumes B is uniformly/independently placed.
    #     The diagnostics module shows this is violated (events are clustered),
    #     which is exactly why final significance is set by surrogates, not here.
    #   * Independent trials: k ~ Binomial(N_A, p_hit) treats the N_A A-instances
    #     as independent, though they share one B pool (greedy consumes B's).
    #   * No right-censoring correction: A-instances near an observation's end
    #     have less than a full window w available, so p_hit is a mild
    #     over-estimate there (slightly anti-conservative).

    # --- Precompute per-observation arrays once (a sorted by end, b by start) ---
    # Also cheaply bound the maximum achievable occurrence count: in each
    # observation at most min(#A, #B) pairs can be formed. If the sum of those
    # caps cannot reach the minimum occurrence, no interval ever will, so we skip
    # the whole search — this prunes the many pattern pairs that barely co-occur.
    per_obs = []
    a_gap_lists: list[list[int]] = []   # per A-occurrence: sorted acceptable B-gaps
    gaps: set[int] = set()
    max_possible = 0
    for a_list, b_list in obs_index.values():
        if not a_list or not b_list:
            continue
        a_srt = sorted(a_list, key=lambda x: x.end)
        b_srt = sorted(b_list, key=lambda x: x.start)
        a_ends = [x.end for x in a_srt]
        a_tok = [x.tokens for x in a_srt]
        a_starts = [x.start for x in a_srt]
        b_starts = [x.start for x in b_srt]
        b_ends = [x.end for x in b_srt]
        b_tok = [x.tokens for x in b_srt]
        obs_id = a_srt[0].obs
        per_obs.append((obs_id, a_ends, a_starts, a_tok, b_ends, b_starts, b_tok))
        max_possible += min(len(a_ends), len(b_ends))
        for ai, ae in enumerate(a_ends):
            row = [bs - ae for k, bs in enumerate(b_starts)
                   if bs - ae >= min_lag and (bs > ae or a_tok[ai].isdisjoint(b_tok[k]))]
            if row:
                row.sort()
                a_gap_lists.append(row)
                gaps.update(row)
    if max_possible < min_occurrence or not gaps:
        return None
    edges = sorted(gaps)
    # For dense event streams the distinct-gap set can be enormous, making the
    # exact O(g^2) window search costly. Optionally subsample to `max_edges`
    # rank-spaced candidate edges (keeping the extremes) — a bounded approximation
    # of the interval boundaries, akin to THEME's non-exhaustive "Free Heuristic".
    if max_edges and len(edges) > max_edges:
        step = len(edges) / max_edges
        idx = sorted({int(i * step) for i in range(max_edges)} | {len(edges) - 1})
        edges = [edges[i] for i in idx]

    # --- Stage 1: cheap count-A upper bound. For each window, count-A = number of
    # A-occurrences with >=1 acceptable B inside it (B reusable). Since greedy
    # (one-to-one) can only match FEWER, count-A >= greedy_k, and significance
    # strengthens with k, so a window that is not count-A-significant can never be
    # greedy-significant. We collect only the count-A-significant windows as
    # candidates — for most pattern pairs there are none, and greedy is skipped
    # entirely. This is an exact gate, not an approximation. ---
    candidates = []  # (countA_k, d1, d2)
    edges_np = np.asarray(edges, dtype=np.int64)
    for i, d1 in enumerate(edges):
        # nearest acceptable B-gap >= d1 for each A-occurrence
        fs = [row[j] for row in a_gap_lists
              if (j := bisect_left(row, d1)) < len(row)]
        if len(fs) < min_occurrence:
            continue
        fs_np = np.sort(np.asarray(fs, dtype=np.int64))
        d2s = edges_np[i:]                                   # candidate right edges
        kA = np.searchsorted(fs_np, d2s, side="right")       # count fs <= d2
        m = kA >= min_occurrence
        if not m.any():
            continue
        d2m, kAm = d2s[m], kA[m]
        w = (d2m - d1 + 1).astype(float)
        p_hit = 1.0 - (1.0 - p1) ** w
        # vectorised P(X >= kA) = I_{p_hit}(kA, N_A - kA + 1)
        pv = betainc(kAm, N_A - kAm + 1, p_hit)
        sig = pv < alpha
        for d2v, kAv in zip(d2m[sig].tolist(), kAm[sig].tolist()):
            candidates.append((int(kAv), d1, int(d2v)))
    if not candidates:
        return None

    # --- Stage 2: exact greedy only on candidate windows, largest count-A first.
    # Once the best confirmed greedy count can't be beaten by a candidate's upper
    # bound, stop. ---
    candidates.sort(key=lambda c: -c[0])
    best_key = None
    best_d = None
    for kA, d1, d2 in candidates:
        if best_key is not None and kA < -best_key[0]:
            break                        # upper bound below best greedy k → done
        k = 0
        for (_oid, a_ends, _as, a_tok, _be, b_starts, b_tok) in per_obs:
            k += _match_obs(a_ends, a_tok, _be, b_starts, b_tok, d1, d2, False)
        if k < min_occurrence:
            continue
        w = d2 - d1 + 1
        p_hit = 1.0 - (1.0 - p1) ** w                      # Eq. 1
        p_value = binom_sf(k, N_A, p_hit)                  # Eq. 2, P(X >= k)
        if p_value >= alpha:
            continue
        key = (-k, p_value, w, d1)
        if best_key is None or key < best_key:
            best_key = key
            best_d = (d1, d2, p_value)

    if best_d is None:
        return None

    # --- Rebuild the matched occurrences for the winning window only. ---
    d1, d2, p_value = best_d
    instances: list[Instance] = []
    for (oid, a_ends, a_starts, a_tok, b_ends, b_starts, b_tok) in per_obs:
        _, matched = _match_obs(a_ends, a_tok, b_ends, b_starts, b_tok, d1, d2, True)
        for (ae, ai, j) in matched:
            instances.append(Instance(
                obs=oid, start=a_starts[ai], end=b_ends[j],
                tokens=a_tok[ai] | b_tok[j],
            ))
    return CIResult(d1=d1, d2=d2, p_value=p_value, instances=instances)
