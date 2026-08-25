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
