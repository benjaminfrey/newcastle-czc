"""The freeze produces a complete Town Meeting packet, and refuses a bad version."""
import json
import os
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
    """The few hundred lines going to the voters must be reviewable BEFORE the packet
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
    # A bad or incomplete path is not a map error: adoption-map.json gates the
    # freeze and must not be named as the thing to fix. (The default-tree case,
    # where the map IS the cause, keeps 'Fix the map' -- see the two tests above.)
    assert "fix the map" not in r.stderr.lower(), r.stderr
    assert "incomplete" in r.stderr, r.stderr


def test_breakdown_honours_src_dir_env_and_flag_wins(tmp_path):
    """SRC_DIR is the same seam build-full-czc.sh uses. The flag beats it."""
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

# --- The freeze goes through the release driver ----------------------------

import shutil

import pytest

_SCRIPT = (REPO / "build" / "build-adoption.sh").read_text()


@pytest.fixture
def wt(tmp_path):
    """A detached worktree of HEAD carrying the working-tree build-adoption.sh, so
    freezes write into it and never into the real repo."""
    path = tmp_path / "wt"
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "--detach", str(path), "HEAD"],
                   check=True, capture_output=True)
    shutil.copy(REPO / "build" / "build-adoption.sh", path / "build" / "build-adoption.sh")
    try:
        yield path
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(path)],
                       capture_output=True)


def _stub_driver(tmp_path, wt, exit_code=0, place=True):
    """A stand-in for build-release.sh: records argv and environment and, if
    `place`, places a release dir inside the worktree as the real driver does."""
    log = tmp_path / "driver.log"
    stub = tmp_path / "stub-release.sh"
    stub.write_text(
        '#!/usr/bin/env bash\n'
        f'printf "%s\\n" "$@" > "{log}"\n'
        f'echo "MODE=$ADOPTION_MODE DATE=$ADOPTION_EVENT_DATE" >> "{log}"\n'
        + (f'mkdir -p "{wt}/releases/$1"\n'
           f'echo x > "{wt}/releases/$1/Newcastle CZC (Town Meeting Edition $1).md"\n'
           if place else '')
        + f'exit {exit_code}\n')
    return stub, log


def _freeze(tmp_path, wt, extra=(), exit_code=0, place=True, env=None):
    stub, log = _stub_driver(tmp_path, wt, exit_code, place)
    r = subprocess.run(
        ["bash", str(wt / "build" / "build-adoption.sh"), "v9.0", "March 15, 2027",
         "--freeze-date=January 2, 2027", *extra],
        cwd=wt, capture_output=True, text=True,
        env={**os.environ, "CZC_LEAF_RELEASE": str(stub), **(env or {})})
    return r, log


def test_refuses_to_freeze_a_dirty_source_tree(tmp_path, wt):
    """The meeting edition renders from the working tree; the adopted edition
    renders from the tag. A dirty tree has no commit representing what voters
    saw, so the freeze refuses -- before the driver runs."""
    (wt / "source" / "ZZZ-uncommitted-test-file.md").write_text("stray\n")
    r, log = _freeze(tmp_path, wt)
    assert r.returncode != 0
    out = (r.stdout + r.stderr).lower()
    assert "refusing to freeze" in out and "zzz-uncommitted-test-file.md" in out
    assert not log.exists(), "the driver ran despite a dirty source/"
    assert not (wt / "releases" / "v9.0").exists()


def test_freeze_has_no_article_number_in_a_build_command_and_one_driver_call():
    code = "\n".join(l for l in _SCRIPT.splitlines() if not l.lstrip().startswith("#"))
    assert "build-standalone.sh" not in code
    assert not re.search(r"\bArticle \d", code), "an Article number in a build command"
    assert code.count("build-release.sh") == 1, code.count("build-release.sh")
    assert 'LEAF_RELEASE="${CZC_LEAF_RELEASE:-' in code


def test_stale_strings_are_gone_from_the_script():
    for stale in ("March 24, 2025", "3-8 become 4-9", "entirely new"):
        assert stale not in _SCRIPT, stale


def test_freeze_calls_the_driver_in_meeting_mode_and_writes_provenance(tmp_path, wt):
    r, log = _freeze(tmp_path, wt)
    assert r.returncode == 0, r.stdout + r.stderr
    argv = log.read_text().splitlines()
    baseline = json.loads(_PRE_ROLLOVER_MAP.read_text())["baseline_version"]
    assert argv[:3] == ["v9.0", "January 2, 2027", f"--old-ver={baseline}"], argv
    assert "--calls" not in argv
    assert "MODE=meeting DATE=March 15, 2027" in argv
    prov = json.loads((wt / "releases" / "v9.0" / "frozen-from.json").read_text())
    assert set(prov) == {"_README", "version", "meeting_date", "frozen_on",
                         "frozen_from_commit", "frozen_source_tree"}
    assert prov["version"] == "v9.0"
    assert prov["meeting_date"] == "March 15, 2027"
    assert prov["frozen_on"] == "January 2, 2027"
    assert "remove releases/v9.0/" in r.stdout


def test_freeze_passes_calls_through(tmp_path, wt):
    calls = tmp_path / "calls.json"
    calls.write_text("{}")
    r, log = _freeze(tmp_path, wt, extra=("--calls", str(calls)))
    assert r.returncode == 0, r.stdout + r.stderr
    argv = log.read_text().splitlines()
    assert argv[argv.index("--calls") + 1] == str(calls), argv


def test_driver_refusal_exits_1_and_writes_nothing(tmp_path, wt):
    r, _ = _freeze(tmp_path, wt, exit_code=1, place=False)
    assert r.returncode == 1
    assert "nothing was frozen" in r.stderr
    assert not (wt / "releases" / "v9.0").exists()


def test_failure_after_the_driver_placed_the_packet_says_so(tmp_path, wt):
    r, _ = _freeze(tmp_path, wt, exit_code=1, place=True)
    assert r.returncode == 1
    assert "nothing was frozen" not in r.stderr
    assert "incomplete" in r.stderr and "releases/v9.0" in r.stderr
    assert not (wt / "releases" / "v9.0" / "frozen-from.json").exists()


@pytest.mark.parametrize("var", [
    "SRC_DIR", "OUT_DIR", "OUT_NAME_OVERRIDE", "STANDALONE_FRONT_NOTE", "SECTION_MAP",
    "REDLINE_OUT", "REDLINE_MD_OUT", "CZC_LEAF_FULL", "CZC_LEAF_REDLINE_FULL",
    "CZC_LEAF_STANDALONE", "CZC_LEAF_REDLINE_STANDALONE"])
def test_inherited_build_overrides_are_refused_before_the_driver(tmp_path, wt, var):
    r, log = _freeze(tmp_path, wt, env={var: "/somewhere/else"})
    assert r.returncode == 1
    assert var in r.stderr
    assert not log.exists(), "the driver ran with an inherited override"
    assert not (wt / "releases" / "v9.0").exists()


def test_dry_run_exits_before_any_driver_call(tmp_path, wt):
    r, log = _freeze(tmp_path, wt, extra=("--dry-run",))
    assert r.returncode == 0, r.stderr
    assert not log.exists()
    assert not (wt / "releases" / "v9.0").exists()


# --- --render-summary --------------------------------------------------------

def _render(wt, *extra):
    return subprocess.run(
        ["bash", str(wt / "build" / "build-adoption.sh"), "v9.0", "March 15, 2027",
         "--render-summary", *extra],
        cwd=wt, capture_output=True, text=True)


def test_render_summary_refuses_without_a_packet(wt):
    r = _render(wt)
    assert r.returncode == 1
    assert "no frozen packet" in r.stderr


def test_render_summary_refuses_without_the_md(wt):
    (wt / "releases" / "v9.0").mkdir(parents=True)
    r = _render(wt)
    assert r.returncode == 1
    assert "does not exist" in r.stderr


def test_render_summary_refuses_the_generated_skeleton(wt):
    import sys as _sys
    _sys.path.insert(0, str(REPO / "build"))
    import summary_skeleton
    packet = wt / "releases" / "v9.0"
    packet.mkdir(parents=True)
    (packet / "Summary of Changes v9.0.md").write_text(
        "# Summary of Changes\n\n" + summary_skeleton.PLACEHOLDER + "\n")
    r = _render(wt)
    assert r.returncode == 1
    assert "skeleton" in r.stderr
    assert not (packet / "Summary of Changes v9.0.pdf").exists()


@pytest.mark.parametrize("extra", [("--dry-run",), ("--calls", "x.json"),
                                   ("--freeze-date=January 2, 2027",)])
def test_render_summary_cannot_be_combined_with_freeze_flags(wt, extra):
    packet = wt / "releases" / "v9.0"
    packet.mkdir(parents=True)
    (packet / "Summary of Changes v9.0.md").write_text("# Summary\n\nHand written.\n")
    r = _render(wt, *extra)
    assert r.returncode == 1
    assert "cannot be combined" in r.stderr
    assert not (packet / "Summary of Changes v9.0.pdf").exists()


def test_render_summary_renders_only_the_pdf(wt):
    packet = wt / "releases" / "v9.0"
    packet.mkdir(parents=True)
    (packet / "Summary of Changes v9.0.md").write_text(
        "# Summary of Changes\n\nThe voters will see one change: a comma.\n")
    (packet / "marker.txt").write_text("untouched")
    r = _render(wt)
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.name for p in packet.iterdir()) == [
        "Summary of Changes v9.0.md", "Summary of Changes v9.0.pdf", "marker.txt"]
    assert (packet / "marker.txt").read_text() == "untouched"
