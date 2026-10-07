"""Chrome on the first page of a native-Typst unit.

Nothing in this repository asserted chrome on any unit's first page before this
file, which is why Article 2's first district page shipped without a footer in
the adopted v1.0 edition. The guards that caused it were written for a leading
parity blank that build-full-czc.sh no longer inserts.
"""
import os
import subprocess
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent

WORDMARK = "Newcastle Core Zoning Code"
DISTRICT_PANEL = "LOT DIMENSIONS"
RUNNING_HEAD = "DISTRICT STANDARDS"
TAB = "ARTICLE 2"
# Every probe is confined to the band where its chrome element sits, because
# the same words can also occur in body text (the running head's words occur at
# y ~ 268 on the first district page). A whole-page substring test would pass
# with the chrome element missing. Bands measured on the v0.24-draft integrated
# build, all 13 district pages (letter, 612 x 792 pt):
#   running head  y  26-39, x from 90      -> band y 0-50
#   footer        y 761-773                -> band y 745-792
#   article tab   x   6-23, y 149-202, text rotated 90 deg (dir 0,-1); pymupdf
#                 extracts it inside a clip like any other text. The tab sits in
#                 the OUTER margin, so both side strips are probed (x < 40 and
#                 x > width - 40) and either one satisfies the probe.
HEADER_BAND_PT = 50
FOOTER_BAND_TOP_PT = 745
TAB_STRIP_PT = 40
TAB_BAND_Y_PT = (130, 220)


def build_integrated(tmp_path, version="v0.24-draft", date_str="August 24, 2026", **env):
    """Build the integrated draft into tmp_path and return the open document."""
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    e = dict(os.environ, OUT_DIR=str(out), **env)
    r = subprocess.run(["bash", "build/build-full-czc.sh", version, date_str],
                       cwd=REPO, env=e, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return pymupdf.open(next(out.glob("*.pdf")))


def district_pages(d):
    """Indices of the district pages. Refuses to return an empty selection: a
    selector that matches nothing makes every 'missing == []' assertion below
    pass having examined zero pages."""
    pages = [i for i, p in enumerate(d) if DISTRICT_PANEL in p.get_text()]
    assert pages, (f"no district pages found ({DISTRICT_PANEL!r} appears on no "
                   f"page) - the selector drifted or Article 2 did not render")
    return pages


def _band(page, y0, y1):
    return pymupdf.Rect(0, y0, page.rect.width, y1)


def _tab_text(page):
    y0, y1 = TAB_BAND_Y_PT
    w = page.rect.width
    return "".join(page.get_text(clip=pymupdf.Rect(x0, y0, x1, y1))
                   for x0, x1 in ((0, TAB_STRIP_PT), (w - TAB_STRIP_PT, w)))


def test_every_district_page_carries_the_footer(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i in district_pages(d)
                   if WORDMARK not in d[i].get_text(
                       clip=_band(d[i], FOOTER_BAND_TOP_PT, d[i].rect.height))]
    finally:
        d.close()
    assert missing == [], (
        f"district pages without a footer: {missing}. Historically this was an "
        f"early return on here().page() == 1 at the header, footer and "
        f"background sites of article-02.typ (guards written for a leading "
        f"parity blank the build stopped inserting; removed 2026-10-07). A "
        f"reintroduced here().page() == 1 early return is the first thing to "
        f"check.")


def test_every_district_page_carries_the_article_tab(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i in district_pages(d) if TAB not in _tab_text(d[i])]
    finally:
        d.close()
    assert missing == [], f"district pages without the article tab: {missing}"


def test_every_district_page_carries_the_running_head(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i in district_pages(d)
                   if RUNNING_HEAD not in d[i].get_text(
                       clip=_band(d[i], 0, HEADER_BAND_PT))]
    finally:
        d.close()
    assert missing == [], f"district pages without the running head: {missing}"
