# build/tests/test_unit_chrome.py
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


def build_integrated(tmp_path, version="v0.24-draft", date_str="August 24, 2026", **env):
    """Build the integrated draft into tmp_path and return the open document."""
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    e = dict(os.environ, OUT_DIR=str(out), **env)
    subprocess.run(["bash", "build/build-full-czc.sh", version, date_str],
                   cwd=REPO, env=e, check=True, capture_output=True)
    return pymupdf.open(next(out.glob("*.pdf")))


def test_every_district_page_carries_the_footer(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i, page in enumerate(d)
                   if DISTRICT_PANEL in page.get_text()
                   and WORDMARK not in page.get_text()]
    finally:
        d.close()
    assert missing == [], (
        f"district pages without a footer: {missing}. article-02.typ returns "
        f"early on here().page() == 1, a guard written for a leading parity "
        f"blank the build no longer inserts.")


def test_every_district_page_carries_the_article_tab(tmp_path):
    d = build_integrated(tmp_path)
    try:
        missing = [i + 1 for i, page in enumerate(d)
                   if DISTRICT_PANEL in page.get_text()
                   and "ARTICLE 2" not in page.get_text()]
    finally:
        d.close()
    assert missing == [], f"district pages without the article tab: {missing}"
