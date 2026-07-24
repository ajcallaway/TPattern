"""
Bout-support sensitivity analysis.
==================================

The "minimum % of samples" / bout-support threshold (``Config.min_samples_frac``)
says: a pattern must appear in at least this fraction of distinct bouts
(observations) to be kept. Internally it becomes

    min_bouts = ceil(min_samples_frac * n_bouts)

and it prunes the search (it is anti-monotone: a longer pattern can only span
fewer bouts than its prefix).

WHY THIS SCRIPT EXISTS
----------------------
Support is a *prevalence* filter, not a significance test. It answers "how
widespread is this pattern?", not "is this pattern more than chance?". Chance is
handled separately, by calibration against a surrogate null with correction for
repeated testing.

That distinction matters, because if you choose the support threshold by looking
at which value gives the nicest downstream result, the threshold has quietly
become a researcher degree of freedom and the downstream result is circular.

The fix is not to guess a better number. It is to:

  1. fix a PRIMARY threshold on grounds independent of the outcome
     (see `choose_primary_threshold` below),
  2. report every objective at every threshold, not just the one that moved,
  3. report each surviving pattern's bout support as a NUMBER, so the reader can
     see prevalence directly instead of inferring it from a cut-off.

Run:
    python support_sensitivity.py events.csv --time-unit ms --obs-start obs_start --obs-end obs_end
"""

from __future__ import annotations

import math
import sys

from tpattern import Config, Engine, calibrate, read_table


# Thresholds to sweep. None = no support filter: detection is unconstrained and
# calibration alone decides significance. This is the cleanest primary, because
# it removes the threshold from the inferential path entirely.
THRESHOLDS = [None, 0.10, 0.25]

MIN_OCCURRENCE = 3      # the field floor; also Config's default
B = 200                 # surrogates; raise for a confirmatory (family-wise) claim
SEED = 20260720


def bout_support(pattern, n_bouts):
    """Fraction of distinct bouts (observations) this pattern appears in.

    N (len(pattern.instances)) counts occurrences and can exceed the number of
    bouts, because one bout may contain a pattern several times. Support counts
    DISTINCT bouts, which is what the threshold acts on.
    """
    bouts = {inst.obs for inst in pattern.instances}
    return len(bouts), len(bouts) / n_bouts


def choose_primary_threshold(n_bouts, min_occurrence=MIN_OCCURRENCE):
    """Report what each candidate threshold actually implies for THIS sample.

    A threshold is only meaningful if it bites above the minimum-occurrence
    floor. If ceil(frac * n_bouts) <= min_occurrence, the threshold is inert:
    the occurrence floor is already doing the work, and comparing that threshold
    against another is comparing two labels for the same filter.
    """
    print(f"\nSample: {n_bouts} bouts. Minimum occurrence floor: {min_occurrence}.")
    print(f"{'threshold':>12}  {'min bouts':>10}  {'status'}")
    for frac in THRESHOLDS:
        if frac is None:
            print(f"{'none':>12}  {0:>10}  calibration alone decides significance")
            continue
        min_bouts = math.ceil(frac * n_bouts)
        if min_bouts <= min_occurrence:
            status = f"INERT (<= floor of {min_occurrence}); not a real constraint"
        else:
            status = "active"
        print(f"{frac:>11.0%}  {min_bouts:>10}  {status}")


def run_one(observations, frac, n_bouts):
    """Detect + calibrate at one support threshold; return a summary dict."""
    cfg = Config(min_samples_frac=frac, min_occurrence=MIN_OCCURRENCE, min_lag=1)

    detected = [p for p in Engine(observations, cfg).detect() if p.level >= 1]
    result = calibrate(observations, cfg, null="profile", B=B,
                       q_target=0.05, seed=SEED)
    survivors = sorted(result.kept("fdr"), key=lambda c: c.fdr_q)

    rows = []
    for c in survivors:
        n_bt, supp = bout_support(c.pattern, n_bouts)
        rows.append({
            "signature": c.pattern.signature(),
            "N": c.N,
            "bouts": n_bt,
            "support": supp,
            "p_emp": c.p_emp,
            "q": c.fdr_q,
        })
    return {"frac": frac, "detected": len(detected),
            "survivors": len(survivors), "rows": rows}


def main(path, time_unit="s", obs_start=None, obs_end=None):
    # These two structural inputs change every result and neither announces itself.
    # Reading milliseconds as seconds rescales every lag; omitting the observation
    # window makes T the span of the first to last event rather than the real
    # window, which shifts every baseline probability. So warn rather than default
    # silently.
    if not (obs_start and obs_end):
        print("WARNING: no observation-window columns given, so T is being inferred\n"
              "         from the first and last event of each observation. T is the\n"
              "         denominator of the baseline, so this changes every result.\n"
              "         Pass --obs-start/--obs-end if your data have real windows.\n")
    observations = read_table(path, time_unit=time_unit,
                              obs_start=obs_start, obs_end=obs_end)
    n_bouts = len(observations)
    print(f"Loaded {n_bouts} bouts (time_unit={time_unit!r}, "
          f"window={'from data' if obs_start else 'inferred from events'}).")

    choose_primary_threshold(n_bouts)

    results = [run_one(observations, frac, n_bouts) for frac in THRESHOLDS]

    print("\n" + "=" * 78)
    print("SENSITIVITY: detection and survival by bout-support threshold")
    print("=" * 78)
    print(f"{'threshold':>12}  {'detected':>9}  {'survive FDR':>12}")
    for r in results:
        label = "none" if r["frac"] is None else f"{r['frac']:.0%}"
        print(f"{label:>12}  {r['detected']:>9}  {r['survivors']:>12}")

    for r in results:
        label = "none" if r["frac"] is None else f"{r['frac']:.0%}"
        print(f"\n--- surviving patterns at threshold = {label} ---")
        if not r["rows"]:
            print("  (none survived false-discovery control)")
        for row in r["rows"]:
            print(f"  {row['signature']:<50} N={row['N']:>3}  "
                  f"bouts={row['bouts']:>3} ({row['support']:.1%})  "
                  f"p={row['p_emp']:.4f}  q={row['q']:.3f}")

    # Stability: which patterns survive at EVERY threshold? Those are the ones
    # whose reportability does not depend on the choice.
    sets = [{row["signature"] for row in r["rows"]} for r in results]
    stable = set.intersection(*sets) if sets else set()
    unstable = set.union(*sets) - stable if sets else set()

    print("\n" + "=" * 78)
    print("STABILITY")
    print("=" * 78)
    print(f"Survive at ALL thresholds ({len(stable)}): "
          "report these as the primary result; the threshold is immaterial to them.")
    for s in sorted(stable):
        print(f"  + {s}")
    print(f"\nThreshold-DEPENDENT ({len(unstable)}): "
          "these are a fragility finding, not a headline result.")
    for s in sorted(unstable):
        where = [("none" if r["frac"] is None else f"{r['frac']:.0%}")
                 for r in results if s in {row["signature"] for row in r["rows"]}]
        print(f"  ? {s}   (survives only at: {', '.join(where)})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Bout-support sensitivity analysis.")
    ap.add_argument("events_csv")
    ap.add_argument("--time-unit", default="s", choices=["s", "ms"],
                    help="unit of the time columns in your file (default: s)")
    ap.add_argument("--obs-start", default=None,
                    help="column giving each observation's true start time")
    ap.add_argument("--obs-end", default=None,
                    help="column giving each observation's true end time")
    a = ap.parse_args()
    main(a.events_csv, time_unit=a.time_unit,
         obs_start=a.obs_start, obs_end=a.obs_end)
