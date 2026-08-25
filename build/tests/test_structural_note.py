"""The baseline redline's structural-changes note (ADOPTION-SPEC.md §4.3).

THE DEFECT THIS PINS. build-redline-full.sh hardcoded one cover caveat for both
the draft-to-draft and the baseline runs, mentioning only the figures/tables
limitation. So the packet redline showed Article 2 with ZERO marks and no
renumbering marks anywhere, and said nothing about either. A citizen reads that
as "Article 2 untouched, nothing renumbered." Suppressing ~126 renumbering
marks is honest only if the reader is told once, plainly -- these tests are
what keep that page in the packet.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent
BUILD = REPO / "build"
sys.path.insert(0, str(BUILD))

import structural_note  # noqa: E402
import adoption_map  # noqa: E402


def note_text(tmp_path, **kw):
    out = tmp_path / "note.pdf"
    structural_note.build_note(str(out), **kw)
    d = pymupdf.open(out)
    assert d.page_count == 1, (
        "the note must stay ONE page: it is the front matter's verso and the "
        "front-matter page count is parity-critical")
    return d[0].get_text()


def test_note_states_all_three_unmarkable_changes(tmp_path):
    t = note_text(tmp_path)
    low = t.lower()
    # 1. Article 2 unmarked, and explicitly not "untouched".
    assert "article 2" in low
    assert "unmarked" in low
    assert "untouched" in low, (
        "the note must say in words that no marks does NOT mean no change")
    # 2. The renumbering, stated once instead of marked 126 times.
    assert "renumber" in low
    assert "3 becomes 4" in low and "8 becomes 9" in low
    # 3. The pre-existing figures/tables limitation.
    assert "figure" in low and "current state" in low
    # And that Article 3 is wholly new, so its all-red body is not a surprise.
    assert "thoroughfares" in low


def test_note_reads_its_article_map_from_the_data(tmp_path):
    """The page and the suppression must not be able to disagree: the shift
    sentence is generated from adoption-map.json, not restated in prose."""
    m = tmp_path / "map.json"
    m.write_text(json.dumps({
        "baseline_version": "v0.1-baseline",
        "article_numbers": {"1": 1, "2": 3},
        "files": {},
        "not_text_comparable": {},
    }))
    t = note_text(tmp_path, map_path=str(m))
    assert "2 becomes 3" in t
    assert "3 becomes 4" not in t


def test_note_names_the_document_it_compares_against(tmp_path):
    t = note_text(tmp_path, old_label="the Code adopted November 3, 2020")
    assert "November 3, 2020" in t


# --- The parity-critical half ------------------------------------------------
# The note replaces the blank verso between the cover and the TOC. That keeps
# the pre-TOC page count EVEN (invariant 1: the TOC is rendered standalone and
# its binding margins bake in at its own parity) and the front matter EVEN
# (invariant 2: every Article opens on a recto). A note that changed either
# would silently break chrome across the whole document.

def test_front_note_replaces_the_blank_without_moving_anything(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    note = tmp_path / "note.pdf"
    structural_note.build_note(str(note))

    e = dict(os.environ, OUT_DIR=str(out), FRONT_NOTE_PDF=str(note))
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                       cwd=REPO, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    d = pymupdf.open(next(out.glob("*.pdf")))
    assert d.page_count == 117, (
        f"the note must not change the page count (got {d.page_count}); it "
        f"takes the place of the blank verso, it does not add a page")
    assert "HOW TO READ THIS REDLINE" in d[1].get_text(), (
        "the note belongs on the verso facing the cover — before any marked text")
    assert d[1].get_text().strip(), "page 2 is still blank: the note was not inserted"

    # Parity: the printed footer number on the last page must be
    # physical - FRONT_COUNT, and FRONT_COUNT must still be 4.
    last = d[-1].get_text()
    assert "113" in last, (
        f"the footer's page number moved — front matter is no longer 4 pages "
        f"(last page text: {last[-200:]!r})")
