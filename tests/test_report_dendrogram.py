"""Regression: report()/patterns_overview must handle a single composite pattern.

With cols=2, plt.subplots returns a 2-axis ndarray even for one pattern; the old
code wrapped that array in a list and passed it to pattern_dendrogram, which then
called ndarray.plot(). The de-duplication work collapsed the quickstart to exactly
one composite, exposing the crash in report().
"""
import matplotlib
matplotlib.use("Agg")

from tpattern import Config, Engine, calibrate, report
from tpattern.viz import patterns_overview
from tpattern.synthetic import SyntheticSpec, make_dataset


def _planted():
    obs, _ = make_dataset(SyntheticSpec(
        n_seq=300, planted=[("A", 0), ("B", 1500)], plant_fraction=0.15,
        jitter=200, bg_rate=2.5, seed=7))
    return obs


def test_patterns_overview_single_composite(tmp_path):
    obs = _planted()
    comps = [p for p in Engine(obs, Config(min_lag=1)).detect() if p.level >= 1]
    assert comps, "planted data should yield at least one composite"
    out = tmp_path / "ov.png"
    patterns_overview(comps[:1], str(out))   # the n == 1 path
    assert out.exists() and out.stat().st_size > 0


def test_report_writes_dendrogram(tmp_path):
    obs = _planted()
    r = calibrate(obs, Config(min_lag=1), null="profile", B=50, seed=1)
    import os
    w = report(r, str(tmp_path / "out"), title="t")
    assert os.path.exists(w["dendrograms"]) and os.path.getsize(w["dendrograms"]) > 0


def test_forest_plot_degenerate_ci(tmp_path):
    """An odds-ratio CI can hit 0 or inf (a group with a zero cell); forest_plot
    must not set a non-positive/inf limit on its log x-axis."""
    import warnings
    from tpattern import forest_plot
    items = [{"label": "a", "or": 2.0, "lo": 0.0, "hi": float("inf")},
             {"label": "b", "or": 1.5, "lo": 0.8, "hi": 3.0}]
    out = tmp_path / "forest.png"
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        forest_plot(items, str(out))
    assert out.exists() and out.stat().st_size > 0
