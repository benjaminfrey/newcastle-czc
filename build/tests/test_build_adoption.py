"""The freeze produces a complete Town Meeting packet, and refuses a bad version."""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# The reviewed headline number is NOT pinned here any more. It was EXPECTED_TOTAL
# = 151, measured against the working tree on 2026-08-24; it went red the moment
# an amendment landed, and re-pinning it is how a reviewed number silently
# becomes a reproduced one. The number is now asserted two ways: against a frozen
# fixture tree (the instrument works) and as the sum of its own per-article lines
# (the instrument is self-consistent). The release operator still reads the real
# breakdown before a freeze -- that is build-adoption.sh's job, not this file's.


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


def test_breakdown_reports_the_fixture_tree_exactly():
    """The instrument is pinned against a frozen input, not against source/.

    The fixture is the v0.1-baseline Article 1 with exactly one line changed
    (see fixtures/breakdown-src/README.md), so the breakdown must report 2
    changed lines for it: one deleted, one added. The live tree reports 0 for
    Article 1 under the same map, so the "2" can only come from the fixture --
    an ignored --src-dir cannot satisfy this. The fixture holds only Article 1
    while the map names nine, so the breakdown refuses (exit 1) at the first
    missing file; the refusal must name the fixture directory."""
    fixture = Path(__file__).resolve().parent / "fixtures" / "breakdown-src"
    r = subprocess.run(
        [sys.executable, "build/adoption_breakdown.py", "--src-dir", str(fixture),
         "--map", str(_PRE_ROLLOVER_MAP)],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 1, (r.returncode, r.stdout, r.stderr)
    assert re.search(r"^\s+article-01-general\.md\s+2 lines$", r.stdout, re.M), r.stdout
    assert str(fixture) in r.stderr, r.stderr


def test_breakdown_total_equals_the_sum_of_its_own_lines():
    """The invariant: whatever the per-article numbers are, the TOTAL is their
    sum. This holds at every release, so it never needs re-pinning -- and it
    catches the failure a literal cannot: a total that stops matching its own
    breakdown (e.g. an article dropped from, or double-counted into, the sum)."""
    r = subprocess.run([sys.executable, "build/adoption_breakdown.py"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    per_article = [int(m) for m in re.findall(r"^\s+article-\S+\s+(\d+) lines?$",
                                              r.stdout, re.M)]
    total = int(re.search(r"^\s+TOTAL\s+(\d+) substantive changed lines?",
                          r.stdout, re.M).group(1))
    assert per_article, f"no per-article lines parsed from:\n{r.stdout}"
    assert any(per_article), (
        f"every article reports 0 \u2014 the map pin is gone, so this invariant is vacuous:\n{r.stdout}")
    assert sum(per_article) == total, (
        f"TOTAL {total} is not the sum of its own per-article lines "
        f"{per_article} (sum {sum(per_article)})")


def test_article_02_is_disclosed_not_counted():
    """article-02-prefatory.md's baseline (2,444 lines of markdown) moved into
    a native-Typst unit; a naive diff misreports that move as ~2,300 phantom
    deletions. It must appear in the breakdown, labelled NOT TEXT-COMPARABLE,
    and be excluded from TOTAL (otherwise the total would be ~2,500 instead of
    a few hundred)."""
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
    through to a real build that leaves a release directory behind. Uses a
    version that will never exist -- releases/v1.0 is now a real, committed
    adoption release, so it cannot double as a scratch target."""
    release_dir = REPO / "releases" / "v9.0"
    assert not release_dir.exists(), "a prior test/run left releases/v9.0 behind"
    try:
        r = subprocess.run(["bash", "build/build-adoption.sh", "v9.0", "March 15, 2027",
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


def test_breakdown_accepts_a_source_directory(tmp_path):
    """The breakdown must be runnable against a fixture tree, or every test of
    it is pinned to whatever is in source/ today."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "article-01-general.md").write_text(
        '---\narticle-number: "1"\narticle-name: "General Standards"\n---\n\n'
        '# Article 1 General Standards\n\n## 1. CORE ZONING CODE\n')
    r = subprocess.run(
        [sys.executable, "build/adoption_breakdown.py", "--src-dir", str(src)],
        cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1), r.stderr
    assert "article-01-general.md" in r.stdout, r.stdout
    # The listing alone cannot tell a read seam from an ignored flag (the live
    # tree has an article-01 too). The fixture is missing every other mapped
    # article, so the refusal must name the fixture directory, not source/.
    assert r.returncode == 1 and str(src) in r.stderr, r.stderr


def test_breakdown_honours_src_dir_env_and_flag_wins(tmp_path):
    """SRC_DIR is the same seam build-full-czc.sh uses. The flag beats it."""
    import os
    env_src, flag_src = tmp_path / "from-env", tmp_path / "from-flag"
    env_src.mkdir()
    flag_src.mkdir()
    env = {**os.environ, "SRC_DIR": str(env_src)}
    cmd = [sys.executable, "build/adoption_breakdown.py"]
    r = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True)
    assert r.returncode == 1 and str(env_src) in r.stderr, r.stderr
    r = subprocess.run(cmd + ["--src-dir", str(flag_src)], cwd=REPO, env=env,
                       capture_output=True, text=True)
    assert r.returncode == 1 and str(flag_src) in r.stderr, r.stderr
    assert str(env_src) not in r.stderr, r.stderr


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
    release_dir = REPO / "releases" / "v9.0"
    assert not release_dir.exists(), "a prior test/run left releases/v9.0 behind"
    stray = REPO / "source" / "ZZZ-uncommitted-test-file.md"
    assert not stray.exists()
    stray.write_text("stray\n")
    try:
        r = subprocess.run(["bash", "build/build-adoption.sh", "v9.0", "March 15, 2027"],
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
