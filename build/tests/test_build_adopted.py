"""The adopted edition: same content as the voters saw, different chrome only."""
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))


@contextmanager
def _temp_tag(version):
    """A real, LOCAL git tag + the releases/<version>[-adopted] dirs it can
    produce, torn down afterward regardless of test outcome. Uses version
    numbers no real release would ever use, to make a leftover from a failed
    test run unmistakable rather than confusable with a real draft/adoption."""
    meeting_dir = REPO / "releases" / version
    adopted_dir = REPO / "releases" / f"{version}-adopted"
    assert not meeting_dir.exists(), f"{meeting_dir} already exists — leftover from a prior run?"
    assert not adopted_dir.exists(), f"{adopted_dir} already exists — leftover from a prior run?"
    subprocess.run(["git", "tag", version], cwd=REPO, check=True)
    try:
        yield meeting_dir, adopted_dir
    finally:
        subprocess.run(["git", "tag", "-d", version], cwd=REPO, capture_output=True)
        for d in (meeting_dir, adopted_dir):
            if d.exists():
                shutil.rmtree(d)


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


def test_residue_gate_checks_the_filename_too():
    """Page-text scanning alone cannot see the artifact's own filename (Task 8
    review, Important 1) — the gate must also flag chrome carried in a path."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "residue", REPO / "build" / "adopted_residue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    clean_text = "The Planning Board, or its designnee, drafts the official map."
    residue, damage = mod.check(clean_text, ["/tmp/x/Newcastle CZC (Adopted v1.0).pdf"])
    assert residue == []
    assert damage == []

    residue, _ = mod.check(clean_text, ["/tmp/x/Newcastle CZC (Integrated Draft v1.0).pdf"])
    assert residue != []


def test_refuses_and_leaves_no_release_dir_when_meeting_edition_is_missing():
    """The identity gate has nothing to compare against if the meeting edition
    was never built (or was pruned). This must refuse with a legible message
    naming the meeting edition — not a bare traceback — and, since the check
    happens before the (otherwise expensive) render, must leave no
    releases/<version>-adopted/ directory behind at all."""
    version = "v918.0"
    with _temp_tag(version) as (_meeting_dir, adopted_dir):
        r = subprocess.run(["bash", "build/build-adopted.sh", version, "March 1, 2099"],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode != 0
        assert "meeting edition" in (r.stdout + r.stderr).lower()
        assert not adopted_dir.exists(), (
            "a refused run (missing meeting edition) left a shipped-looking "
            "release directory behind")


def test_identity_gate_failure_leaves_no_release_dir():
    """A refused run must not leave a complete, shipped-looking
    releases/<version>-adopted/ directory behind (Task 8 review, Important 2)
    — checked here for a LATE failure, after the (real, rendered) adopted
    build has already run, to prove the scratch-then-place ordering actually
    holds and this isn't only true for the early/cheap refusal paths."""
    version = "v917.0"
    with _temp_tag(version) as (meeting_dir, adopted_dir):
        env = {**os.environ, "ADOPTION_MODE": "meeting", "ADOPTION_EVENT_DATE": "March 1, 2099"}
        r = subprocess.run(["bash", "build/build-full-czc.sh", version, "March 1, 2099"],
                           cwd=REPO, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr

        meeting_md = meeting_dir / f"Newcastle CZC (Integrated Draft {version}).md"
        assert meeting_md.exists(), r.stdout
        # Simulate the tagged source having diverged from the meeting edition on
        # disk -- exactly the case the identity gate exists to catch.
        with meeting_md.open("a", encoding="utf-8") as f:
            f.write("\nTAMPERED — this line was never voted on.\n")

        r2 = subprocess.run(["bash", "build/build-adopted.sh", version, "March 1, 2099"],
                            cwd=REPO, capture_output=True, text=True)
        assert r2.returncode != 0
        assert "differs" in (r2.stdout + r2.stderr).lower()
        assert not adopted_dir.exists(), (
            "a refused run (identity-gate failure, post-render) left a "
            "shipped-looking release directory behind")


def test_adopted_artifact_filenames_carry_no_draft_chrome():
    """The real regression for Important 1: build the adopted edition
    end-to-end and check the actual filenames it writes to disk, not just the
    gate's internal logic."""
    version = "v919.0"
    with _temp_tag(version) as (meeting_dir, adopted_dir):
        env = {**os.environ, "ADOPTION_MODE": "meeting", "ADOPTION_EVENT_DATE": "March 1, 2099"}
        r = subprocess.run(["bash", "build/build-full-czc.sh", version, "March 1, 2099"],
                           cwd=REPO, env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert (meeting_dir / f"Newcastle CZC (Integrated Draft {version}).md").exists()

        r2 = subprocess.run(["bash", "build/build-adopted.sh", version, "March 1, 2099"],
                            cwd=REPO, capture_output=True, text=True)
        assert r2.returncode == 0, r2.stderr
        assert adopted_dir.exists()
        names = [p.name for p in adopted_dir.iterdir()]
        assert names, "the adopted build produced no files"
        for n in names:
            assert "draft" not in n.lower(), f"draft chrome survived in filename: {n!r}"
