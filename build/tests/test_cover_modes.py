"""The cover's three states.

The adopted cover must not carry draft language, and the meeting cover must
still say NOT YET ADOPTED -- the vote has not happened when it is produced.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))
BASELINE = REPO / "docs" / "Newcastle Core Zoning Code.pdf"

import pymupdf  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("build_cover", REPO / "build" / "build-cover.py")
build_cover_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_cover_mod)


def cover_text(tmp_path, **kw):
    out = tmp_path / "cover.pdf"
    build_cover_mod.build_cover(str(BASELINE), str(out), kw.pop("version"),
                                kw.pop("date_str"), **kw)
    return pymupdf.open(out)[0].get_text()


def test_draft_mode_is_unchanged(tmp_path):
    t = cover_text(tmp_path, version="v0.24-draft", date_str="August 24, 2026")
    assert "INTEGRATED DRAFT" in t
    assert "NOT ADOPTED" in t


def test_meeting_mode_says_not_yet_adopted(tmp_path):
    t = cover_text(tmp_path, version="v1.0", date_str="August 24, 2026",
                   mode="meeting", event_date="March 15, 2027")
    assert "TOWN MEETING EDITION" in t
    assert "NOT YET ADOPTED" in t
    assert "March 15, 2027" in t


def test_adopted_mode_carries_no_draft_language(tmp_path):
    t = cover_text(tmp_path, version="v1.0", date_str="March 15, 2027",
                   mode="adopted", event_date="March 15, 2027")
    upper = t.upper()
    for banned in ("INTEGRATED DRAFT", "NOT ADOPTED", "NOT YET ADOPTED",
                   "FOR REVIEW ONLY", "TOWN MEETING EDITION"):
        assert banned not in upper, banned
    assert "March 15, 2027" in t


def test_adopted_mode_still_masks_the_clerk_attestation(tmp_path):
    """The masked signature block is a legal certification of the ORIGINAL
    adopted code. It must stay masked in every mode -- an adopted amendment is
    not the same document the clerk attested."""
    t = cover_text(tmp_path, version="v1.0", date_str="March 15, 2027",
                   mode="adopted", event_date="March 15, 2027")
    assert "Attested" not in t


# --- the amended-through line -------------------------------------------
#
# The baseline cover's third date line reads "AMENDED THROUGH: MARCH 24, 2025".
# On an adopted edition that is wrong -- the Code is amended through the
# adoption date. Before the vote it is right, so draft and meeting editions
# leave it alone.
#
# It is part of the SCANNED cover art, with no text layer, so a text assertion
# cannot see the stale line at all: a test that only checks extracted text
# passes even if the mask is deleted. The pixel tests below are the real gate.

def cover_pdf(tmp_path, name, **kw):
    out = tmp_path / f"{name}.pdf"
    build_cover_mod.build_cover(str(BASELINE), str(out), kw.pop("version"),
                                kw.pop("date_str"), **kw)
    return pymupdf.open(out)


def ink_pixels(doc, rect, dpi=600, threshold=150):
    pix = doc[0].get_pixmap(dpi=dpi, clip=rect)
    s, n = pix.samples, pix.n
    return sum(1 for i in range(0, len(s), n)
               if (s[i] + s[i + 1] + s[i + 2]) / 3 < threshold)


# Left part of the stale line, exposed when the new date is short enough that
# the replacement text does not reach back over it. "May 1, 2027" starts at
# x=409.9; the stale "AMEN..." glyphs begin at x=388.8.
STALE_STRIP = pymupdf.Rect(388, 721, 408, 734)


def test_adopted_mode_restates_the_amended_through_date(tmp_path):
    t = cover_text(tmp_path, version="v1.0", date_str="March 15, 2027",
                   mode="adopted", event_date="March 15, 2027")
    assert "AMENDED THROUGH: MARCH 15, 2027" in t


def test_adopted_mode_removes_the_stale_amended_through_line(tmp_path):
    """A short adoption date leaves the stale line's left end uncovered by the
    replacement text -- so if the mask were dropped or mis-placed, the old
    'AMEN...' glyphs would still be sitting there."""
    doc = cover_pdf(tmp_path, "adopted", version="v1.0", date_str="May 1, 2027",
                    mode="adopted", event_date="May 1, 2027")
    assert ink_pixels(doc, STALE_STRIP) == 0


def test_meeting_mode_keeps_the_baseline_amended_through_line(tmp_path):
    """Positive control for the test above -- same strip, ink present. Nothing
    is amended until the vote passes, so the packet keeps the baseline date."""
    doc = cover_pdf(tmp_path, "meeting", version="v1.0", date_str="August 24, 2026",
                    mode="meeting", event_date="March 15, 2027")
    assert ink_pixels(doc, STALE_STRIP) > 0
    assert "AMENDED THROUGH" not in cover_text(
        tmp_path, version="v1.0", date_str="August 24, 2026",
        mode="meeting", event_date="March 15, 2027").upper()


def test_draft_mode_keeps_the_baseline_amended_through_line(tmp_path):
    doc = cover_pdf(tmp_path, "draft", version="v0.24-draft", date_str="August 24, 2026")
    assert ink_pixels(doc, STALE_STRIP) > 0


def test_adopted_mode_requires_an_event_date_before_drawing(tmp_path):
    """The amended-through overprint dereferences event_date, so the mode/date
    validation has to run before anything is drawn."""
    import pytest
    with pytest.raises(ValueError, match="event_date"):
        build_cover_mod.build_cover(str(BASELINE), str(tmp_path / "x.pdf"),
                                    "v1.0", "March 15, 2027", mode="adopted")
