"""Check the applied/shared genuine-lag numbers on the CURRENT code version,
and characterise the non-goals 18-vs-19 boundary across seeds.
Run: python examples/check_applied_current.py"""
import tpattern
from pathlib import Path
from tpattern import read_table, Config, calibrate

print("tpattern version:", getattr(tpattern, "__version__", "?"), flush=True)
DATA = Path(__file__).resolve().parents[1] / "data"
G = {"Goals": "worldcup_goals.csv", "NonGoals": "worldcup_nongoals.csv",
     "DefRecovery": "worldcup_defensive_recovery.csv"}


def load(g):
    return read_table(DATA / G[g], obs_start="obs_start", obs_end="obs_end", time_unit="ms")


SEED = 20260714
print("\n=== genuine-lag calibration (min_lag=1, profile null), canonical seed ===", flush=True)
for g, Bg in [("Goals", 2000), ("NonGoals", 200), ("DefRecovery", 200)]:
    r = calibrate(load(g), Config(min_lag=1), null="profile", B=Bg,
                  alpha=.005, q_target=.05, seed=SEED)
    surv = sorted(r.kept("fdr"), key=lambda c: -c.N)
    print(f"  {g:13} (B={Bg}): {len(r.real)} detected, {len(surv)} survive FDR", flush=True)

print("\n=== NonGoals survivor count across seeds (B=200) ===", flush=True)
ng = load("NonGoals")
for s in (1, 2, 7, 42, 2026, 20260714):
    r = calibrate(ng, Config(min_lag=1), null="profile", B=200, alpha=.005, q_target=.05, seed=s)
    surv = sorted(r.kept("fdr"), key=lambda c: -c.N)
    boundary = [f"{c.N}:{c.fdr_q:.3f}" for c in surv if c.fdr_q > 0.04]
    print(f"  seed={s:>9}: {len(surv)} survive FDR | near-threshold(q>.04): {boundary}", flush=True)
print("\nDONE", flush=True)
