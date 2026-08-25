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
