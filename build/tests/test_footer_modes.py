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


def build_standalone(article, version, date_str, tmp_path, **env):
    """Builds into tmp_path via OUT_DIR, so nothing under releases/ is created
    or deleted. The version must still be well-formed, because
    build-standalone.sh enforces the version-state rule in both directions
    (build/version_state.py --require)."""
    out = tmp_path / "standalone"
    e = dict(os.environ, OUT_DIR=str(out), **env)
    subprocess.run(["bash", "build/build-standalone.sh", article, version, date_str],
                   cwd=REPO, env=e, check=True, capture_output=True)
    pdfs = [p for p in out.glob("*.pdf") if " — Redline" not in p.name]
    assert len(pdfs) == 1, f"expected exactly one standalone pdf, found {pdfs}"
    d = pymupdf.open(pdfs[0])
    try:
        return "\n".join(p.get_text() for p in d), d.page_count
    finally:
        d.close()


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
    away from the cover that carries the status.

    Also pins the cover's TWO DIFFERENT DATES: the packet is frozen on the
    build date and voted on at the meeting date, and cover line 3's "Frozen
    <date>" must be the former. build-adoption.sh passed the meeting date for
    both until the final review, printing a future freeze date on the packet's
    own provenance line."""
    t = build(tmp_path, "v1.0", "August 24, 2026",
              ADOPTION_MODE="meeting", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "not yet adopted" in t.lower()
    assert "Frozen August 24, 2026" in t
    assert "Frozen March 15, 2027" not in t


# --- The reverse of the whole-number rule (ADOPTION-SPEC.md §6.1). -----------
# Refusing draft chrome on a whole number was implemented; refusing ADOPTION
# chrome on a draft number was not, and that direction is the dangerous one:
# it produced a cover and footer claiming adoption, from the working tree,
# with neither the content-identity nor the draft-residue gate (both live in
# build-adopted.sh) -- reachable with one environment variable.

def test_adopted_mode_refuses_a_draft_version(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    e = dict(os.environ, OUT_DIR=str(out), ADOPTION_MODE="adopted",
             ADOPTION_EVENT_DATE="March 15, 2027")
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "March 15, 2027"],
                       cwd=REPO, env=e, capture_output=True, text=True)
    assert r.returncode != 0, "a decimal version was stamped ADOPTED"
    assert "adoption version" in (r.stdout + r.stderr).lower()
    assert not list(out.glob("*.pdf")), "a refused adopted build still produced a PDF"


def test_meeting_mode_refuses_a_draft_version(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    e = dict(os.environ, OUT_DIR=str(out), ADOPTION_MODE="meeting",
             ADOPTION_EVENT_DATE="March 15, 2027")
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.24-draft", "March 15, 2027"],
                       cwd=REPO, env=e, capture_output=True, text=True)
    assert r.returncode != 0
    assert not list(out.glob("*.pdf"))


def test_standalone_adopted_mode_refuses_a_draft_version():
    """Article 3 is the one article most likely to circulate on its own, so the
    standalone builder must refuse the same bypass the integrated one does."""
    release_dir = REPO / "releases" / "v0.97-draft"
    assert not release_dir.exists()
    e = dict(os.environ, ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    r = subprocess.run(["bash", "build/build-standalone.sh", "3", "v0.97-draft",
                        "March 15, 2027"], cwd=REPO, env=e,
                       capture_output=True, text=True)
    try:
        assert r.returncode != 0
        assert not release_dir.exists(), (
            "a refused standalone build left a release directory behind")
    finally:
        shutil.rmtree(release_dir, ignore_errors=True)


# --- build-standalone.sh: same footer rule, since Task 7's build-adoption.sh
# builds the standalone Article 3 (the Town Meeting packet's own copy) via
# build-standalone.sh, not build-full-czc.sh. A standalone edition that still
# said "Draft" on a Town Meeting or Adopted document would be exactly the kind
# of self-contradiction §1.3 forbids -- and Article 3 is the one article most
# likely to circulate on its own.

def test_standalone_draft_footer_is_unchanged(tmp_path):
    t, pages = build_standalone("3", "v0.94-draft", "August 24, 2026", tmp_path)
    assert "Draft v0.94-draft" in t
    assert pages == 28


def test_standalone_meeting_footer_is_town_meeting_edition(tmp_path):
    t, pages = build_standalone(
        "3", "v94.0", "August 24, 2026", tmp_path,
        ADOPTION_MODE="meeting", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "Town Meeting Edition v94.0" in t
    assert "Draft v" not in t
    assert pages == 28


def test_standalone_adopted_footer_carries_the_adoption_date(tmp_path):
    t, pages = build_standalone(
        "3", "v93.0", "March 15, 2027", tmp_path,
        ADOPTION_MODE="adopted", ADOPTION_EVENT_DATE="March 15, 2027")
    assert "Adopted: March 15, 2027" in t
    assert "Draft v" not in t
    assert pages == 28
