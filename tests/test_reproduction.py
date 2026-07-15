"""
Reproduction test — the anchor for the paper's reproducibility claim.

The detector must reproduce THEME's published occurrence counts for the World Cup
Goals sample to the exact N. These anchors were read from the audited manuscript.
Skipped automatically if the (external) THEME_Goals data folder is not present.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import read_sample, Engine, Config  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "THEME_Goals"

# (A, B, expected N) — from the audited World Cup manuscript (Goals sample).
ANCHORS = [
    ("Challenge_Pressure", "Shot_Goal_Pressure", 21),
    ("Challenge_Pressure", "Pass_Complete_Pressure", 21),
    ("Cross_Incomplete_NoPressure", "Shot_Goal_Pressure", 14),
    ("Cross_Incomplete_NoPressure", "Shot_Goal_NoPressure", 8),
    ("Shot_Goal_Pressure", "Challenge_Pressure", 16),
    ("Shot_Goal_NoPressure", "Challenge_Pressure", 7),
]

pytestmark = pytest.mark.skipif(not DATA.exists(),
                                reason="THEME_Goals data folder not present")


@pytest.fixture(scope="module")
def goals_patterns():
    obs = read_sample(DATA)
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
