"""Footer text per adoption state, and the exhibit banner rules."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pymupdf

REPO = Path(__file__).resolve().parent.parent.parent


def build(tmp_path, version, date_str, **env):
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    e = dict(os.environ, OUT_DIR=str(out), **env)
    subprocess.run(["bash", "build/build-full-czc.sh", version, date_str],
                   cwd=REPO, env=e, check=True, capture_output=True)
    pdf = next(out.glob("*.pdf"))
    d = pymupdf.open(pdf)
    return "\n".join(p.get_text() for p in d)


def build_standalone(article, version, date_str, **env):
    """build-standalone.sh has no OUT_DIR seam -- it always writes into
    releases/<version>/ in the real repo tree. Callers must pass a throwaway,
    test-only VERSION tag (never a real release tag); this helper deletes that
    directory again once the PDF has been read, so it leaves nothing behind."""
    release_dir = REPO / "releases" / version
    e = dict(os.environ, **env)
    try:
        subprocess.run(["bash", "build/build-standalone.sh", article, version, date_str],
                       cwd=REPO, env=e, check=True, capture_output=True)
        pdf = next(release_dir.glob(f"Article {article} *.pdf"))
        d = pymupdf.open(pdf)
        text = "\n".join(p.get_text() for p in d)
        page_count = d.page_count
        d.close()
    finally:
        shutil.rmtree(release_dir, ignore_errors=True)
    return text, page_count


def test_draft_footer_is_unchanged(tmp_path):
    t = build(tmp_path, "v0.24-draft", "August 24, 2026")
    assert "Draft v0.24-draft" in t


def test_adopted_footer_carries_the_adoption_date(tmp_path):
    t = build(tmp_path, "v1.0", "March 15, 2027",
              ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "Adopted: March 15, 2027" in t
    assert "Draft v" not in t


def test_adopted_exhibits_keep_provenance_but_drop_draft_language(tmp_path):
    t = build(tmp_path, "v1.0", "March 15, 2027",
              ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "approximate" in t.lower(), "the provenance note must survive"
    assert "not yet reviewed or adopted" not in t.lower()


def test_meeting_exhibits_carry_their_own_not_yet_adopted_marker(tmp_path):
    """Exhibit 3.1 is five pages and 3.2 a full-page map; both get photocopied
    away from the cover that carries the status."""
    t = build(tmp_path, "v1.0", "August 24, 2026",
              ADOPTION_MODE="meeting", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "not yet adopted" in t.lower()


# --- build-standalone.sh: same footer rule, since Task 7's build-adoption.sh
# builds the standalone Article 3 (the Town Meeting packet's own copy) via
# build-standalone.sh, not build-full-czc.sh. A standalone edition that still
# said "Draft" on a Town Meeting or Adopted document would be exactly the kind
# of self-contradiction §1.3 forbids -- and Article 3 is the one article most
# likely to circulate on its own.

def test_standalone_draft_footer_is_unchanged(tmp_path):
    t, pages = build_standalone("3", "v0.24-draft-test-standalone-draft", "August 24, 2026")
    assert "Draft v0.24-draft-test-standalone-draft" in t
    assert pages == 28


def test_standalone_meeting_footer_is_town_meeting_edition(tmp_path):
    t, pages = build_standalone(
        "3", "v1.0-test-standalone-meeting", "August 24, 2026",
        ADOPTION_MODE="meeting", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "Town Meeting Edition v1.0-test-standalone-meeting" in t
    assert "Draft v" not in t
    assert pages == 28


def test_standalone_adopted_footer_carries_the_adoption_date(tmp_path):
    t, pages = build_standalone(
        "3", "v1.0-test-standalone-adopted", "March 15, 2027",
        ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "Adopted: March 15, 2027" in t
    assert "Draft v" not in t
    assert pages == 28
