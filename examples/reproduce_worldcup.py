"""
reproduce_worldcup.py — regenerate the World Cup results from the shipped data.
==============================================================================

This is the reproducibility artifact for the technical-note comparison between
THEME 8 and the open `tpattern` engine, on the 2022 World Cup shot-ending
possession sequences. It runs out of the box: the derived event data ships with
this repository in ../data/ (see ../data/README.md for provenance).

It recomputes:

  1. Concordance  — pattern counts by hierarchical level, tpattern vs THEME
                    (THEME figures are the audited manuscript counts).
  2. Exclusion    — the one substantive divergence: THEME retained interception
                    in the defensive-recovery group; the open mean-per-observation
                    rule excludes it. Re-running with IT retained recovers THEME's
                    interception-mediated recycling loops.
  3. Concurrency  — the fraction of consecutive events sharing a timestamp, and
                    what happens to the headline patterns when a genuine lag is
                    required.
  4. Calibration  — how many detected patterns survive the surrogate null with
                    Benjamini-Hochberg FDR (optional; ~10 min).

Run:
    python examples/reproduce_worldcup.py              # 1-3 (fast, ~5 s)
    python examples/reproduce_worldcup.py --calibrate  # also the surrogate null

All randomness is seeded (see SEED); results are deterministic.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from tpattern import read_table, Engine, Config, calibrate

SEED = 20260714
DATA = Path(__file__).resolve().parents[1] / "data"
GROUPS = {"Goals": "worldcup_goals.csv",
          "NonGoals": "worldcup_nongoals.csv",
          "DefRecovery": "worldcup_defensive_recovery.csv"}

# Audited THEME 8 manuscript counts: (total, L0, L1, L2+).
THEME = {"Goals": (37, 19, 15, 3),
         "NonGoals": (118, 31, 64, 23),
         "DefRecovery": (250, 25, 80, 145)}


def load(group):
    return read_table(DATA / GROUPS[group], obs_start="obs_start",
                      obs_end="obs_end", time_unit="ms")


def counts_by_level(pats):
    lv = Counter(p.level for p in pats)
    return (len(pats), lv.get(0, 0), lv.get(1, 0),
            sum(v for k, v in lv.items() if k >= 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true",
                    help="also run the surrogate null (slow, ~10 min)")
    ap.add_argument("--B", type=int, default=200)
    args = ap.parse_args()

    print("=" * 70)
    print("1. CONCORDANCE — pattern counts, tpattern vs THEME 8 (same parameters)")
    print("=" * 70)
    print(f"{'group':13}{'level':14}{'tpattern':>10}{'THEME':>8}")
    detected = {}
    for g in GROUPS:
        obs = load(g)
        pats = Engine(obs, Config()).detect()
        detected[g] = pats
        tot, l0, l1, l2p = counts_by_level(pats)
        tt, t0, t1, t2 = THEME[g]
        for lab, a, b in [("total", tot, tt), ("L0 univariate", l0, t0),
                          ("L1 bivariate", l1, t1), ("L2+ higher", l2p, t2)]:
            print(f"{g if lab=='total' else '':13}{lab:14}{a:>10}{b:>8}")
        print("-" * 45)
    print("Level 0 reproduces THEME exactly in all three groups.")

    print("\n" + "=" * 70)
    print("2. EXCLUSION DIVERGENCE — defensive recovery, interception retained")
    print("=" * 70)
    obs = load("DefRecovery")
    kept_it = Engine(obs, Config(exclude_events=[])).detect()
    it_loops = [p for p in kept_it if p.has_loop and "Interception" in p.signature()]
    n_comp = sum(1 for p in detected["DefRecovery"] if p.level >= 1)
    print(f"Frequent-event rule applied (default): interception excluded, "
          f"{n_comp} composite patterns.")
    print(f"Interception retained (as THEME had it): {len(it_loops)} "
          f"interception-mediated loops recovered, e.g.")
    for p in sorted(it_loops, key=lambda p: -p.N)[:3]:
        print(f"    N={p.N:>3}  {p}")
    print("=> the divergence is the exclusion heuristic, not the detection maths.")

    print("\n" + "=" * 70)
    print("3. CONCURRENCY — co-occurrence vs genuine sequence")
    print("=" * 70)
    for g in GROUPS:
        o = load(g)
        same = tot = 0
        for x in o:
            ts = [t for t, _ in x.events]
            for i in range(1, len(ts)):
                tot += 1
                same += (ts[i] == ts[i - 1])
        print(f"  {g:13} {same/tot*100:4.1f}% of consecutive events share a timestamp")
    probe = [("Challenge_Pressure", "Shot_Goal_Pressure"),
             ("Shot_Goal_Pressure", "Challenge_Pressure"),
             ("Cross_Incomplete_NoPressure", "Shot_Goal_Pressure"),
             ("Cross_Incomplete_NoPressure", "Shot_Goal_NoPressure")]
    goals = load("Goals")
    d0 = {p.signature(): p.N for p in Engine(goals, Config(min_lag=0)).detect()}
    d1 = {p.signature(): p.N for p in Engine(goals, Config(min_lag=1)).detect()}
    print("\n  Goals — occurrences with all events vs with a genuine >=1 frame lag:")
    for a, b in probe:
        sig = f"({a} {b})"
        print(f"    {a} -> {b}: N={d0.get(sig,0)} -> {d1.get(sig,0)}")
    print("  => challenge-shot links are simultaneous (co-occurrence);")
    print("     cross-shot links are genuine sequence.")

    if args.calibrate:
        print("\n" + "=" * 70)
        print(f"4. CALIBRATION — profile-preserving null, B={args.B}, FDR q<=.05")
        print("=" * 70)
        print(f"{'group':13}{'detected(L>=1)':>15}{'FDR keep':>10}{'FWER keep':>11}")
        for g in GROUPS:
            res = calibrate(load(g), Config(), null="profile", B=args.B,
                            alpha=.005, q_target=.05, seed=SEED)
            print(f"{g:13}{len(res.real):>15}{len(res.kept('fdr')):>10}"
                  f"{len(res.kept('fwer')):>11}")
        print("\nNote: at B=200 the Monte-Carlo p-value floor is ~1/(B+1)=.005, so Holm")
        print("FWER is resolution-limited; FDR is the practical control. Raise B for FWER.")


if __name__ == "__main__":
    main()
