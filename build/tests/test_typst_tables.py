"""build/typst_tables.py -- Article 3's raw-Typst tables as readable markdown.
Strict: anything outside the measured grammar is refused (None), so czc_md
writes a pointer instead of garbled text."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402
import typst_tables as tt  # noqa: E402

REPO = BUILD.parent
ART3 = "article-03-streets-roads-driveways.md"


def _blocks():
    text = subprocess.run(["git", "-C", str(REPO), "show", f"v1.0:source/{ART3}"],
                          capture_output=True, text=True, check=True).stdout
    return czc_diff.split_markdown(text)[2]


def _table(md):
    lines = md.split("\n")
    rows = [ln for ln in lines if ln.startswith("| ")]
    return lines[0], rows


def test_the_four_tables_convert_exactly():
    got = [tt.to_markdown(b) for b in _blocks()]
    assert None not in got
    shapes = []
    for md in got:
        caption, rows = _table(md)
        assert md.split("\n")[1] == ""
        cols = rows[0].count(" | ") + 1
        shapes.append((caption.split()[1], len(rows) - 1, cols))   # minus the separator row
    assert shapes == [("3.4", 15, 2), ("3.5", 4, 3), ("3.2", 9, 2), ("3.3", 8, 6)]
    t34, t35, t32, t33 = got
    assert "| D1 Rural | R2 Rural Road; R3 Rural Lane on low-volume segments; R1 Connector Road on transition segments |" in t34
    assert "| Design Speed (MPH) | Sight Distance (FT) |" in t32
    assert "| 60 | 645 |" in t32
    assert "| **Construction** |  |  |  |  |  |" in t33
    assert "| Total HBP thickness | 2½″ | 2″ | 2½″ | 2″ or gravel surface | n/a |" in t33
    assert "| :--- | :--- | :--- |" in t35
    assert "engineer's stamp" in t35


def test_the_converted_tables_parse_as_tables():
    if not shutil.which("pandoc"):
        pytest.skip("pandoc not installed")
    for md in (tt.to_markdown(b) for b in _blocks()):
        r = subprocess.run(["pandoc", "-f", "markdown", "-t", "html"], input=md,
                           capture_output=True, text=True)
        assert r.returncode == 0 and "<table" in r.stdout


@pytest.mark.parametrize("edit", [
    lambda b: b.replace("#table(", "#table(stroke: none,\n    #table(", 1),
    lambda b: b.replace("[20], [155],", "table.cell(colspan: 2)[20],", 1),
    lambda b: b.replace("[20]", "[#strong[20]]", 1),
    lambda b: b.replace("TABLE 3.2 SIGHT DISTANCE", "Sight distance", 1),
    lambda b: b.replace("[20], [155],", "[20],", 1),               # a short row
    lambda b: b.replace(                                            # header after a row
        "table.header([Design Speed (MPH)], [Sight Distance (FT)]),\n    [20], [155],",
        "[20], [155],\n    table.header([Design Speed (MPH)], [Sight Distance (FT)]),", 1),
    lambda b: b.replace("SIGHT DISTANCE", "SIGHT #footnote[x] DISTANCE", 1),
    lambda b: b.replace("SIGHT DISTANCE", "SIGHT $x$ DISTANCE", 1),
    lambda b: b.replace("[155]", "[155~ft]", 1),
])
def test_anything_unrecognised_is_refused(edit):
    sight = next(b for b in _blocks() if "TABLE 3.2" in b)
    assert tt.to_markdown(sight) is not None                        # the control
    assert tt.to_markdown(edit(sight)) is None


def test_a_pipe_in_a_cell_is_escaped():
    sight = next(b for b in _blocks() if "TABLE 3.2" in b)
    md = tt.to_markdown(sight.replace("[20]", "[20 | 25]", 1))
    assert "| 20 \\| 25 | 155 |" in md
