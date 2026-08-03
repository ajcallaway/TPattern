"""Single source of truth for every World Cup number that appears across the
three papers (applied, validation, tutorial). Fixed seed + current version, so
all three can be reconciled to one run. Emits /tmp/canonical.json.

Run: python examples/canonical_numbers.py
"""
import json
import tpattern
from pathlib import Path
from tpattern import read_table, Engine, Config, calibrate

VER = getattr(tpattern, "__version__", "?")
SEED = 20260714
DATA = Path(__file__).resolve().parents[1] / "data"
GRP = {"Goals": ("worldcup_goals.csv", 2000),
       "NonGoals": ("worldcup_nongoals.csv", 200),
       "DefRecovery": ("worldcup_defensive_recovery.csv", 200)}


def load(f):
    return read_table(DATA / f, obs_start="obs_start", obs_end="obs_end", time_unit="ms")


out = {"version": VER, "seed": SEED, "groups": {}}
print(f"tpattern {VER}, seed {SEED}", flush=True)

for g, (f, B) in GRP.items():
    obs = load(f)
    # descriptive detection (min_lag=0)
    det0 = Engine(obs, Config(min_lag=0)).detect()
    tot = len(det0); l2 = sum(1 for p in det0 if p.level >= 2)
    comp0 = [p for p in det0 if p.level >= 1]
    # min_lag=0 calibration (applied [46])
    c0 = calibrate(obs, Config(), null="profile", B=B, alpha=.005, q_target=.05, seed=SEED)
    surv0 = c0.kept("fdr")
    # genuine-lag calibration (min_lag=1) (validation Table 5, tutorial, applied [50])
    c1 = calibrate(obs, Config(min_lag=1), null="profile", B=B, alpha=.005, q_target=.05, seed=SEED)
    surv1 = sorted(c1.kept("fdr"), key=lambda c: -c.N)
    rec = {
        "detected_total": tot, "higher_order_L2plus": l2,
        "composite_detected_lag0": len(comp0),
        "cal_lag0_survive": len(surv0), "cal_lag0_composite": len([c for c in c0.real if c.level >= 1]),
        "genuinelag_detected": len(c1.real), "genuinelag_survive": len(surv1),
        "genuinelag_top": [{"N": c.N, "q": round(c.fdr_q, 3), "sig": str(c.pattern)} for c in surv1[:6]],
        "B": B,
    }
    out["groups"][g] = rec
    print(f"  {g:12}: det {tot}({l2} L2+) | lag0 {rec['cal_lag0_survive']}/{rec['cal_lag0_composite']}"
          f" | genuine-lag {rec['genuinelag_survive']}/{rec['genuinelag_detected']}", flush=True)

# Goals null-choice: rotation vs profile at B=2000, genuine lag (validation [62], tutorial)
goals = load(GRP["Goals"][0])
nc = {}
for nm in ("profile", "rotation", "shuffle"):
    r = calibrate(goals, Config(min_lag=1), null=nm, B=2000, alpha=.005, q_target=.05, seed=SEED)
    nc[nm] = len(r.kept("fdr"))
out["goals_nullchoice_genuinelag_B2000"] = nc
print("  goals null-choice (genuine lag, B=2000):", nc, flush=True)

json.dump(out, open("/tmp/canonical.json", "w"), indent=2)
print("\nSaved /tmp/canonical.json", flush=True)
