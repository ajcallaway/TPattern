"""Unified synthetic validation for the paper: one canonical configuration drives
the recovery power curve (Table 2 / Figure 4), the per-analysis false-positive rate
and its CI, and the two null regimes (Table 4). Dumps every number to JSON.

Run: python validate_synthetic.py   (slow: ~10-15 min)
"""
import json
import numpy as np
from tpattern import Config, calibrate, Observation
from tpattern.synthetic import SyntheticSpec, make_dataset

# ---- ONE canonical configuration ----
CFG = dict(n_seq=300, T=6000, bg_types=8, bg_rate=2.5, jitter=200, lag=1500, seed=7, B=200)
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
K = 20
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
json.dump(out, open("/tmp/valsynth.json", "w"))

# 2. False-positive rate + CI (plant=0, canonical background = the separated regime)
print("\nFALSE POSITIVE / SEPARATED NULL (plant=0)", flush=True)
tot = fp = 0
NULLS = 50
for s in range(NULLS):
    obs, _ = make_dataset(_spec(0.0, 6000 + s))
    r = calibrate(obs, Config(exclude_events=[], min_lag=1), null="profile", B=B, seed=1, **CAL)
    comp = [c for c in r.real if c.level >= 1]
    tot += len(comp); fp += len(r.kept("fdr"))
ci = 3 / tot if tot else None
print(f"  {NULLS} null datasets: {tot} composites, {fp} FDR false survivors, "
      f"95% upper bound 3/{tot} = {ci:.3%}" if tot else "  0 composites", flush=True)
out["false_positive"] = {"n_datasets": NULLS, "composites": tot, "fp_fdr": fp,
                         "ci_upper": ci}

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

json.dump(out, open("/tmp/valsynth.json", "w"))
print("\nSaved /tmp/valsynth.json", flush=True)
