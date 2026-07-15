"""
Ground-truth validation — self-contained, no external data.

Two properties THEME never demonstrated:
  1. Recovery — a pattern planted into noise is detected with the right structure.
  2. Type-I control — on data with NO planted coupling, the surrogate calibration
     keeps (essentially) nothing, i.e. the false-positive rate is controlled.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import Engine, Config, calibrate  # noqa: E402
from tpattern.synthetic import SyntheticSpec, make_dataset  # noqa: E402


def test_planted_pattern_is_recovered():
    spec = SyntheticSpec(n_seq=300, planted=[("A", 0), ("B", 1500)],
                         plant_fraction=0.2, seed=7)
    obs, truth = make_dataset(spec)
    sigs = {p.signature() for p in Engine(obs, Config()).detect()}
    assert truth in sigs, f"planted pattern {truth} not recovered"


def test_three_event_pattern_is_recovered():
    spec = SyntheticSpec(n_seq=350, planted=[("A", 0), ("B", 1200), ("C", 1200)],
                         plant_fraction=0.2, seed=11)
    obs, truth = make_dataset(spec)
    sigs = {p.signature() for p in Engine(obs, Config()).detect()}
    assert truth in sigs, f"planted 3-event pattern {truth} not recovered"


def test_null_data_yields_few_survivors():
    """No planted coupling: after FDR calibration, survivors should be ~none."""
    spec = SyntheticSpec(n_seq=250, plant_fraction=0.0, bg_rate=2.5, seed=3)
    obs, _ = make_dataset(spec)
    res = calibrate(obs, Config(), null="profile", B=100, q_target=0.05)
    kept = res.kept("fdr")
    # allow a rare stochastic false positive, but the pile must be controlled
    assert len(kept) <= 1, f"expected ~0 survivors on null data, got {len(kept)}"
