"""Power curve at 100 simulations per point, with success counts so binomial
(Wilson) CIs can be reported. Same canonical config as validate_synthetic.py.
Dumps /tmp/powercurve_ci.json. Slow (~70 min)."""
import json
from tpattern import Config, calibrate
from tpattern.synthetic import SyntheticSpec, make_dataset

N, T, TYPES, RATE, JIT, LAG, B = 300, 6000, 8, 2.5, 200, 1500, 200
FRACS = [0.03, 0.05, 0.06, 0.07, 0.10, 0.13, 0.15, 0.17, 0.20]
K = 100


def recover(frac, seed):
    obs, truth = make_dataset(SyntheticSpec(
        n_seq=N, T=T, bg_types=TYPES, bg_rate=RATE, planted=[("A", 0), ("B", LAG)],
        plant_fraction=frac, jitter=JIT, seed=seed))
    r = calibrate(obs, Config(min_lag=1), null="profile", B=B, q_target=.05, seed=1)
    got = {c.pattern.signature(): c for c in r.real}.get(truth)
    n = got.N if got else 0
    return n, bool(got and got in r.kept("fdr")), bool(got and got in r.kept("fwer"))


curve = []
print("frac  meanN  FDR(k/100)  FWER(k/100)", flush=True)
for f in FRACS:
    Ns, fdr, fwer = [], 0, 0
    for k in range(K):
        n, rf, rw = recover(f, 7 + 1000 + k)
        Ns.append(n); fdr += rf; fwer += rw
    mN = round(sum(Ns) / K, 1)
    curve.append({"frac": f, "meanN": mN, "K": K, "fdr_k": fdr, "fwer_k": fwer,
                  "p_fdr": fdr / K, "p_fwer": fwer / K})
    print(f"{f:.2f}  {mN:5.1f}   {fdr}/100     {fwer}/100", flush=True)
    json.dump(curve, open("/tmp/powercurve_ci.json", "w"))
print("saved /tmp/powercurve_ci.json", flush=True)
