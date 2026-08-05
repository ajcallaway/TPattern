"""The copy-and-adapt analysis template generator and its variants."""
import ast, pytest
from tpattern import new_analysis
from tpattern.starter import TEMPLATES


def test_all_templates_are_valid_python():
    assert set(TEMPLATES) == {"basic", "two_groups", "null_choice"}
    for name, src in TEMPLATES.items():
        ast.parse(src)                      # each generated script is valid Python
        assert "# <-- EDIT" in src and "read_table" in src


def test_new_analysis_default_and_named(tmp_path):
    p = new_analysis(tmp_path / "a.py")
    assert "recommend" in open(p).read() and "calibrate" in open(p).read()
    g = new_analysis(tmp_path / "g.py", template="two_groups")
    assert "group_contrast" in open(g).read() and "forest_plot" in open(g).read()
    n = new_analysis(tmp_path / "n.py", template="null_choice")
    assert "compare_nulls" in open(n).read()


def test_overwrite_guard_and_bad_name(tmp_path):
    f = tmp_path / "a.py"
    new_analysis(f)
    with pytest.raises(FileExistsError):
        new_analysis(f)
    new_analysis(f, overwrite=True)
    with pytest.raises(ValueError):
        new_analysis(tmp_path / "x.py", template="nope")


def test_basic_template_uses_readable_columns():
    assert "monte_carlo_p" in TEMPLATES["basic"] and "survives_fwer_holm" in TEMPLATES["basic"]
