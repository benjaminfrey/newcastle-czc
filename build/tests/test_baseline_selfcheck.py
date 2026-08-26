"""The adoption-map rollover self-check.

The invariant: the baseline compared against ITSELF must mark zero lines.

These tests build maps pointed at the real v1.0 tag, so they need it to exist.
They skip rather than fail when it does not -- before the first adoption there
is nothing to roll over to, which is the honest state, not a broken suite.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))

import adoption_map  # noqa: E402
import baseline_selfcheck as bsc  # noqa: E402

ADOPTION_TAG = "v1.0"


def _tag_exists(tag: str) -> bool:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", f"{tag}^{{commit}}"],
                          capture_output=True).returncode == 0


requires_tag = pytest.mark.skipif(
    not _tag_exists(ADOPTION_TAG),
    reason=f"{ADOPTION_TAG} does not exist yet; nothing to roll over to")


def _rolled_over_map(tmp_path, **overrides) -> str:
    """A correctly reset map pointed at the adoption tag, plus any breakage."""
    md = [f.split("/")[-1] for f in subprocess.run(
        ["git", "-C", str(REPO), "ls-tree", "--name-only", f"{ADOPTION_TAG}^{{commit}}", "source/"],
        capture_output=True, text=True).stdout.split() if f.endswith(".md")]
    doc = {
        "_README": "test fixture",
        "baseline_version": ADOPTION_TAG,
        "article_numbers": {str(i): i for i in range(1, 10)},
        "files": {f: f for f in md},
        "new_at_this_adoption": [],
        "not_text_comparable": {},
    }
    doc.update(overrides)
    p = tmp_path / "map.json"
    p.write_text(json.dumps(doc, indent=1))
    return str(p)


# --- dormant until it matters ------------------------------------------------

def test_skipped_while_the_baseline_is_not_an_adoption_version():
    """The shipped map points at v0.1-baseline, the 2020 Code in its own
    formatting conventions. Normalising that legitimately changes it, so a
    self-comparison there is meaningless -- and this must stay inert today."""
    assert bsc.run(None) == 0


def test_the_shipped_map_is_not_an_adoption_baseline():
    """Pins the premise of the test above; if the shipped baseline ever becomes
    a whole number, the check goes live and this test should be revisited."""
    import version_state
    amap = adoption_map.load()
    assert not version_state.is_adoption_version(amap.baseline_version)


# --- the invariant holds on a correct rollover -------------------------------

@requires_tag
def test_a_correctly_rolled_over_map_passes(tmp_path):
    assert bsc.problems(adoption_map.load(_rolled_over_map(tmp_path))) == []


@requires_tag
def test_a_correctly_rolled_over_map_exits_zero(tmp_path):
    assert bsc.run(_rolled_over_map(tmp_path)) == 0


# --- each silent failure mode is caught --------------------------------------

@requires_tag
def test_stale_article_numbers_are_caught(tmp_path):
    """The dangerous one. Measured 2026-08-25: this reports 308 phantom lines
    across the eight comparable articles and used to exit 0."""
    m = _rolled_over_map(tmp_path, article_numbers={
        "1": 1, "2": 2, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9})
    found = bsc.problems(adoption_map.load(m))
    assert found, "stale renumbering produced no complaint"
    assert any("phantom" in p for p in found)
    assert bsc.run(m) == 1


@requires_tag
def test_a_file_still_marked_new_is_caught(tmp_path):
    md = json.loads(Path(_rolled_over_map(tmp_path)).read_text())["files"]
    victim = "article-03-streets-roads-driveways.md"
    assert victim in md
    m = _rolled_over_map(tmp_path, files={**md, victim: None})
    found = bsc.problems(adoption_map.load(m))
    assert any("still marked new" in p for p in found)
    assert bsc.run(m) == 1


@requires_tag
def test_a_stale_not_text_comparable_entry_is_caught(tmp_path):
    m = _rolled_over_map(
        tmp_path, not_text_comparable={"article-02-prefatory.md": "stale"})
    found = bsc.problems(adoption_map.load(m))
    assert any("not_text_comparable" in p for p in found)
    assert bsc.run(m) == 1


@requires_tag
def test_a_stale_file_map_is_caught(tmp_path):
    """This half already failed loudly in adoption_breakdown.py; the self-check
    should agree rather than let it through on a different code path."""
    md = json.loads(Path(_rolled_over_map(tmp_path)).read_text())["files"]
    m = _rolled_over_map(tmp_path, files={
        **md, "article-04-site-standards.md": "article-03-site-standards.md"})
    found = bsc.problems(adoption_map.load(m))
    assert any("does not exist at" in p for p in found)
    assert bsc.run(m) == 1


# --- the freeze refuses on a stale map ---------------------------------------

@requires_tag
def test_build_adoption_runs_the_check():
    """Wiring, not behaviour: the precondition must actually be invoked, or the
    module is a test-only ornament."""
    src = (REPO / "build" / "build-adoption.sh").read_text()
    assert "baseline_selfcheck.py" in src
    assert "|| exit 1" in src.split("baseline_selfcheck.py")[1][:40]
