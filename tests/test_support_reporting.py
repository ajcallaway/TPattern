"""Bout support is *reported*, not filtered on.

The support threshold (`min_samples_frac`) is a prevalence filter, not a
significance test, so the library's job is to make prevalence visible rather than
to cut on it. These tests pin that contract: every results row carries the number
of distinct bouts and the support fraction, and the profile plot renders from a
calibration result.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tpattern import (Config, Engine, calibrate, patterns_table,  # noqa: E402
                      support_profile)
from tpattern.synthetic import SyntheticSpec, make_dataset  # noqa: E402


def _sample():
    spec = SyntheticSpec(n_seq=120, planted=[("A", 0), ("B", 1500)],
                         plant_fraction=0.35, seed=5)
    obs, truth = make_dataset(spec)
    return obs, truth


def test_table_reports_bouts_and_support():
    obs, _ = _sample()
    result = calibrate(obs, Config(min_lag=1), null="profile", B=30, seed=1)
    rows = patterns_table(result)
    assert rows, "expected at least one detected pattern"
    for row in rows:
        # bouts counts DISTINCT observations; N counts occurrences and may exceed it
        assert 1 <= row["bouts"] <= len(obs)
        assert row["bouts"] <= row["N"]
        assert 0.0 < row["bout_support"] <= 1.0
        assert abs(row["bout_support"] - row["bouts"] / len(obs)) < 1e-6


def test_support_needs_sample_size_when_uncalibrated():
    """A plain pattern list has no sample size, so support is None unless given."""
    obs, _ = _sample()
    pats = [p for p in Engine(obs, Config(min_lag=1)).detect() if p.level >= 1]
    assert patterns_table(pats)[0]["bout_support"] is None
    rows = patterns_table(pats, n_observations=len(obs))
    assert rows[0]["bout_support"] is not None


def test_calibration_result_carries_sample_size():
    obs, _ = _sample()
    result = calibrate(obs, Config(min_lag=1), null="profile", B=30, seed=1)
    assert result.n_observations == len(obs)


def test_support_profile_renders(tmp_path):
    obs, _ = _sample()
    result = calibrate(obs, Config(min_lag=1), null="profile", B=30, seed=1)
    out = tmp_path / "profile.png"
    key = support_profile(result, str(out), mark_thresholds=(0.10,))
    assert out.exists() and out.stat().st_size > 0
    # returned key is ordered by descending support, so a caption can be built from it
    assert key == sorted(key, key=lambda kv: -kv[1])


def test_support_profile_handles_no_survivors(tmp_path):
    """Pure-null data: nothing survives, and the plot must still render."""
    obs, _ = make_dataset(SyntheticSpec(n_seq=80, plant_fraction=0.0, seed=9))
    result = calibrate(obs, Config(min_lag=1), null="profile", B=30, seed=2)
    out = tmp_path / "empty.png"
    key = support_profile(result, str(out))
    assert out.exists()
    assert key == [] or all(s > 0 for _, s in key)


def test_recommend_reports_duplicates_note():
    """recommend() surfaces same-instant duplicates as a note, not a recommendation."""
    from tpattern import Observation, recommend
    obs = [Observation(name=f"o{i}", start=0, end=100,
                       events=[(0, "A"), (0, "A"), (50, "B")]) for i in range(20)]
    rec = recommend(obs)
    assert any("duplicate" in n.lower() for n in rec.notes), rec.notes
    # clean data: no duplicate note
    clean = [Observation(name=f"c{i}", start=0, end=100,
                         events=[(0, "A"), (50, "B")]) for i in range(20)]
    assert not any("duplicate" in n.lower() for n in recommend(clean).notes)
