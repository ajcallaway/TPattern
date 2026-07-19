"""Regression guards for the calibrated pipeline (panel Review-Extras §C):
the headline q-value the validation paper turns on, detection determinism, and
the occurrence-equivalence invariant. Nothing else pins these."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import read_table, Config, Engine, calibrate       # noqa: E402
from tpattern.synthetic import SyntheticSpec, make_dataset        # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"

def test_headline_calibrated_number_is_pinned():
    obs = read_table(DATA / "worldcup_goals.csv", obs_start="obs_start",
                     obs_end="obs_end", time_unit="ms")
    r = calibrate(obs, Config(min_lag=1), null="profile", B=2000, seed=20260714)
    kept = r.kept("fdr")
    assert len(kept) == 1
    c = kept[0]
    assert c.pattern.signature() == "(Cross_Incomplete_NoPressure Shot_Goal_Pressure)"
    assert c.N == 14
    assert abs(c.fdr_q - 0.006) < 1e-3          # MC p is deterministic at fixed seed

def test_detection_is_deterministic():
    obs, _ = make_dataset(SyntheticSpec(seed=7))
    a = {p.signature(): p.N for p in Engine(obs, Config()).detect()}
    b = {p.signature(): p.N for p in Engine(obs, Config()).detect()}
    assert a == b

def test_no_occurrence_duplicates_after_collapse():
    obs = read_table(DATA / "worldcup_nongoals.csv", obs_start="obs_start",
                     obs_end="obs_end", time_unit="ms")
    pats = [p for p in Engine(obs, Config()).detect() if p.level >= 1]
    keys = [frozenset((i.obs, tuple(sorted(i.tokens))) for i in p.instances) for p in pats]
    assert len(keys) == len(set(keys))          # one representative per occurrence set
