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
import re
import subprocess
import sys
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent
BUILD = REPO / "build"
sys.path.insert(0, str(BUILD))

import structural_note  # noqa: E402
import adoption_map  # noqa: E402


import pytest as _pytest_rollover

_PRE_ROLLOVER_MAP = Path(__file__).resolve().parent / "fixtures" / "adoption-map-v0.1-baseline.json"


@_pytest_rollover.fixture(autouse=True)
def _pin_pre_rollover_adoption_map(monkeypatch):
    """These tests exercise the baseline-redline machinery -- renumbering,
    renamed article files, not-text-comparable articles -- against the
    v0.1-baseline map it was built for. The shipped map was rolled over to
    identity at the v1.0 adoption (September 14, 2026) and no longer exercises
    any of that, so the pre-rollover map is pinned here as a fixture."""
    monkeypatch.setenv("ADOPTION_MAP", str(_PRE_ROLLOVER_MAP))


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
# (invariant 2: the body's physical parity matches its logical numbering, so
# body page 1 is a recto; Articles are NOT padded to open on a recto, v0.19). A
# note that changed either would silently break chrome across the whole document.

# Front matter: cover, front note (the blank in an ordinary build), 2-page TOC.
FRONT_COUNT = 4
# The footer sits at y ~ 761-773 of a 792 pt page; body text can reach ~735.
FOOTER_BAND_PT = 40
# Verso reads "N | Newcastle Core Zoning Code"; recto "Newcastle Core Zoning Code | N".
FOOTER_NUMBER = re.compile(
    r"Newcastle Core Zoning Code\s*\|\s*(\d+)|(\d+)\s*\|\s*Newcastle Core Zoning Code")


def test_front_note_replaces_the_blank_without_moving_anything(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    note = tmp_path / "note.pdf"
    structural_note.build_note(str(note))

    e = dict(os.environ, OUT_DIR=str(out), FRONT_NOTE_PDF=str(note))
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                       cwd=REPO, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr

    # The claim is "the note does not add a page", so compare against the same
    # build without it rather than against a literal that moves every amendment.
    plain_out = tmp_path / "plain"
    plain_out.mkdir()
    rp = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "August 24, 2026"],
                        cwd=REPO, env=dict(os.environ, OUT_DIR=str(plain_out)),
                        capture_output=True, text=True)
    assert rp.returncode == 0, rp.stderr

    plain = d = None
    try:
        plain = pymupdf.open(next(plain_out.glob("*.pdf")))
        d = pymupdf.open(next(out.glob("*.pdf")))
        assert d.page_count == plain.page_count, (
            f"the note changed the page count: {plain.page_count} without it, "
            f"{d.page_count} with it. It takes the place of the blank verso.")
        # Without this the comparison above could pass with the note doing
        # nothing: the page it replaces must be the blank, and in the plain
        # build it must be blank.
        assert not plain[1].get_text().strip(), (
            "the plain build's page 2 is not blank, so there is no blank for "
            "the note to replace")
        assert "HOW TO READ THIS REDLINE" in d[1].get_text(), (
            "the note belongs on the verso facing the cover — before any marked text")
        assert d[1].get_text().strip(), "page 2 is still blank: the note was not inserted"

        # Parity invariant: the printed footer number equals the physical page
        # minus the 4-page front matter (cover, front note, two-page TOC), on
        # EVERY body page — not just the last one, and not a literal that moves
        # with the Code's length. The footer is read from a clipped band at the
        # foot of the page: the wordmark and digits also occur in body text.
        printed = {}
        for i in range(FRONT_COUNT, d.page_count):
            page = d[i]
            band = page.get_text(clip=pymupdf.Rect(
                0, page.rect.height - FOOTER_BAND_PT, page.rect.width, page.rect.height))
            m = FOOTER_NUMBER.search(band)
            printed[i + 1] = int(m.group(1) or m.group(2)) if m else None

        # Non-degeneracy: the check below is vacuous if it parsed nothing.
        body_pages = d.page_count - FRONT_COUNT
        assert body_pages > 0, "no body pages beyond the front matter"
        unparsed = [pg for pg, n in printed.items() if n is None]
        assert unparsed == [], (
            f"body pages with no readable footer number: {unparsed}. Every page "
            f"after the front matter carries one. A footer-less body page may be "
            f"a new structural pad or unit boundary (e.g. the Article 2 "
            f"pad-to-odd) rather than a chrome bug; check the build's page "
            f"structure before the footer code.")

        wrong = {pg: (n, pg - FRONT_COUNT) for pg, n in printed.items()
                 if n != pg - FRONT_COUNT}
        assert wrong == {}, (
            f"footer number != physical page - {FRONT_COUNT} on these pages "
            f"(physical: (printed, expected)): {wrong}. Front matter is "
            f"{FRONT_COUNT} pages and logical must equal physical.")

        # The other side of the same fact: the front matter itself is numberless.
        for i in range(FRONT_COUNT):
            page = d[i]
            band = page.get_text(clip=pymupdf.Rect(
                0, page.rect.height - FOOTER_BAND_PT, page.rect.width, page.rect.height))
            assert FOOTER_NUMBER.search(band) is None, (
                f"physical page {i + 1} is front matter but prints a footer "
                f"number: {band!r}")
    finally:
        for doc in (plain, d):
            if doc is not None:
                doc.close()
