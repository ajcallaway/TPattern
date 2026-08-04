"""The reference registry: coverage, explain(), and the renamed output columns."""
from tpattern import (SETTINGS, COLUMNS, explain, explain_settings, explain_columns,
                      parameters_markdown, read_table, Config, calibrate,
                      patterns_table, Observation)


def test_every_setting_is_complete():
    for s in SETTINGS:
        for field in ("key", "form", "group", "does", "range", "recommend", "effect"):
            assert s.get(field), f"{s.get('form')} missing {field}"
        assert s["group"] in ("A", "B", "C")


def test_explain_by_key_and_form_name():
    a = explain("min_lag")
    b = explain("minimum_lag_frames")
    assert a == b and "recommended" in a and "range" in a


def test_explain_column_and_unknown():
    assert "Benjamini" in explain("fdr_q")
    assert "No setting or column" in explain("does_not_exist")


def test_parameters_markdown_covers_all():
    md = parameters_markdown()
    for s in SETTINGS:
        assert s["form"] in md
    for c in COLUMNS:
        assert c["key"] in md


def _sample():
    obs = []
    for i in range(6):
        ev = [(0, "A"), (300, "B")] + ([(600, "C")] if i < 3 else [])
        obs.append(Observation(name=f"o{i}", start=0, end=1000, events=ev))
    return obs


def test_output_columns_renamed():
    res = calibrate(_sample(), Config(min_lag=1), null="profile", B=50, q_target=.05, seed=1)
    row = patterns_table(res)[0]
    assert "monte_carlo_p" in row and "survives_fwer_holm" in row
    assert "p_emp" not in row and "fwer_keep" not in row
    # every reported column has a registry entry (the tutorial table generates from it)
    keys = {c["key"] for c in COLUMNS}
    for col in ("monte_carlo_p", "fdr_q", "survives_fwer_holm", "N", "level", "bout_support"):
        assert col in keys


def test_sort_tolerates_old_name():
    res = calibrate(_sample(), Config(min_lag=1), null="profile", B=50, q_target=.05, seed=1)
    patterns_table(res, sort="p_emp")   # must not raise
