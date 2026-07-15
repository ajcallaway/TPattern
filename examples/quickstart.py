"""
Quickstart — detect, calibrate, and report T-patterns on synthetic data.

Runs with no external data. It plants a known pattern A -> B -> C into a noisy
background, then shows the full pipeline recovering it and writing a report.
For a real-data example see reproduce_worldcup.py (requires the World Cup files).
"""

from tpattern import Engine, Config, calibrate, report
from tpattern.synthetic import SyntheticSpec, make_dataset


def main():
    # 1. build a dataset with a known planted pattern A -> B -> C
    spec = SyntheticSpec(n_seq=300, planted=[("A", 0), ("B", 1200), ("C", 1200)],
                         plant_fraction=0.2, seed=7)
    observations, truth = make_dataset(spec)

    # 2. detect
    patterns = Engine(observations, Config()).detect()
    composite = [p for p in patterns if p.level >= 1]
    print(f"detected {len(composite)} composite patterns; planted truth = {truth}")

    # 3. calibrate against a profile-preserving surrogate null (FDR-corrected)
    result = calibrate(observations, Config(), null="profile", B=100, q_target=0.05)
    kept = result.kept("fdr")
    print(f"{len(kept)} pattern(s) survive FDR correction:")
    for c in sorted(kept, key=lambda c: c.p_emp)[:10]:
        print(f"    N={c.N:>3}  q={c.fdr_q:.3f}  {c.pattern}")

    # 4. write a report (table + dendrograms + summary)
    written = report(result, "quickstart_out", title="Quickstart synthetic example")
    print("\nreport written:")
    for k, v in written.items():
        print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
