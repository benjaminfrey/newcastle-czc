"""article-02.typ renders the fifth status (○ "No Permit Required", Right to
Farm Plan A) and refuses a cell combining `br` with another code (release-
machinery spec D3). Compiles a throwaway copy of the unit with edited data."""
import json
import shutil
import subprocess
from pathlib import Path

import pymupdf
import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "source"


def _compile(tmp_path: Path, code: str | None) -> subprocess.CompletedProcess:
    shutil.copy(SRC / "article-02.typ", tmp_path / "article-02.typ")
    data = json.loads((SRC / "article-02-data.json").read_text(encoding="utf-8"))
    if code is not None:
        data[0]["use_col1"][0]["entries"][0][1] = code
    (tmp_path / "article-02-data.json").write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run(
        ["typst", "compile", "--root", str(tmp_path), "--font-path", str(REPO / "style" / "fonts"),
         str(tmp_path / "article-02.typ"), str(tmp_path / "out.pdf")],
        capture_output=True, text=True)


def test_the_legend_shows_the_fifth_row_and_the_new_note(tmp_path):
    r = _compile(tmp_path, None)
    assert r.returncode == 0, r.stderr
    doc = pymupdf.open(tmp_path / "out.pdf")
    legend_pages = [p for p in doc if "USE TABLE LEGEND" in p.get_text()]
    assert len(legend_pages) == 13
    for p in legend_pages:
        text = " ".join(p.get_text().split())
        assert "No Permit Required" in text
        # The glyph itself is not asserted: its extracted text depends on the
        # fonts present (Apple Symbols locally, a fallback on CI).
        assert "Uses marked" in text
        assert "require no permit but must meet the standards of Article 7 Section 3." in text


def test_a_br_cell_renders(tmp_path):
    r = _compile(tmp_path, "br")
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("combo", ["br u", "u br"])
def test_br_combined_with_another_code_is_refused(tmp_path, combo):
    r = _compile(tmp_path, combo)
    assert r.returncode != 0
    assert "br" in r.stderr and "cannot share a cell" in r.stderr
