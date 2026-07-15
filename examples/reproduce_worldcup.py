"""
reproduce_worldcup.py — regenerate the World Cup comparison numbers.
====================================================================

This is the archived reproducibility artifact for the technical-note comparison
between THEME 8 and the open `tpattern` engine on the 2022 World Cup shot-ending
sequences. It recomputes, from the same THEME observation files:

  1. Concordance  — pattern counts by hierarchical level, tpattern vs THEME
                    (THEME figures are the audited manuscript counts).
  2. Calibration  — how many detected patterns survive the surrogate null with
                    Benjamini-Hochberg FDR (q <= .05) and Holm FWER.
  3. Exclusion    — the one substantive divergence: THEME retained interception
                    in the defensive-recovery group; the open mean-per-observation
                    rule excludes it. Re-running with IT retained recovers THEME's
                    interception-mediated recycling loops.

Run:
    python3 reproduce_worldcup.py            # detection + exclusion demo (fast)
    python3 reproduce_worldcup.py --calibrate   # also run the B-surrogate null (~10 min)

All randomness is seeded (see SEED); results are deterministic.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from tpattern import read_sample, Engine, Config, calibrate

SEED = 20260714
BASE = Path(__file__).resolve().parents[1]
GROUPS = {"Goals": "THEME_Goals", "NonGoals": "THEME_NonGoals",
          "DefRecovery": "THEME_Saved"}

# Audited THEME 8 manuscript counts: (total, L0, L1, L2+).
THEME = {"Goals": (37, 19, 15, 3),
         "NonGoals": (118, 31, 64, 23),
         "DefRecovery": (250, 25, 80, 145)}


def counts_by_level(pats):
    lv = Counter(p.level for p in pats)
    l0 = lv.get(0, 0); l1 = lv.get(1, 0)
    l2p = sum(v for k, v in lv.items() if k >= 2)
    return len(pats), l0, l1, l2p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true",
                    help="also run the surrogate null (slow)")
    ap.add_argument("--B", type=int, default=200)
    args = ap.parse_args()

    print("=" * 68)
    print("1. CONCORDANCE — pattern counts, tpattern vs THEME 8")
    print("=" * 68)
    print(f"{'group':13}{'level':10}{'tpattern':>10}{'THEME':>8}")
    detected = {}
    for g, folder in GROUPS.items():
        obs = read_sample(BASE / folder)
        pats = Engine(obs, Config()).detect()
        detected[g] = pats
        tot, l0, l1, l2p = counts_by_level(pats)
        tt, t0, t1, t2 = THEME[g]
        for lab, a, b in [("total", tot, tt), ("L0 univ", l0, t0),
                          ("L1 bivar", l1, t1), ("L2+ higher", l2p, t2)]:
            print(f"{g if lab=='total' else '':13}{lab:10}{a:>10}{b:>8}")
        print("-" * 39)

    print("\n" + "=" * 68)
    print("3. EXCLUSION DIVERGENCE — defensive-recovery, interception retained")
    print("=" * 68)
    obs = read_sample(BASE / "THEME_Saved")
    kept_it = Engine(obs, Config(exclude_events=[])).detect()
    it_loops = [p for p in kept_it if p.has_loop and "Interception" in p.signature()]
    print(f"With the frequent-event rule (default): IT excluded, "
          f"{sum(1 for p in detected['DefRecovery'] if p.level>=1)} composite patterns.")
    print(f"With interception retained (as THEME had it): "
          f"{len(it_loops)} interception-mediated recycling loops recovered, e.g.")
    for p in sorted(it_loops, key=lambda p: -p.N)[:3]:
        print(f"    N={p.N:>3}  {p}")

    if args.calibrate:
        print("\n" + "=" * 68)
        print(f"2. CALIBRATION — surrogate null (profile, B={args.B}), FDR q<=.05")
        print("=" * 68)
        print(f"{'group':13}{'detected(L>=1)':>15}{'FDR keep':>10}{'FWER keep':>11}")
        for g, folder in GROUPS.items():
            obs = read_sample(BASE / folder)
            res = calibrate(obs, Config(), null="profile", B=args.B,
                            alpha=.005, q_target=.05, seed=SEED)
            print(f"{g:13}{len(res.real):>15}{len(res.kept('fdr')):>10}"
                  f"{len(res.kept('fwer')):>11}")
        print("\nNote: at B=200 the Monte-Carlo p-value floor is ~1/(B+1)=.005, so "
              "Holm FWER is\nresolution-limited; FDR is the practical control. "
              "Raise B to the thousands for FWER.")


if __name__ == "__main__":
    main()
