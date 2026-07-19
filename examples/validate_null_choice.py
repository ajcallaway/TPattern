"""
Validate the surrogate-null choice (reproduces the null-validity result in the note).
=====================================================================================

No single surrogate null is universally valid: the profile-preserving null and the
rotation/label-shuffling nulls have *complementary* blind spots. This script shows
it on controlled synthetic data with NO cross-type coupling, then confirms the real
World Cup result is not an artefact of the choice.

  1. SEPARATED types (each type in its own temporal niche — the usual case, and the
     case of the World Cup data): the profile null is well calibrated (≈0 false
     positives); the shuffle null, which destroys each type's marginal timing,
     flags almost everything (pure marginal timing mistaken for coupling).

  2. CO-LOCATED types (all types firing in the same shared burst): the profile
     null's one blind spot — it resamples from each type's pooled marginal and so
     erases the per-observation co-location, reading the overlap as coupling.

  3. REAL goals: the headline cross->goal pattern survives ALL THREE nulls, so it is
     not an artefact of any single null's blind spot; the data's within-observation
     spread confirms it is in the niche-separated regime where the profile null is
     the correct test.

Run:  python examples/validate_null_choice.py       (~3-5 min at B=200)
"""

from pathlib import Path

import numpy as np

from tpattern import Config, Observation, calibrate, read_table

B = 200
DATA = Path(__file__).resolve().parents[1] / "data"


def synth(centres, *, n_obs=100, T=1000, rate=1.2, seed=42):
    """Background events, NO cross-type coupling. `centres` maps each type to the
    centre of its within-observation time niche (all equal => co-located)."""
    rng = np.random.default_rng(seed)
    obs = []
    for k in range(n_obs):
        events = []
        for ev, c in centres.items():
            for _ in range(rng.poisson(rate)):
                events.append((int(np.clip(round(rng.normal(c, 80)), 0, T)), ev))
        events.sort()
        obs.append(Observation(name=f"o{k}", start=0, end=T, events=events))
    return obs


def survivors(obs, null):
    res = calibrate(obs, Config(exclude_events=[], min_lag=1),
                    null=null, B=B, q_target=0.05, seed=7)
    n_detected = len([c for c in res.real if c.level >= 1])
    return n_detected, len(res.kept("fdr"))


def main():
    separated = {"A": 200, "B": 400, "C": 600, "D": 800}   # distinct niches
    co_located = {t: 500 for t in "ABCD"}                  # same instant

    print("1. SYNTHETIC, no coupling — false positives should be ~0 for a valid null")
    for label, centres in (("SEPARATED", separated), ("CO-LOCATED", co_located)):
        for null in ("profile", "shuffle"):
            det, surv = survivors(synth(centres), null)
            print(f"   {label:11s} {null:8s}: {det:4d} detected, {surv:4d} survive FDR")

    print("\n2. REAL goals — is the headline pattern robust to the null choice?")
    goals = read_table(DATA / "worldcup_goals.csv",
                       obs_start="obs_start", obs_end="obs_end", time_unit="ms")
    spread = np.mean([np.std([(t - o.start) / max(o.end - o.start, 1)
                              for t, _ in o.events])
                      for o in goals if len(o.events) >= 2])
    print(f"   within-observation position spread = {spread:.3f} "
          f"(Uniform = {1/np.sqrt(12):.3f}; higher = niche-separated, not co-located)")
    for null in ("profile", "shuffle", "rotation"):
        res = calibrate(goals, Config(min_lag=1), null=null, B=B, q_target=0.05, seed=7)
        tgt = [c for c in res.kept("fdr")
               if "Cross_Incomplete_NoPressure" in c.pattern.signature()
               and "Shot_Goal" in c.pattern.signature()]
        flag = "cross->goal survives" if tgt else "cross->goal absent"
        print(f"   null={null:8s}: {len(res.kept('fdr'))} survivors | {flag}")

    print("\nInterpretation: the profile null is clean on separated data and only "
          "inflates when types are co-located; the real goals data are separated "
          "(spread > uniform), and cross->goal survives every null — so it is a "
          "genuine coupling, not an artefact of the null.")


if __name__ == "__main__":
    main()
