"""
Data diagnostics — is the analytic (Poisson/NX-T) null even valid here?
======================================================================

The critical-interval test's analytic p-value rests on a specific assumption:
under the null, an event type's occurrences are scattered as a *homogeneous
Poisson process* over the observation window — equivalently, given N events in
a window [start, end], their times are distributed like N independent Uniform
draws on that window. The NX/T baseline density (N_x / T) is only the correct
null rate if that holds.

Rather than assume it, we test it, and let the result choose the method:

  * If the times look uniform/Poisson  -> the analytic per-window test is
    calibrated; we then only need to correct for the *selection* over windows
    and pairs (an analytic multiple-comparison correction).
  * If the times are clustered/over-dispersed -> the analytic p is miscalibrated
    and we MUST calibrate significance against surrogates end to end.

Two complementary checks:

1. Conditional-uniformity (Kolmogorov–Smirnov). For each event type, map every
   occurrence to its position within its own window, u = (t - start)/(end-start)
   in [0,1], pool across observations, and KS-test against Uniform(0,1). This is
   the exact test of the "given N events, times ~ Uniform" property of a
   homogeneous Poisson process. Rejection => not Poisson-uniform.

2. Index of dispersion. For each event type, take its per-observation counts and
   form D = var/mean. A Poisson count has D = 1; D > 1 indicates clustering
   (over-dispersion), D < 1 under-dispersion. Reported with a chi-square test.

`mean_u` (average within-window position) is also reported: values well above
0.5 mean the event type concentrates late in the sequence (e.g. shots), a direct
sign the uniform assumption fails.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from scipy.stats import kstest, chi2


@dataclass
class TypeDiagnostic:
    event: str
    n: int                    # total occurrences
    n_obs: int                # observations containing it
    mean_u: float             # mean within-window position (0..1); 0.5 = uniform
    ks_stat: float            # KS distance from Uniform(0,1)
    ks_p: float               # KS p-value (small => not uniform)
    dispersion: float         # var/mean of per-observation counts (1 => Poisson)
    disp_p: float             # chi-square p for dispersion != 1


def within_type_diagnostics(observations, min_count: int = 20) -> list[TypeDiagnostic]:
    """Run the conditional-uniformity and dispersion checks per event type."""
    positions: dict[str, list[float]] = defaultdict(list)
    counts: dict[str, list[int]] = defaultdict(list)

    for o in observations:
        span = max(o.end - o.start, 1)
        per_obs_count: dict[str, int] = defaultdict(int)
        for t, ev in o.events:
            u = (t - o.start) / span
            positions[ev].append(min(max(u, 0.0), 1.0))
            per_obs_count[ev] += 1
        # record a count for every type seen anywhere, including zeros later
        for ev, c in per_obs_count.items():
            counts[ev].append(c)

    out: list[TypeDiagnostic] = []
    n_obs_total = len(observations)
    for ev, us in positions.items():
        n = len(us)
        if n < min_count:
            continue
        arr = np.asarray(us)
        ks_stat, ks_p = kstest(arr, "uniform")     # vs Uniform(0,1)

        # Dispersion across ALL observations (missing => 0 occurrences): place the
        # observed nonzero counts, the rest stay 0.
        cc = np.array(counts[ev] + [0] * (n_obs_total - len(counts[ev])))
        mean = cc.mean()
        var = cc.var(ddof=1)
        disp = var / mean if mean > 0 else float("nan")
        # chi-square test that dispersion == 1 (var == mean): statistic
        # (n_obs-1)*D ~ chi2_{n_obs-1} under Poisson.
        dof = n_obs_total - 1
        stat = dof * disp
        disp_p = float(2 * min(chi2.cdf(stat, dof), 1 - chi2.cdf(stat, dof)))

        out.append(TypeDiagnostic(
            event=ev, n=n, n_obs=len(counts[ev]),
            mean_u=float(arr.mean()), ks_stat=float(ks_stat), ks_p=float(ks_p),
            dispersion=float(disp), disp_p=disp_p,
        ))
    out.sort(key=lambda d: -d.n)
    return out


def summarise(diags: list[TypeDiagnostic], alpha: float = 0.05) -> dict:
    """High-level verdict across event types."""
    n = len(diags)
    non_uniform = sum(1 for d in diags if d.ks_p < alpha)
    overdispersed = sum(1 for d in diags if d.dispersion > 1 and d.disp_p < alpha)
    return {
        "n_types_tested": n,
        "n_non_uniform": non_uniform,
        "frac_non_uniform": non_uniform / n if n else float("nan"),
        "n_overdispersed": overdispersed,
        "mean_dispersion": float(np.mean([d.dispersion for d in diags])) if n else float("nan"),
        "verdict": (
            "NON-POISSON: analytic null miscalibrated -> use surrogate calibration"
            if n and non_uniform / n > 0.5 else
            "Approximately Poisson: analytic test with selection correction may suffice"
        ),
    }
