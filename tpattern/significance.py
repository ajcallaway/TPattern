"""
Surrogate-calibrated significance — the mathematically defensible keep/reject.
=============================================================================

The analytic critical-interval p-value is not trustworthy here (see
diagnostics.py: the data are strongly non-Poisson, and the detector selects the
best of many windows and pairs). So we do not threshold it directly. Instead we
calibrate every detected pattern against surrogate data run through the
*identical* detection pipeline. Because the surrogate detection performs the same
window/pair selection, the comparison is automatically corrected for selection
bias; because the surrogate preserves each event type's real marginal structure
(profile-preserving null), it is also corrected for the wrong independence
assumption.

Per Andy's decision we compute TWO statistics side by side:

1. Signature-matched empirical p (primary, interpretable). For each real pattern,
   how often does the *same* pattern (identical signature) arise in the
   surrogates with an occurrence count at least as high?
       p_emp = (1 + #surrogates with that signature at N >= observed) / (1 + B)
   This asks, directly, "could chance have produced THIS pattern this strongly?"
   The +1/+1 is the standard Monte-Carlo correction (never reports p = 0).

2. Analytic strength (secondary). s = -log10(best-window binomial p), calibrated
   the same way against the pooled surrogate strength distribution. Reported for
   comparison / robustness, not as the primary decision.

Two error-rate controls, both stratified by pattern level (the search space, and
hence the null, differs by level):

* FWER (family-wise) — a real pattern is kept only if its empirical p survives a
  Holm–Bonferroni step-down at level alpha across the patterns of its level.
  Controls P(any false pattern) <= alpha. Conservative; confirmatory.
* FDR (false discovery rate) — Benjamini–Hochberg on the empirical p-values at
  q_target. Controls the expected proportion of false patterns; more powerful,
  for screening.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .detect import Config, Engine
from .randomise import build_profiles, profile_surrogate, randomise_sample
from .pattern import Pattern


def _strength(p: Pattern) -> float:
    pv = p.p_value if p.p_value and p.p_value > 0 else 1e-300
    return -math.log10(pv)


@dataclass
class Calibrated:
    pattern: Pattern
    level: int
    N: int
    ci: tuple
    p_emp: float = 1.0        # signature-matched empirical p (primary)
    strength: float = 0.0     # analytic -log10(p) (secondary)
    p_emp_strength: float = 1.0   # empirical p of the analytic strength
    fwer_keep: bool = False   # Holm on p_emp
    fdr_q: float = 1.0        # Benjamini-Hochberg q on p_emp


@dataclass
class CalibrationResult:
    real: list[Calibrated]
    surrogate_counts: dict     # level -> list of per-surrogate pattern counts
    B: int
    alpha: float
    q_target: float
    null: str

    def kept(self, method: str = "fdr") -> list[Calibrated]:
        if method == "fwer":
            return [c for c in self.real if c.fwer_keep]
        return [c for c in self.real if c.fdr_q <= self.q_target]


def _benjamini_hochberg(items, get_p):
    """Assign BH q-values (in place ordering) to `items` by their p = get_p(x)."""
    m = len(items)
    if m == 0:
        return {}
    order = sorted(range(m), key=lambda i: get_p(items[i]))
    q = [0.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        val = get_p(items[i]) * m / (rank + 1)
        running = min(running, val)
        q[i] = min(1.0, running)
    return {id(items[i]): q[i] for i in range(m)}


def _holm_keep(items, get_p, alpha):
    """Holm–Bonferroni step-down; return set of ids kept at family alpha."""
    m = len(items)
    order = sorted(range(m), key=lambda i: get_p(items[i]))
    kept = set()
    for rank, i in enumerate(order):
        if get_p(items[i]) <= alpha / (m - rank):
            kept.add(id(items[i]))
        else:
            break
    return kept


def calibrate(observations, config: Config | None = None, *,
              null: str = "profile", B: int = 200, alpha: float = 0.005,
              q_target: float = 0.05, seed: int = 20260714) -> CalibrationResult:
    """Detect on real data, then calibrate each pattern against B surrogates."""
    config = config or Config()

    real_pats = [p for p in Engine(observations, config).detect() if p.level >= 1]
    real = [Calibrated(pattern=p, level=p.level, N=p.N, ci=p.ci,
                       strength=_strength(p)) for p in real_pats]

    profiles = build_profiles(observations) if null == "profile" else None
    np_rng = np.random.default_rng(seed)

    # signature-matched: per real signature, how many surrogates reach its N
    sig_N = {p.signature(): p.N for p in real_pats}
    beat_count: dict[str, int] = defaultdict(int)          # count-based
    # analytic-strength: pooled surrogate strengths per level for empirical p
    surr_strengths: dict[int, list[float]] = defaultdict(list)
    surrogate_counts: dict[int, list[int]] = defaultdict(list)
    track_levels = {c.level for c in real}

    for b in range(B):
        if null == "profile":
            surr = profile_surrogate(observations, profiles, np_rng)
        else:
            surr = randomise_sample(observations, null, random.Random(seed + b))
        pats = [p for p in Engine(surr, config).detect() if p.level >= 1]

        best_by_sig: dict[str, int] = {}
        per_level_strength: dict[int, list[float]] = defaultdict(list)
        for p in pats:
            sig = p.signature()
            if p.N > best_by_sig.get(sig, 0):
                best_by_sig[sig] = p.N
            per_level_strength[p.level].append(_strength(p))
        for sig, n_obs in sig_N.items():
            if best_by_sig.get(sig, 0) >= n_obs:
                beat_count[sig] += 1
        for lv in track_levels:
            surr_strengths[lv].extend(per_level_strength.get(lv, []))
            surrogate_counts[lv].append(len(per_level_strength.get(lv, [])))

    # empirical p-values (Monte-Carlo, +1/+1 correction)
    for c in real:
        sig = c.pattern.signature()
        c.p_emp = (1 + beat_count.get(sig, 0)) / (1 + B)
        pool = surr_strengths.get(c.level, [])
        ge = sum(1 for s in pool if s >= c.strength)
        c.p_emp_strength = (1 + ge) / (1 + len(pool)) if pool else 1.0 / (1 + B)

    # per-level FWER (Holm) and FDR (BH) on the primary empirical p
    for lv in track_levels:
        grp = [c for c in real if c.level == lv]
        keep = _holm_keep(grp, lambda c: c.p_emp, alpha)
        qmap = _benjamini_hochberg(grp, lambda c: c.p_emp)
        for c in grp:
            c.fwer_keep = id(c) in keep
            c.fdr_q = qmap[id(c)]

    return CalibrationResult(real=real, surrogate_counts=surrogate_counts,
                             B=B, alpha=alpha, q_target=q_target, null=null)
