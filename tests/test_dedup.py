"""Occurrence-identical patterns (co-timed reversals, equivalent bracketings) must
collapse to one representative when collapse_equivalent is on, so the pattern count
and the multiple-comparison family reflect distinct hypotheses (panel Essential 1)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import read_table, Config, Engine  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data"

def _occ_keys(pats):
    return [frozenset((i.obs, tuple(sorted(i.tokens))) for i in p.instances)
            for p in pats if p.level >= 1]

def test_collapse_removes_occurrence_identical_duplicates():
    obs = read_table(DATA / "worldcup_nongoals.csv", obs_start="obs_start",
                     obs_end="obs_end", time_unit="ms")
    on = [p for p in Engine(obs, Config(min_lag=0, collapse_equivalent=True)).detect()
          if p.level >= 1]
    off = [p for p in Engine(obs, Config(min_lag=0, collapse_equivalent=False)).detect()
           if p.level >= 1]
    keys_on = _occ_keys(on)
    # with collapse on, every composite has a distinct occurrence set
    assert len(keys_on) == len(set(keys_on)), "duplicates survived collapse"
    # collapse actually removed duplicates that existed without it
    assert len(on) < len(off), "expected duplicates to be present without collapse"

def test_collapse_does_not_touch_headline():
    obs = read_table(DATA / "worldcup_goals.csv", obs_start="obs_start",
                     obs_end="obs_end", time_unit="ms")
    pats = [p for p in Engine(obs, Config(min_lag=1)).detect() if p.level >= 1]
    keys = _occ_keys(pats)
    assert len(keys) == len(set(keys))  # headline path has no duplicates anyway


def test_same_time_same_type_duplicates_collapse():
    """Same-type events at an identical timestamp collapse to one point (default);
    they are retained only when the option is explicitly disabled."""
    from tpattern import Observation, Engine, Config
    obs = [Observation(name="o", start=0, end=200,
                       events=[(0, "A"), (0, "A"), (100, "A"), (0, "B")])]
    eng = Engine(obs, Config()); eng.build_terminals()
    n_A = next(p.N for p in eng.univariate if p.event == "A")
    assert n_A == 2, f"collapse: A should be 2 distinct points, got {n_A}"
    eng2 = Engine(obs, Config(collapse_duplicates=False)); eng2.build_terminals()
    n_A2 = next(p.N for p in eng2.univariate if p.event == "A")
    assert n_A2 == 3, f"no-collapse: A should retain all 3, got {n_A2}"
