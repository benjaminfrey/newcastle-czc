"""Tests for ingest/triage.py — the per-page census + A/B/C/D tier assignment.

Offline, no network, no LLM. Exercises both synthetic PDFs (built in-process
with PyMuPDF, one per tier/edge case) and the three REAL fixture files named
in this workflow's task brief (read-only, under docs/ — never modified).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import fitz  # noqa: E402

from ingest import triage  # noqa: E402

REPO_ROOT = APP_ROOT.parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"

SHATTUCK = FIXTURES_DIR / "4.A.1. M003, L059 (White Rd, Shattuck) Subdivision Application 2025.10.07.pdf"
MORRISSEY = FIXTURES_DIR / "M011, L046-A (Morrissey, 53 Pleasant Street) SLZ Application, 2025 Submitted Documents.pdf"
STANTEC = FIXTURES_DIR / "M004, L087 (NT Land III, 684 US Route 1) (Stantec) application 2024.05.08.pdf"

requires_fixtures = pytest.mark.skipif(
    not (SHATTUCK.exists() and MORRISSEY.exists() and STANTEC.exists()),
    reason="real Findings of Fact fixture PDFs not present under docs/",
)


# --------------------------------------------------------------------------- #
# Synthetic PDFs — one built per test, exercising each tier boundary in
# isolation without depending on the real fixture files' exact contents.
# --------------------------------------------------------------------------- #


def _make_pdf(tmp_path: Path, pages: list[dict]) -> Path:
    """Build a throwaway PDF. Each `pages` entry may set:
        text: str
        width, height: page size in points (default Letter 612x792)
        rotate: int (0/90/180/270)
        rect_count: number of filled rectangles to draw (vector density)
    """
    doc = fitz.open()
    for spec in pages:
        w = spec.get("width", 612)
        h = spec.get("height", 792)
        page = doc.new_page(width=w, height=h)
        text = spec.get("text")
        if text:
            # insert_textbox wraps within the given rect -- plain
            # insert_text silently clips a single long line at the page
            # edge instead of wrapping, which would under-count char_count.
            rect = fitz.Rect(36, 36, w - 36, h - 36)
            page.insert_textbox(rect, text, fontsize=11)
        for i in range(spec.get("rect_count", 0)):
            x = 10 + (i % 40) * 5
            y = 10 + (i // 40) * 5
            page.draw_rect(fitz.Rect(x, y, x + 3, y + 3), color=(0, 0, 0))
        if spec.get("rotate"):
            page.set_rotation(spec["rotate"])
    out = tmp_path / "synthetic.pdf"
    doc.save(str(out))
    doc.close()
    return out


def test_tier_c_scan_for_near_empty_page(tmp_path: Path):
    pdf = _make_pdf(tmp_path, [{"text": ""}])
    pages = triage.triage_pdf(pdf)
    assert len(pages) == 1
    assert pages[0].tier == "C"
    assert pages[0].char_count < 20


def test_tier_a_native_for_labeled_form_text(tmp_path: Path):
    text = "Applicant: Jane Doe\nOwner: John Doe\nMap/Lot: 003-059\n" + ("filler text " * 20)
    pdf = _make_pdf(tmp_path, [{"text": text}])
    pages = triage.triage_pdf(pdf)
    assert pages[0].char_count >= 200
    assert pages[0].has_label_tokens is True
    assert pages[0].tier == "A"


def test_tier_b_for_long_prose_with_no_label_tokens(tmp_path: Path):
    # >=200 chars, no colon-labels, no bare date -- pure prose. The
    # "values with no labels" trap, prose flavor.
    text = "the quick brown fox jumps over the lazy dog several times " * 5
    pdf = _make_pdf(tmp_path, [{"text": text}])
    pages = triage.triage_pdf(pdf)
    assert pages[0].char_count >= 200
    assert pages[0].has_label_tokens is False
    assert pages[0].tier == "B"


def test_tier_b_for_short_hybrid_text(tmp_path: Path):
    text = "Applicant: Jane Doe"  # short, has a label, still < 200 chars
    pdf = _make_pdf(tmp_path, [{"text": text}])
    pages = triage.triage_pdf(pdf)
    assert 20 <= pages[0].char_count < 200
    assert pages[0].tier == "B"


def test_tier_d_for_oversized_page_area(tmp_path: Path):
    # 24in x 36in (a D-size architectural sheet) -- comfortably > tabloid.
    pdf = _make_pdf(tmp_path, [{"width": 24 * 72, "height": 36 * 72, "text": "Sheet C-2"}])
    pages = triage.triage_pdf(pdf)
    assert pages[0].is_plansheet is True
    assert pages[0].tier == "D"


def test_tier_d_for_high_vector_line_density(tmp_path: Path):
    pdf = _make_pdf(tmp_path, [{"rect_count": 80, "text": ""}])
    pages = triage.triage_pdf(pdf)
    assert pages[0].vector_path_count >= 60
    assert pages[0].tier == "D"


def test_tier_d_for_rotated_page_carrying_real_text(tmp_path: Path):
    text = "Sheet: C-2  Scale: 1\" = 40'  " + ("notes " * 10)
    pdf = _make_pdf(tmp_path, [{"text": text, "rotate": 90}])
    pages = triage.triage_pdf(pdf)
    assert pages[0].rotation == 90
    assert pages[0].char_count >= 20
    assert pages[0].tier == "D"


def test_rotated_but_blank_scanned_page_is_tier_c_not_d(tmp_path: Path):
    # A page rotation flag alone, on an otherwise-empty page, is a scanner
    # orientation artifact -- must NOT force tier D (this is exactly the
    # real Shattuck file's shape: see test_shattuck_is_all_tier_c below).
    pdf = _make_pdf(tmp_path, [{"text": "", "rotate": 270}])
    pages = triage.triage_pdf(pdf)
    assert pages[0].rotation == 270
    assert pages[0].char_count < 20
    assert pages[0].is_plansheet is False
    assert pages[0].tier == "C"


def test_page_sha256_is_deterministic_across_runs(tmp_path: Path):
    pdf = _make_pdf(tmp_path, [{"text": "Applicant: Jane Doe"}])
    first = triage.triage_pdf(pdf)[0].page_sha256
    second = triage.triage_pdf(pdf)[0].page_sha256
    assert first == second
    assert len(first) == 64  # hex sha256


def test_page_sha256_differs_for_different_content(tmp_path: Path):
    dir_a, dir_b = tmp_path / "a", tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    pdf1 = _make_pdf(dir_a, [{"text": "Applicant: Jane Doe"}])
    pdf2 = _make_pdf(dir_b, [{"text": "Applicant: John Smith, a much longer and different page"}])
    h1 = triage.triage_pdf(pdf1)[0].page_sha256
    h2 = triage.triage_pdf(pdf2)[0].page_sha256
    assert h1 != h2


def test_image_count_and_dimensions_recorded(tmp_path: Path):
    pdf = _make_pdf(tmp_path, [{"text": "Applicant: Jane Doe", "width": 612, "height": 792}])
    p = triage.triage_pdf(pdf)[0]
    assert p.width_pt == 612
    assert p.height_pt == 792
    assert p.image_count == 0  # synthetic page has no embedded raster image


def test_tier_census_counts_every_tier():
    pages = [
        triage.PageCensus(1, 0, 0, 0, 612, 792, 0, False, False, "C", "x"),
        triage.PageCensus(2, 500, 0, 0, 612, 792, 0, True, False, "A", "y"),
        triage.PageCensus(3, 50, 0, 0, 612, 792, 0, False, False, "B", "z"),
        triage.PageCensus(4, 0, 0, 90, 2000, 2000, 0, False, True, "D", "w"),
    ]
    assert triage.tier_census(pages) == {"A": 1, "B": 1, "C": 1, "D": 1}
    assert triage.any_plansheet(pages) is True


def test_unreadable_pdf_raises_and_writes_nothing(tmp_path: Path):
    bogus = tmp_path / "not-a-real.pdf"
    bogus.write_bytes(b"%PDF-1.4\nthis is not actually a valid xref/pdf body")
    with pytest.raises(triage.UnreadablePdf):
        triage.triage_pdf(bogus)


def test_has_label_tokens_recognizes_colon_labels():
    assert triage.has_label_tokens("Applicant: Jane Doe") is True
    assert triage.has_label_tokens("Owner - John Doe") is True


def test_has_label_tokens_recognizes_bare_dates():
    assert triage.has_label_tokens("10/10/2025\nDear Board,") is True


def test_has_label_tokens_false_for_plain_prose():
    assert triage.has_label_tokens("the quick brown fox jumps over the lazy dog") is False


# --------------------------------------------------------------------------- #
# Real fixture files — the task brief's own ground truth.
# --------------------------------------------------------------------------- #


@requires_fixtures
def test_shattuck_is_18_pages_all_tier_c():
    pages = triage.triage_pdf(SHATTUCK)
    assert len(pages) == 18
    assert triage.tier_census(pages) == {"A": 0, "B": 0, "C": 18, "D": 0}
    # Ground truth context: these are scanned, zero-text-layer pages that
    # also carry a page rotation flag from how the source was scanned --
    # exactly the case test_rotated_but_blank_scanned_page_is_tier_c_not_d
    # exercises synthetically.
    assert all(p.char_count < 20 for p in pages)


@requires_fixtures
def test_morrissey_is_4_pages_all_tier_a():
    pages = triage.triage_pdf(MORRISSEY)
    assert len(pages) == 4
    assert triage.tier_census(pages) == {"A": 4, "B": 0, "C": 0, "D": 0}


@requires_fixtures
def test_stantec_is_56_pages_mixed_with_at_least_15_non_native():
    pages = triage.triage_pdf(STANTEC)
    assert len(pages) == 56
    non_native = sum(1 for p in pages if p.tier != "A")
    assert non_native >= 15
    census = triage.tier_census(pages)
    assert sum(census.values()) == 56
    # "mixed" -- more than one tier actually present.
    assert sum(1 for n in census.values() if n > 0) > 1


@requires_fixtures
def test_real_fixture_page_sha256_values_are_all_unique_per_document():
    for path in (SHATTUCK, MORRISSEY, STANTEC):
        pages = triage.triage_pdf(path)
        hashes = [p.page_sha256 for p in pages]
        assert len(hashes) == len(set(hashes)), f"duplicate page_sha256 within {path.name}"
