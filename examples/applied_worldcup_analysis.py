"""
Reproducible analysis for the applied World Cup temporal-structure paper.
=========================================================================

Runs the complete tpattern analysis behind the paper from the three shipped
event tables, and prints every number that appears in the Tables and text, so
the paper reproduces from open code end to end. No THEME, no manual steps.

    pip install tpattern
    python applied__worldcup_analysis.py

Input: the three World Cup shot-ending event tables (one row per event:
observation, event, start; with obs_start/obs_end windows), in DATA below.

Settings (identical across the three groups; this is the whole configuration):
    significance alpha         0.005     accept a critical-interval window
    minimum occurrence         3         floor for calibration
    frequent-event exclusion   1.50      mean occurrences/observation (uniform)
    collapse duplicates        on        same-(type,time) records are one point
    collapse equivalent        on        occurrence-identical patterns -> one
    minimum lag (descriptive)  0         raw detection, co-occurrence permitted
    minimum lag (calibrated)   1         genuine lag; co-timed = co-occurrence
    surrogate null             profile-preserving
    surrogates B               200 (2000 for the goals confirmatory pattern)
    error control              Benjamini-Hochberg FDR, q <= .05
    random seed                20260714
"""
import os
from tpattern import read_table, Config, Engine, calibrate

DATA = os.path.expanduser("~/Documents/Research/tpattern/data")
GROUPS = {"Goals": "worldcup_goals.csv",
          "Non-goals": "worldcup_nongoals.csv",
          "Def-recovery": "worldcup_defensive_recovery.csv"}
SEED = 20260714


def load(name):
    return read_table(os.path.join(DATA, name),
                      obs_start="obs_start", obs_end="obs_end", time_unit="ms")


def hr(t):
    print("\n" + "=" * 72 + f"\n{t}\n" + "=" * 72)


def table1_and_2():
    """Descriptive detection (min_lag=0): counts by level (Table 1) and the
    dominant patterns (Table 2). Uniform frequent-event exclusion."""
    hr("TABLE 1 — pattern counts by level  (descriptive, min_lag=0)")
    print(f"{'group':13}{'n_seq':>7}{'L0':>6}{'L1':>6}{'L2+':>6}{'total':>7}{'excluded':>16}")
    detected = {}
    for g, f in GROUPS.items():
        obs = load(f)
        eng = Engine(obs, Config(min_lag=0))
        pats = eng.detect()
        detected[g] = (obs, pats)
        by = {}
        for p in pats:
            by[p.level] = by.get(p.level, 0) + 1
        l2 = sum(v for k, v in by.items() if k >= 2)
        print(f"{g:13}{len(obs):>7}{by.get(0,0):>6}{by.get(1,0):>6}{l2:>6}"
              f"{sum(by.values()):>7}{','.join(eng.excluded):>16}")

    hr("TABLE 2 — dominant composite patterns per group (min_lag=0)")
    for g, (obs, pats) in detected.items():
        comp = sorted((p for p in pats if p.level >= 1), key=lambda p: -p.N)[:6]
        print(f"\n  {g}:")
        for p in comp:
            print(f"    L{p.level}  N={p.N:4d}  {p.signature()}")
    return detected


def concurrency(detected):
    """Same-timestamp co-occurrence vs genuine sequence (Goals): the challenge-shot
    pairs collapse under a one-frame lag, the cross-shot pair does not."""
    hr("CO-OCCURRENCE vs SEQUENCE  (Goals, min_lag 0 -> 1)")
    goals = detected["Goals"][0]
    d1 = {p.signature(): p.N for p in Engine(goals, Config(min_lag=1)).detect() if p.level == 1}
    d0 = {p.signature(): p.N for p in detected["Goals"][1] if p.level == 1}

    def show(a, b):
        for sig, n in d0.items():
            toks = sig.strip("()").split()
            if len(toks) == 2 and toks[0] == a and toks[1] == b:
                print(f"    {a} -> {b}:  min_lag0={n}  min_lag1={d1.get(sig,0)}")
    show("Challenge_Pressure", "Shot_Goal_Pressure")
    show("Shot_Goal_Pressure", "Challenge_Pressure")
    show("Cross_Incomplete_NoPressure", "Shot_Goal_Pressure")
    # fraction of consecutive events sharing a timestamp
    for g, f in GROUPS.items():
        obs = load(f)
        same = tot = 0
        for o in obs:
            ts = sorted(t for t, _ in o.events)
            for i in range(len(ts) - 1):
                tot += 1
                same += (ts[i + 1] == ts[i])
        print(f"    {g:13} co-timed consecutive pairs: {same/tot*100:.1f}%")


def calibration():
    """Surrogate calibration (profile null, FDR): survivors per group, and the
    genuine-lag goals confirmatory pattern at B=2000."""
    hr("CALIBRATION — survivors  (profile null, B=200, FDR q<=.05, min_lag=0)")
    print(f"{'group':13}{'detected':>10}{'FDR keep':>10}{'FWER keep':>11}")
    for g, f in GROUPS.items():
        r = calibrate(load(f), Config(), null="profile", B=200,
                      alpha=.005, q_target=.05, seed=SEED)
        print(f"{g:13}{len(r.real):>10}{len(r.kept('fdr')):>10}{len(r.kept('fwer')):>11}")

    hr("GOALS confirmatory pattern (genuine lag, profile null, B=2000)")
    r = calibrate(load(GROUPS["Goals"]), Config(min_lag=1), null="profile",
                  B=2000, q_target=.05, seed=SEED)
    for c in sorted(r.kept("fdr"), key=lambda c: c.fdr_q):
        print(f"    {c.pattern.signature()}  N={c.N}  p={c.p_emp:.4f}  q={c.fdr_q:.3f}")


if __name__ == "__main__":
    det = table1_and_2()
    concurrency(det)
    calibration()      # slowest: the three-group + goals B=2000 calibration
    print("\nDone. Every number above appears in the paper's Tables and text.")
