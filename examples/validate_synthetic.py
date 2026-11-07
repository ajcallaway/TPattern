"""Unified synthetic validation for the paper: one canonical configuration drives
the recovery power curve (Table 2 / Figure 4), the per-analysis false-positive rate
and its CI, and the two null regimes (Table 4). Dumps every number to JSON.

Run: python validate_synthetic.py   (slow: ~10-15 min)
"""
import argparse
import json
from pathlib import Path

import numpy as np
from tpattern import Config, calibrate, Observation
from tpattern.synthetic import SyntheticSpec, make_dataset

_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument("--B", type=int, default=200,
                 help="surrogates per calibration (paper's synthetic tables used 200; "
                      "pass 2000 to match the confirmatory real-data resolution)")
_ap.add_argument("--K", type=int, default=20, help="simulations per power-curve point")
_ap.add_argument("--nulls", type=int, default=100, help="independent null datasets")
_ap.add_argument("--out", default=None, help="output JSON (default results/valsynth_B<B>.json)")
_args = _ap.parse_args()

# ---- ONE canonical configuration ----
CFG = dict(n_seq=300, T=6000, bg_types=8, bg_rate=2.5, jitter=200, lag=1500, seed=7,
           B=_args.B)
N, T, TYPES, RATE, JIT, LAG, SEED, B = (CFG["n_seq"], CFG["T"], CFG["bg_types"],
                                        CFG["bg_rate"], CFG["jitter"], CFG["lag"],
                                        CFG["seed"], CFG["B"])
CAL = dict(q_target=0.05)
out = {"config": CFG}


def _spec(frac, seed):
    return SyntheticSpec(n_seq=N, T=T, bg_types=TYPES, bg_rate=RATE,
                         planted=[("A", 0), ("B", LAG)], plant_fraction=frac,
                         jitter=JIT, seed=seed)


def _recover(frac, seed):
    obs, truth = make_dataset(_spec(frac, seed))
    r = calibrate(obs, Config(min_lag=1), null="profile", B=B, seed=1, **CAL)
    got = {c.pattern.signature(): c for c in r.real}.get(truth)
    n = got.N if got else 0
    return n, bool(got and got in r.kept("fdr")), bool(got and got in r.kept("fwer"))


# 1. Power curve (Figure 4) + Table 2 rows
fracs = [0.03, 0.05, 0.06, 0.07, 0.10, 0.13, 0.15, 0.17, 0.20]
K = _args.K
curve = []
print("POWER CURVE (canonical bg_rate=2.5, n=300, T=6000)", flush=True)
print("frac  meanN  P(FDR) P(FWER)", flush=True)
for f in fracs:
    Ns, fdr, fwer = [], 0, 0
    for k in range(K):
        n, rf, rw = _recover(f, SEED + 1000 + k)
        Ns.append(n); fdr += rf; fwer += rw
    mN = sum(Ns) / K
    print(f"{f:.2f}  {mN:5.1f}  {fdr/K:.2f}   {fwer/K:.2f}", flush=True)
    curve.append({"frac": f, "meanN": round(mN, 1), "p_fdr": fdr/K, "p_fwer": fwer/K})
out["powercurve"] = curve
out["table2"] = [c for c in curve if c["frac"] in (0.06, 0.10, 0.15, 0.20)]
OUT = Path(_args.out) if _args.out else (
    Path(__file__).resolve().parents[1] / "results" / f"valsynth_B{B}.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(OUT, "w"), indent=2)   # checkpoint: power curve done

# 2. False-positive rate + CI (plant=0, canonical background = the separated regime)
print("\nFALSE POSITIVE / SEPARATED NULL (plant=0)", flush=True)
tot = fp = dws = 0   # composites, total false survivors, datasets-with-a-survivor
NULLS = _args.nulls
for s in range(NULLS):
    obs, _ = make_dataset(_spec(0.0, 6000 + s))
    r = calibrate(obs, Config(exclude_events=[], min_lag=1), null="profile", B=B, seed=1, **CAL)
    comp = [c for c in r.real if c.level >= 1]
    surv = r.kept("fdr")
    tot += len(comp); fp += len(surv); dws += (1 if surv else 0)
# PER-ANALYSIS false-positive rate: fraction of INDEPENDENT null datasets with >=1 survivor.
# Rule of three needs independent trials, so the denominator is NULLS (datasets), not patterns.
ci = 3 / NULLS if dws == 0 else None
print(f"  {NULLS} independent null datasets: {dws} had a false FDR survivor "
      f"({tot} composites detected in total, {fp} survivors). "
      f"Per-analysis 95%% upper bound = 3/{NULLS} = {3/NULLS:.1%}" if dws == 0 else
      f"  {dws}/{NULLS} datasets had a false survivor", flush=True)
out["false_positive"] = {"n_datasets": NULLS, "datasets_with_survivor": dws,
                         "composites": tot, "fp_fdr": fp, "per_analysis_ci_upper": ci}

# representative separated dataset (Table 4 row)
obs0, _ = make_dataset(_spec(0.0, SEED))
rp = calibrate(obs0, Config(exclude_events=[], min_lag=1), null="profile", B=B, seed=7, **CAL)
rr = calibrate(obs0, Config(exclude_events=[], min_lag=1), null="rotation", B=B, seed=7, **CAL)
sep_det = len([c for c in rp.real if c.level >= 1])
out["null_separated"] = {"detected": sep_det, "profile": len(rp.kept("fdr")),
                         "rotation": len(rr.kept("fdr"))}
print(f"  Table-4 separated: detected={sep_det}, profile={len(rp.kept('fdr'))}, "
      f"rotation={len(rr.kept('fdr'))}", flush=True)

# 3. Co-located null (Table 4 other row): all types in one shared burst, matched params
print("\nCO-LOCATED NULL (shared burst, matched params)", flush=True)
rng = np.random.default_rng(SEED)
centre, sigma = T // 2, int(T * 0.05)
obs_c = []
for k in range(N):
    ev = []
    for i in range(TYPES):
        for _ in range(rng.poisson(RATE)):
            ev.append((int(np.clip(round(rng.normal(centre, sigma)), 0, T)), f"bg{i}"))
    ev.sort(); obs_c.append(Observation(name=f"c{k}", start=0, end=T, events=ev))
rcp = calibrate(obs_c, Config(exclude_events=[], min_lag=1), null="profile", B=B, seed=7, **CAL)
rcr = calibrate(obs_c, Config(exclude_events=[], min_lag=1), null="rotation", B=B, seed=7, **CAL)
col_det = len([c for c in rcp.real if c.level >= 1])
out["null_colocated"] = {"detected": col_det, "profile": len(rcp.kept("fdr")),
                         "rotation": len(rcr.kept("fdr"))}
print(f"  Table-4 co-located: detected={col_det}, profile={len(rcp.kept('fdr'))}, "
      f"rotation={len(rcr.kept('fdr'))}", flush=True)

json.dump(out, open(OUT, "w"), indent=2)
print(f"\nSaved {OUT}", flush=True)
