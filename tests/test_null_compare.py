"""compare_nulls: profile vs rotation decomposition into core and shell."""
import os

from tpattern import (Config, compare_nulls, NullComparison, calibrate,
                      null_comparison_plot)
from tpattern.synthetic import SyntheticSpec, make_dataset


def _planted(frac=0.15, seed=7):
    # a dataset with a genuine A->B coupling planted on top of background
    obs, _ = make_dataset(SyntheticSpec(
        n_seq=300, planted=[("A", 0), ("B", 1500)], plant_fraction=frac,
        jitter=200, bg_rate=2.5, seed=seed))
    return obs


def test_compare_nulls_structure():
    obs = _planted()
    cfg = Config(min_lag=1)
    cmp = compare_nulls(obs, cfg, nulls=("profile", "rotation"), B=100, seed=1)
    assert isinstance(cmp, NullComparison)
    assert set(cmp.nulls) == {"profile", "rotation"}
    # detection is null-independent: both nulls see the same detected patterns
    assert set(cmp.detected["profile"]) == set(cmp.detected["rotation"])
    # core is exactly the intersection of the two survivor sets
    assert cmp.common == cmp.survives["profile"] & cmp.survives["rotation"]
    # unique sets are disjoint from the core and from each other
    assert cmp.unique["profile"].isdisjoint(cmp.common)
    assert cmp.unique["rotation"].isdisjoint(cmp.common)
    assert cmp.unique["profile"].isdisjoint(cmp.unique["rotation"])


def test_rows_and_layers_consistent():
    obs = _planted()
    cmp = compare_nulls(obs, Config(min_lag=1), B=100, seed=2)
    for r in cmp.rows():
        surv = [n for n in cmp.nulls if r["survives"][n]]
        assert surv, "a row must survive at least one null"
        if len(surv) == len(cmp.nulls):
            assert r["layer"] == "core"
        elif len(surv) == 1:
            assert r["layer"] == f"{surv[0]}-only"
        # every listed q is a probability
        for n in cmp.nulls:
            q = r["q"][n]
            assert q is None or 0.0 <= q <= 1.0


def test_matches_individual_calibrate():
    # compare_nulls must agree with calling calibrate() per null
    obs = _planted()
    cfg = Config(min_lag=1)
    cmp = compare_nulls(obs, cfg, nulls=("profile", "rotation"), B=100, seed=3)
    for null in ("profile", "rotation"):
        r = calibrate(obs, cfg, null=null, B=100, seed=3)
        assert cmp.survives[null] == {c.pattern.signature() for c in r.kept("fdr")}


def test_plot_writes_file(tmp_path):
    obs = _planted()
    cmp = compare_nulls(obs, Config(min_lag=1), B=100, seed=4)
    out = tmp_path / "cmp.png"
    null_comparison_plot(cmp, str(out), title="test")
    assert out.exists() and out.stat().st_size > 0
