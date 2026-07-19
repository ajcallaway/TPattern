"""group_contrast must recover a pattern planted more heavily in one group, with
an odds ratio > 1 and a small p-value (ground truth)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import group_contrast                    # noqa: E402
from tpattern.synthetic import SyntheticSpec, make_dataset  # noqa: E402


def _labelled_sample():
    hi, _ = make_dataset(SyntheticSpec(n_seq=120, planted=[("A", 0), ("B", 1500)],
                                       plant_fraction=0.40, seed=1))
    lo, _ = make_dataset(SyntheticSpec(n_seq=120, planted=[("A", 0), ("B", 1500)],
                                       plant_fraction=0.05, seed=2))
    for o in hi:
        o.name = "hi_" + o.name
    for o in lo:
        o.name = "lo_" + o.name
    return hi + lo


def test_group_contrast_recovers_planted_difference():
    obs = _labelled_sample()
    rows = group_contrast(obs, group_of=lambda o: "high" if o.name.startswith("hi")
                          else "low")
    planted = next(r for r in rows if r["signature"] == "(A B)")
    assert planted["odds_ratio"] > 2.0
    assert planted["p"] < 0.01
    assert planted["more_common_in"] == "high"


def test_group_contrast_requires_two_groups():
    obs = _labelled_sample()
    try:
        group_contrast(obs, group_of=lambda o: "only_one")
        assert False, "should reject a single group"
    except ValueError:
        pass
