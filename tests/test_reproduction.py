"""
Reproduction test — the anchor for the paper's reproducibility claim.

The detector must reproduce THEME's published occurrence counts for the World Cup
Goals sample to the exact N. These anchors were read from the audited manuscript.
The derived data ships in data/, so this runs everywhere (including CI) rather
than being skipped.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import read_table, Engine, Config  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "worldcup_goals.csv"

# (A, B, expected N) — from the audited World Cup manuscript (Goals sample).
ANCHORS = [
    ("Challenge_Pressure", "Shot_Goal_Pressure", 21),
    ("Challenge_Pressure", "Pass_Complete_Pressure", 21),
    ("Cross_Incomplete_NoPressure", "Shot_Goal_Pressure", 14),
    ("Cross_Incomplete_NoPressure", "Shot_Goal_NoPressure", 8),
    ("Shot_Goal_Pressure", "Challenge_Pressure", 16),
    ("Shot_Goal_NoPressure", "Challenge_Pressure", 7),
]


@pytest.fixture(scope="module")
def goals_patterns():
    obs = read_table(DATA, obs_start="obs_start", obs_end="obs_end", time_unit="ms")
    assert len(obs) == 163, "expected the 163 goal sequences"
    return {p.signature(): p for p in Engine(obs, Config()).detect()}


@pytest.mark.parametrize("a,b,expected", ANCHORS)
def test_level1_anchor_counts(goals_patterns, a, b, expected):
    sig = f"({a} {b})"
    assert sig in goals_patterns, f"pattern {a} -> {b} not detected"
    assert goals_patterns[sig].N == expected


def test_univariate_count_matches_theme(goals_patterns):
    # THEME reported 19 univariate (Level 0) event types for Goals.
    l0 = [p for p in goals_patterns.values() if p.level == 0]
    assert len(l0) == 19


def test_key_trivariate_present(goals_patterns):
    sig = "(Cross_Incomplete_NoPressure (Challenge_Pressure Shot_Goal_Pressure))"
    assert sig in goals_patterns
    assert goals_patterns[sig].N == 6


def test_observation_window_is_preserved():
    """The NX/T baseline depends on the observation window, so the shipped data
    must carry it explicitly rather than have it inferred from the events."""
    obs = read_table(DATA, obs_start="obs_start", obs_end="obs_end", time_unit="ms")
    assert sum(max(o.T, 1) for o in obs) == 1064634
