"""Tests for the 0.1.11 output layer: per-pattern timing, and the THEME-style
tables (durations, event-type roles, connections, data summary, interval counts)."""
import os
from tpattern import (Observation, Engine, Config, calibrate, patterns_table,
                      duration_stats, pattern_durations, event_type_roles,
                      connections, data_summary, interval_counts, report,
                      occurrence_plot, duration_plot)


def sample():
    # A -> B at a fixed 300 ms lag in every observation; half also carry a later C, so
    # (A B) survives standalone (not fully absorbed) alongside the longer ((A B) C).
    obs = []
    for i in range(8):
        ev = [(0, "A"), (300, "B")]
        if i < 4:
            ev.append((600, "C"))
        obs.append(Observation(name=f"o{i}", start=0, end=1000, events=ev))
    return obs


def patterns():
    return Engine(sample(), Config(min_lag=1)).detect()


def test_duration_stats_from_instances():
    p = next(p for p in patterns() if p.signature() == "(A B)")
    d = duration_stats(p)
    assert d["n"] == 8 and d["median"] == 300 and d["min"] == 300 and d["max"] == 300


def test_patterns_table_has_timing_columns():
    rows = patterns_table(patterns(), n_observations=8)
    ab = next(r for r in rows if r["signature"] == "(A B)")
    assert ab["duration_median_ms"] == 300
    assert ab["critical_interval"].endswith("ms")          # unit is labelled
    assert ab["duration_range_ms"] == "[300,300]"


def test_pattern_durations_one_row_per_occurrence():
    rows = pattern_durations(patterns())
    ab = [r for r in rows if r["signature"] == "(A B)"]
    assert len(ab) == 8
    assert all(r["duration_ms"] == r["end_ms"] - r["start_ms"] for r in rows)


def test_event_type_roles_first_and_last():
    roles = {r["event_type"]: r for r in event_type_roles(patterns())}
    # A only ever starts a pattern; C only ever ends one
    assert roles["A"]["pct_first"] == 1.0 and roles["A"]["as_last"] == 0
    assert roles["C"]["pct_last"] == 1.0 and roles["C"]["as_first"] == 0


def test_connections_direction():
    conn = {r["event_type"]: r for r in connections(patterns())}
    assert "B" in conn["A"]["followed_by"] and "C" in conn["A"]["followed_by"]
    assert conn["A"]["n_followed_by"] >= 2


def test_data_summary_counts():
    rows = data_summary(sample())
    a = next(r for r in rows if r["event_type"] == "A")
    assert a["count"] == 8 and a["observations"] == 8 and a["mean_per_observation"] == 1.0


def test_interval_counts_split():
    rows = interval_counts(patterns(), [(0, 100), (100, 1000)], split_time=100)
    ab = next(r for r in rows if r["signature"] == "(A B)")
    # every A->B occurrence starts at t=0, so all are in [0,100] and before the split
    assert ab["in[0,100]"] == 8 and ab["before_split"] == 8 and ab["after_split"] == 0


def test_report_writes_all_default_outputs(tmp_path):
    res = calibrate(sample(), Config(min_lag=1), null="profile", B=50, q_target=0.05, seed=1)
    w = report(res, str(tmp_path), observations=sample(), title="unit test")
    for key in ("table", "durations", "roles", "connections", "data_summary",
                "dendrograms", "durations_plot", "occurrence_plot", "summary"):
        assert key in w and os.path.getsize(w[key]) > 0


def test_plots_render(tmp_path):
    res = calibrate(sample(), Config(min_lag=1), null="profile", B=50, q_target=0.05, seed=1)
    f1 = str(tmp_path / "occ.png"); f2 = str(tmp_path / "dur.png")
    occurrence_plot(sample(), f1)
    duration_plot(res, f2)
    assert os.path.getsize(f1) > 0 and os.path.getsize(f2) > 0
