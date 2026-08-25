"""The adopted edition: same content as the voters saw, different chrome only."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))


def test_refuses_a_decimal_version():
    r = subprocess.run(["bash", "build/build-adopted.sh", "v1.1-draft", "March 15, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0


def test_refuses_when_the_meeting_edition_tag_does_not_exist():
    r = subprocess.run(["bash", "build/build-adopted.sh", "v9.0", "March 15, 2027"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "tag" in (r.stdout + r.stderr).lower()


def test_residue_gate_targets_chrome_not_the_word_draft():
    """The Code's own text says 'the Planning Board ... drafts the official map'.
    A gate that fails on that would be deleted the first time it fired."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "residue", REPO / "build" / "adopted_residue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    ok_text = "The Planning Board, or its designnee, drafts the official map."
    assert mod.find_residue(ok_text) == []

    bad = "INTEGRATED DRAFT — NOT ADOPTED"
    assert mod.find_residue(bad) != []

    bad2 = "Draft v1.0"
    assert mod.find_residue(bad2) != []
