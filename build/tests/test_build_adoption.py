"""The freeze produces a complete Town Meeting packet, and refuses a bad version."""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# The number a Town Meeting packet is reviewed against (ADOPTION-SPEC.md §1.2
# / §3.3; normalize_for_diff.py's own measured figure). If this legitimately
# changes -- a new draft lands, a normaliser rule changes -- that change must
# be understood and re-verified by hand (re-run the dry run, read the new
# per-article breakdown) BEFORE this constant is updated to match. Do not
# "fix the test" without doing that reading; the whole point of this command
# is that the number is reviewed, not merely reproduced.
#
# 243 -> 151 on 2026-08-24 (Task 2b) is a NORMALISATION IMPROVEMENT, NOT a
# content change: normalize_for_diff.py gained a table-number rule (`TABLE
# 4.1` / `Table 4.1` / `table 4.1` -> the current article's number, all three
# casings) and a frontmatter `article-number: "N"` rule, both driven by the
# same baseline->current article map the existing cross-reference renumbering
# already used. ~90 of the old 243 lines were table captions/refs and
# frontmatter fields that only moved because their article number moved --
# Articles 1, 5, 6, and 7 now report ZERO substantive changes (their entire
# prior diff was this renumbering noise). Nothing in the Code shrank; re-run
# `python3 build/adoption_breakdown.py` to see the same per-article split.
EXPECTED_TOTAL = 151


def test_refuses_a_decimal_version(tmp_path):
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.1-draft", "March 15, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "whole" in (r.stdout + r.stderr).lower()


def test_requires_a_meeting_date():
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0


def test_prints_the_substantive_change_breakdown():
    """The 243 lines going to the voters must be reviewable BEFORE the packet
    exists, not discovered at the meeting (ADOPTION-SPEC.md §7)."""
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--dry-run"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "substantive change" in out.lower()
    assert "article-09-definitions.md" in out


def test_dry_run_total_matches_the_reviewed_figure():
    """A regression test with teeth: deleting the not_text_comparable skip
    (or any other regression in the breakdown) must not leave the suite
    green while the packet quietly reports a different number. See
    EXPECTED_TOTAL's comment for what to do if this number legitimately
    changes."""
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--dry-run"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    m = re.search(r"TOTAL\s+(\d+)\s+substantive changed lines", r.stdout)
    assert m, r.stdout
    assert int(m.group(1)) == EXPECTED_TOTAL, r.stdout


def test_article_02_is_disclosed_not_counted():
    """article-02-prefatory.md's baseline (2,444 lines of markdown) moved into
    a native-Typst unit; a naive diff misreports that move as ~2,300 phantom
    deletions. It must appear in the breakdown, labelled NOT TEXT-COMPARABLE,
    and be excluded from TOTAL (which is how EXPECTED_TOTAL lands on 243
    instead of ~2,546)."""
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--dry-run"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "article-02-prefatory.md" in out
    assert "NOT TEXT-COMPARABLE" in out
    assert "excludes 1 not-text-comparable article" in out
    # And it must not have been silently counted into a much larger total.
    m = re.search(r"TOTAL\s+(\d+)\s+substantive changed lines", out)
    assert m and int(m.group(1)) < 1000, out


def test_rejects_a_mistyped_dry_run_flag(tmp_path):
    """The entire safety story of this command is 'preview before you build'.
    An unrecognised third argument must refuse loudly, not silently fall
    through to a real build that leaves releases/v1.0/ behind."""
    release_dir = REPO / "releases" / "v1.0"
    assert not release_dir.exists(), "a prior test/run left releases/v1.0 behind"
    try:
        r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                            "--dryrun"], cwd=REPO, capture_output=True, text=True)
        assert r.returncode != 0
        assert "unrecognised argument" in (r.stdout + r.stderr).lower()
        assert not release_dir.exists(), (
            "a mistyped flag silently performed the freeze and shipped a release directory")
    finally:
        if release_dir.exists():
            import shutil
            shutil.rmtree(release_dir)


def _write_map(tmp_path, files):
    path = tmp_path / "adoption-map.json"
    path.write_text(json.dumps({
        "baseline_version": "v0.1-baseline",
        "article_numbers": {},
        "files": files,
        "not_text_comparable": {},
    }))
    return path


def test_missing_baseline_file_fails_loudly(tmp_path):
    """build/redline_resolve.py already refuses (ADOPTION-SPEC.md §6.4: 'an
    unmatched file is an error, never a silent ... rendering') when a mapped
    baseline file does not exist at the baseline tag. adoption_breakdown.py
    -- the module this number is read from -- must refuse the same way
    instead of quietly counting the article as 100% newly added."""
    map_path = _write_map(tmp_path, {"fake-current.md": "fake-baseline-does-not-exist.md"})
    r = subprocess.run([sys.executable, "build/adoption_breakdown.py", "--map", str(map_path)],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "fix the map" in r.stderr.lower()


def test_missing_current_file_fails_loudly(tmp_path):
    """A mapped current file that no longer exists in the working tree must
    not vanish from both the listing and the TOTAL with no trace."""
    map_path = _write_map(tmp_path, {"fake-current-missing.md": "article-01-general.md"})
    r = subprocess.run([sys.executable, "build/adoption_breakdown.py", "--map", str(map_path)],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "fix the map" in r.stderr.lower()


# --- The freeze date and the meeting date are DIFFERENT facts ----------------
# Cover line 2 says "for adoption at Town Meeting, <meeting-date>"; line 3 says
# "Frozen <date>". build-adoption.sh passed the MEETING date for both, so the
# packet's own provenance line read "Frozen March 15, 2027" on a document
# frozen months earlier — a statement about the future, on the line that exists
# to say where the document came from.

def test_freeze_date_is_separate_from_the_meeting_date():
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--dry-run", "--freeze-date=January 2, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "Town Meeting, March 15, 2027" in r.stdout
    assert "frozen January 2, 2027" in r.stdout


def test_freeze_date_defaults_to_today_not_the_meeting_date():
    from datetime import date
    today = date.today().strftime("%B %-d, %Y")
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--dry-run"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert f"frozen {today}" in r.stdout


def test_rejects_an_empty_freeze_date():
    r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027",
                        "--freeze-date="], cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0


# --- The freeze must be tied to a commit ------------------------------------

def test_refuses_to_freeze_a_dirty_source_tree(tmp_path):
    """The meeting edition renders from the working tree; the adopted edition
    renders from the tag. If the tree is dirty at freeze time there is no
    commit that represents what the voters were shown, so the tie cannot be
    recorded and the freeze must refuse."""
    release_dir = REPO / "releases" / "v1.0"
    assert not release_dir.exists(), "a prior test/run left releases/v1.0 behind"
    stray = REPO / "source" / "ZZZ-uncommitted-test-file.md"
    assert not stray.exists()
    stray.write_text("stray\n")
    try:
        r = subprocess.run(["bash", "build/build-adoption.sh", "v1.0", "March 15, 2027"],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode != 0
        out = (r.stdout + r.stderr).lower()
        assert "refusing to freeze" in out
        assert "zzz-uncommitted-test-file.md" in out
        assert not release_dir.exists(), (
            "a refused freeze left a shipped-looking release directory behind")
    finally:
        stray.unlink(missing_ok=True)
        if release_dir.exists():
            import shutil
            shutil.rmtree(release_dir)
