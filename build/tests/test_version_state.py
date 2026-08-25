"""Whole numbers are adopted law; decimals are drafts. Enforced, not assumed."""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "build"))

import version_state as vs  # noqa: E402


def test_parses_a_draft():
    v = vs.parse("v0.24-draft")
    assert (v.major, v.minor, v.is_draft) == (0, 24, True)


def test_parses_an_adoption_version():
    v = vs.parse("v1.0")
    assert (v.major, v.minor, v.is_draft) == (1, 0, False)


def test_adoption_version_must_be_whole():
    assert vs.is_adoption_version("v1.0") is True
    assert vs.is_adoption_version("v2.0") is True
    assert vs.is_adoption_version("v1.1") is False
    assert vs.is_adoption_version("v0.24-draft") is False
    assert vs.is_adoption_version("v1.0-draft") is False


def test_baseline_tag_is_not_an_adoption_version():
    """v0.1-baseline is a transcription of the previously adopted code, not an
    adoption produced by this tool."""
    assert vs.is_adoption_version("v0.1-baseline") is False


def test_cli_refuses_a_decimal_for_adoption():
    r = subprocess.run([sys.executable, "build/version_state.py",
                        "--require", "adoption", "v1.1-draft"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
    assert "whole" in (r.stdout + r.stderr).lower()


def test_cli_refuses_a_whole_number_for_a_draft():
    r = subprocess.run([sys.executable, "build/version_state.py",
                        "--require", "draft", "v1.0"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0


# --- Parsing must fail CLOSED ------------------------------------------------
# `--require draft` used to accept anything it could not parse: is_adoption_version()
# swallowed the ValueError and returned False, and the draft branch only refused on
# True. So `--require draft vX.Y.Z-frozen` exited 0, silently, on the one command
# whose job is to refuse. The --require adoption direction never had the hole.

MALFORMED = ("v1", "1.0", "v0.24-frozen", "draft", "", "v0.24-draft-test",
             "v0.24-draft-test-standalone-draft", "v1.0-test-standalone-meeting")


def test_cli_refuses_a_malformed_version_for_a_draft():
    for bad in MALFORMED:
        r = subprocess.run([sys.executable, "build/version_state.py",
                            "--require", "draft", bad],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode != 0, f"--require draft accepted malformed {bad!r}"
        assert (r.stdout + r.stderr).strip(), f"refused {bad!r} with no message"


def test_cli_refuses_a_malformed_version_for_an_adoption():
    for bad in MALFORMED:
        r = subprocess.run([sys.executable, "build/version_state.py",
                            "--require", "adoption", bad],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode != 0, f"--require adoption accepted malformed {bad!r}"


def test_cli_still_accepts_the_real_release_versions():
    """The gate must not have been tightened into refusing what it exists to
    allow. v0.2.1-draft and v0.4.1..v0.4.5-draft are REAL shipped tags in this
    repo, so the three-component form has to keep parsing."""
    for good in ("v0.24-draft", "v0.1-baseline", "v0.4.1-draft", "v0.2.1-draft"):
        r = subprocess.run([sys.executable, "build/version_state.py",
                            "--require", "draft", good],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode == 0, f"{good!r} was refused: {r.stderr}"
    for good in ("v1.0", "v2.0"):
        r = subprocess.run([sys.executable, "build/version_state.py",
                            "--require", "adoption", good],
                           cwd=REPO, capture_output=True, text=True)
        assert r.returncode == 0, f"{good!r} was refused: {r.stderr}"


def test_a_patch_version_is_never_an_adoption_version():
    """v1.0.0 parses (the repo has three-component tags) but is not adopted
    law: a whole number means exactly vN.0."""
    assert vs.is_adoption_version("v1.0.0") is False
    r = subprocess.run([sys.executable, "build/version_state.py",
                        "--require", "adoption", "v1.0.0"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode != 0
