"""Data-check tests for read_table: the E/W/I codes, and that the clean path
stays silent and unchanged. See tpattern/io.py CHECKS."""
import pytest
from tpattern import read_table, DataFormatError, CHECKS, check_reference


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


# ---- E codes: raise, nothing loaded ----

def test_E01_missing_column(tmp_path):
    f = write(tmp_path, "m.csv", "observation,event,time\np1,pass,0\np1,shot,3\n")
    with pytest.raises(DataFormatError) as e:
        read_table(f)
    assert "E01" in str(e.value) and "start" in str(e.value)


def test_E01_suggests_close_column(tmp_path):
    f = write(tmp_path, "m.csv", "observation,event,Start\np1,pass,0\np1,shot,3\n")
    with pytest.raises(DataFormatError) as e:
        read_table(f)
    assert "Start" in str(e.value)  # suggested the near-match


def test_E02_wrong_separator(tmp_path):
    f = write(tmp_path, "s.csv", "observation;event;start\np1;pass;0\np1;shot;3\n")
    with pytest.raises(DataFormatError) as e:
        read_table(f)
    assert "E02" in str(e.value)


def test_E03_header_only(tmp_path):
    f = write(tmp_path, "h.csv", "observation,event,start\n")
    with pytest.raises(DataFormatError) as e:
        read_table(f)
    assert "E03" in str(e.value)


def test_E04_all_rows_blank(tmp_path):
    f = write(tmp_path, "b.csv", "observation,event,start\n,pass,0\n,shot,3\n")
    with pytest.raises(DataFormatError) as e:
        read_table(f)
    assert "E04" in str(e.value)


def test_E05_no_pattern_capable_observation(tmp_path):
    # every observation has exactly one event
    f = write(tmp_path, "one.csv",
              "observation,event,start\np1,pass,0\np2,shot,0\np3,cross,0\n")
    with pytest.raises(DataFormatError) as e:
        read_table(f)
    assert "E05" in str(e.value)


# ---- W codes: load anyway, reported ----

def test_W10_non_numeric_times_dropped(tmp_path, capsys):
    f = write(tmp_path, "c.csv",
              "observation,event,start\np1,pass,0\np1,cross,01:03\np1,shot,5\n"
              "p2,pass,1\np2,shot,4\n")
    obs = read_table(f)                       # default report: a W fired, so it prints
    out = capsys.readouterr().out
    assert "W10" in out and "left out" in out
    # the one good p1 row + p2 both loaded; the mm:ss row dropped
    assert sum(len(o.events) for o in obs) == 4


def test_W13_near_duplicate_labels(tmp_path, capsys):
    f = write(tmp_path, "d.csv",
              "observation,event,start\np1,Pass,0\np1,pass,1\np1,shot,2\n"
              "p2,Pass,0\np2,shot,2\n")
    read_table(f)
    assert "W13" in capsys.readouterr().out


def test_clean_file_is_silent(tmp_path, capsys):
    f = write(tmp_path, "ok.csv",
              "observation,event,start\np1,pass,0\np1,shot,2\np2,pass,0\np2,shot,3\n")
    obs = read_table(f)
    assert capsys.readouterr().out == ""       # nothing to warn about
    assert len(obs) == 2


# ---- I codes: only shown with report="all" ----

def test_I20_effective_sample_only_with_all(tmp_path, capsys):
    f = write(tmp_path, "e.csv",
              "observation,event,start\np1,pass,0\np1,shot,2\np2,pass,0\n")  # p2 has 1 event
    read_table(f)                              # default: I-only, stays silent
    assert capsys.readouterr().out == ""
    read_table(f, report="all")                # report='all' surfaces the info note
    assert "I20" in capsys.readouterr().out


def test_report_false_silences_warnings(tmp_path, capsys):
    f = write(tmp_path, "c.csv",
              "observation,event,start\np1,pass,0\np1,x,bad\np1,shot,5\np2,a,0\np2,b,1\n")
    read_table(f, report=False)
    assert capsys.readouterr().out == ""


# ---- BOM (Excel) handled ----

def test_utf8_bom_is_stripped(tmp_path):
    p = tmp_path / "bom.csv"
    p.write_bytes("﻿observation,event,start\np1,pass,0\np1,shot,2\n".encode("utf-8"))
    obs = read_table(str(p))                   # must not see the BOM as part of the column name
    assert len(obs) == 1 and len(obs[0].events) == 2


# ---- registry integrity (Appendix A generates from this) ----

def test_check_reference_covers_every_code():
    rows = check_reference()
    assert {r["code"] for r in rows} == set(CHECKS)
    for r in rows:
        assert r["condition"] and r["fix"] and r["severity"]
