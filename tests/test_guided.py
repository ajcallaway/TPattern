"""The guided wizard's engine (run_analysis) must complete end-to-end and write
the expected outputs. The widget layer (launch) is UI-only and not tested here."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tpattern import run_analysis  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "worldcup_goals.csv"

pytestmark = pytest.mark.skipif(not DATA.exists(), reason="shipped data not present")


def test_run_analysis_end_to_end(tmp_path):
    res = run_analysis(str(DATA), obs_start="obs_start", obs_end="obs_end",
                       time_unit="ms", null="profile", min_lag=1, B=50,
                       outdir=str(tmp_path / "out"), title="test")
    # it read the 163 goal sequences and captured a recommendation
    assert "163 observations" in res.recommendation
    assert res.n_detected > 0
    # it produced a table, a summary and a Methods statement
    assert Path(res.files["table"]).exists()
    assert Path(res.files["summary"]).exists()
    assert "T-pattern detection was performed with tpattern" in res.methods
    assert "min_lag = 1" in res.methods  # the chosen setting is documented
