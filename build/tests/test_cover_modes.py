"""The cover's three states.

The adopted cover must not carry draft language, and the meeting cover must
still say NOT YET ADOPTED -- the vote has not happened when it is produced.
"""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))
BASELINE = REPO / "docs" / "Newcastle Core Zoning Code.pdf"

import pytest  # noqa: E402
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


V01_MAP = REPO / "build" / "tests" / "fixtures" / "adoption-map-v0.1-baseline.json"
AMENDED_ROW = pymupdf.Rect(300, 721, 566, 734)  # the whole third date line


def test_meeting_mode_keeps_the_scan_when_baseline_is_the_scan(tmp_path, monkeypatch):
    """Positive control for the adopted test above -- same strip, ink present.
    With the v0.1 map the baseline IS the scan (March 24, 2025), so there is
    nothing to restate and the scanned line is left alone."""
    monkeypatch.setenv("ADOPTION_MAP", str(V01_MAP))
    doc = cover_pdf(tmp_path, "meeting", version="v1.0", date_str="August 24, 2026",
                    mode="meeting", event_date="March 15, 2027")
    assert ink_pixels(doc, STALE_STRIP) > 0
    assert "AMENDED THROUGH" not in doc[0].get_text().upper()


def test_draft_mode_keeps_the_scan_when_baseline_is_the_scan(tmp_path, monkeypatch):
    monkeypatch.setenv("ADOPTION_MAP", str(V01_MAP))
    doc = cover_pdf(tmp_path, "draft", version="v0.24-draft", date_str="August 24, 2026")
    assert ink_pixels(doc, STALE_STRIP) > 0
    assert "as amended through March 24, 2025" in doc[0].get_text().replace("\n", " ")


OWN_DATE = "September 14, 2026"


@pytest.fixture
def own_map(tmp_path, monkeypatch):
    """A map this test owns: the v0.1 fixture's shape with a non-scan date."""
    m = json.loads(V01_MAP.read_text())
    m["baseline_amended_through"] = OWN_DATE
    p = tmp_path / "own-map.json"
    p.write_text(json.dumps(m))
    monkeypatch.setenv("ADOPTION_MAP", str(p))


def test_live_map_records_a_baseline_amended_through_date():
    import adoption_map
    v = adoption_map.load(REPO / "build" / "adoption-map.json").baseline_amended_through
    assert isinstance(v, str) and v.strip()


def test_draft_cover_states_the_baseline_it_was_generated_from(tmp_path, own_map):
    t = cover_text(tmp_path, version="v0.25-draft", date_str="October 11, 2026").replace("\n", " ")
    assert "proposed amendments to the Core Zoning Code" in t
    assert f"as amended through {OWN_DATE}" in t
    assert "includes proposed Article 3" not in t
    assert "March 24, 2025" not in t


def _reprint_alone_ink(tmp_path, text):
    """Ink in AMENDED_ROW of the reprint drawn by itself on a blank page."""
    d = pymupdf.open()
    pg = d.new_page(width=612, height=792)
    build_cover_mod._draw_tracked(
        pg, text, build_cover_mod.AMENDED_RIGHT, build_cover_mod.AMENDED_BASELINE,
        build_cover_mod.AMENDED_SIZE, build_cover_mod.AMENDED_TRACK,
        build_cover_mod.SCAN_INK)
    return d


def _ink_bitmap(doc, rect, dpi=600, threshold=150):
    pix = doc[0].get_pixmap(dpi=dpi, clip=rect)
    s, n = pix.samples, pix.n
    return [(s[i] + s[i + 1] + s[i + 2]) / 3 < threshold for i in range(0, len(s), n)]


@pytest.mark.parametrize("mode,kw", [
    ("draft", {}),
    ("meeting", {"event_date": "March 15, 2027"}),
    ("adopted", {"event_date": "September 14, 2026"}),
])
def test_baseline_amended_through_line_replaces_the_stale_scan(tmp_path, mode, kw, own_map):
    """With a test-owned map the baseline is September 14, 2026 (adopted: the event date), so the scanned
    "AMENDED THROUGH: MARCH 24, 2025" must be gone and the new date reprinted.

    Measured (600 dpi): the stale scan's ink spans x 388.8..563.9, but the
    reprinted "AMENDED THROUGH: SEPTEMBER 14, 2026" is longer and starts at
    x=367.3 -- so its own ink covers all of STALE_STRIP (388..408) and a
    "0 ink in the strip" assertion is impossible here (it is used only by the
    short-date adopted test). Instead the whole third date line is compared
    pixel for pixel with the reprint drawn ALONE on a blank page: the two must
    be identical. Any surviving stale glyph (mask deleted or mis-placed) adds
    ink the blank-page render lacks, so this fails without the mask."""
    doc = cover_pdf(tmp_path, mode, version="v1.0", date_str="August 24, 2026",
                    mode=mode, **kw)
    alone = _reprint_alone_ink(tmp_path, "AMENDED THROUGH: SEPTEMBER 14, 2026")
    got, want = _ink_bitmap(doc, AMENDED_ROW), _ink_bitmap(alone, AMENDED_ROW)
    differing = sum(1 for g, w in zip(got, want) if g != w)
    # Measured: 2 differing pixels of ~33,800 (sub-pixel anti-aliasing at the
    # threshold). A surviving stale line leaves thousands; 25 is a wide margin.
    assert differing <= 25, differing
    assert sum(_ink_bitmap(doc, AMENDED_ROW)) > 0  # not vacuous: the reprint is there
    assert "AMENDED THROUGH: SEPTEMBER 14, 2026" in doc[0].get_text().upper()


def test_cover_refuses_a_map_without_baseline_amended_through(tmp_path, monkeypatch):
    import json
    m = json.loads(V01_MAP.read_text())
    del m["baseline_amended_through"]
    p = tmp_path / "map.json"
    p.write_text(json.dumps(m))
    env = dict(__import__("os").environ, ADOPTION_MAP=str(p))
    r = subprocess.run([sys.executable, str(REPO / "build" / "build-cover.py"),
                        str(BASELINE), str(tmp_path / "x.pdf"), "v0.25-draft",
                        "October 11, 2026"], capture_output=True, text=True, env=env)
    assert r.returncode == 1
    assert "baseline_amended_through" in r.stderr
    assert not (tmp_path / "x.pdf").exists()


def test_adopted_mode_requires_an_event_date_before_drawing(tmp_path):
    """The amended-through overprint dereferences event_date, so the mode/date
    validation has to run before anything is drawn."""
    with pytest.raises(ValueError, match="event_date"):
        build_cover_mod.build_cover(str(BASELINE), str(tmp_path / "x.pdf"),
                                    "v1.0", "March 15, 2027", mode="adopted")
