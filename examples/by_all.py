"""
by_all.py — Benjamini-Yekutieli survivor counts for all three World Cup groups.
==============================================================================

Fills the outstanding BY cells of Table 5 in the validation paper. The earlier
run of this analysis wrote to /tmp and was lost when the session ended, so this
version persists each group to disk **as it finishes** (results/by_all.json),
and can be re-run to top up only the groups that are missing.

Settings are the paper's confirmatory regime, identical to the verified goals
run (which must reproduce BH=1, BY=1 for Cross -> Shot_Goal_Pressure):

    genuine lag (min_lag=1), profile-preserving null, B=2000,
    alpha=.005, q_target=.05, seed=20260714

Run (slow — NonGoals is 1,299 sequences at B=2000; expect hours):
    python examples/by_all.py                  # all three groups, resumable
    python examples/by_all.py --only NonGoals  # one group
    python examples/by_all.py --B 200          # fast smoke test (NOT paper values)
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tpattern import read_table, Config, calibrate

SEED = 20260714
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "results" / "by_all.json"
GROUPS = {"Goals": "worldcup_goals.csv",
          "NonGoals": "worldcup_nongoals.csv",
          "DefRecovery": "worldcup_defensive_recovery.csv"}


def load(group):
    return read_table(DATA / GROUPS[group], obs_start="obs_start",
                      obs_end="obs_end", time_unit="ms")


def run_group(group, B):
    """Calibrate one group and return the Table 5 row: detected count, the BH /
    BY / Holm survivor counts, and every FDR survivor with both q-values."""
    res = calibrate(load(group), Config(min_lag=1), null="profile", B=B,
                    alpha=.005, q_target=.05, seed=SEED)
    surv = sorted(res.kept("fdr"), key=lambda c: -c.N)
    return {
        "B": B,
        "detected": len(res.real),
        "n_bh": len(res.kept("fdr")),
        "n_by": len(res.kept("fdr_by")),
        "n_holm": len(res.kept("fwer")),
        "survivors": [{"pattern": c.pattern.signature(), "N": c.N,
                       "level": c.pattern.level, "p_emp": c.p_emp,
                       "q_bh": c.fdr_q, "q_by": c.fdr_q_by,
                       "holm": c.fwer_keep} for c in surv],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--only", choices=list(GROUPS))
    ap.add_argument("--force", action="store_true",
                    help="re-run groups already present in the output file")
    args = ap.parse_args()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    done = json.loads(OUT.read_text()) if OUT.exists() else {}

    todo = [args.only] if args.only else list(GROUPS)
    for g in todo:
        key = f"{g}_B{args.B}"
        if key in done and not args.force:
            print(f"{g}: already done (B={args.B}) — skipping", flush=True)
            continue
        print(f"{g}: calibrating, B={args.B} ...", flush=True)
        done[key] = run_group(g, args.B)
        # persist immediately, so a killed session never loses a finished group
        OUT.write_text(json.dumps(done, indent=2))
        r = done[key]
        print(f"{g}: detected={r['detected']}  BH={r['n_bh']}  "
              f"BY={r['n_by']}  Holm={r['n_holm']}", flush=True)
        for s in r["survivors"]:
            print(f"    N={s['N']:>3}  q_BH={s['q_bh']:.3f}  q_BY={s['q_by']:.3f}  "
                  f"{'Holm' if s['holm'] else '    '}  {s['pattern']}", flush=True)

    print(f"\nTABLE 5 — BH / BY / Holm survivors (B={args.B}, profile null, genuine lag)")
    print(f"{'group':13}{'detected':>10}{'BH':>5}{'BY':>5}{'Holm':>6}")
    for g in GROUPS:
        r = done.get(f"{g}_B{args.B}")
        if r:
            print(f"{g:13}{r['detected']:>10}{r['n_bh']:>5}{r['n_by']:>5}{r['n_holm']:>6}")
    print(f"\nWritten: {OUT}")


if __name__ == "__main__":
    main()
