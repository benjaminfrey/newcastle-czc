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
EXPECTED_TOTAL = 243


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
