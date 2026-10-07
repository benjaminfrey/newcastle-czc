"""Artifact naming. THE FILENAME IS CHROME TOO -- build/adoption-name.sh's own
header says so, and build/adopted_residue.py checks filenames rather than only
page text. The standalone name was composed inline in build-standalone.sh,
before czc_standalone_name existed, with no mode component, so three
consumers disagreed about it."""
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NAME_SH = REPO / "build" / "adoption-name.sh"


def name(*args):
    """Call czc_standalone_name in a sourced shell; return (stdout, returncode)."""
    script = f'source "{NAME_SH}"; czc_standalone_name ' + " ".join(f'"{a}"' for a in args)
    r = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    return r.stdout, r.returncode


def test_draft_name_matches_the_shipped_v1_0_standalone():
    """Pins the draft form against a real published basename (releases/v1.0 tracks
    the .md). That file carries the draft name only because the mode component did
    not exist when it was written: build-adoption.sh built it in meeting mode but
    hard-codes the draft-form filename. It is a valid pin of the draft form, not
    evidence that the pipeline names meeting-mode output this way."""
    out, rc = name("draft", "3", "Thoroughfares", "v1.0")
    assert rc == 0
    assert out == "Article 3 Thoroughfares (Standalone v1.0)"
    shipped = REPO / "releases" / "v1.0" / f"{out}.md"
    assert shipped.exists(), (
        f"{shipped} is missing -- either the release layout changed or this name is "
        f"wrong; check which before editing the assertion")


def test_redline_form_differs_from_the_plain_form():
    plain, plain_rc = name("draft", "3", "Thoroughfares", "v1.1-draft")
    assert plain_rc == 0
    red, rc = name("draft", "3", "Thoroughfares", "v1.1-draft", "redline")
    assert rc == 0
    assert red != plain
    assert red == plain + " — Redline"


def test_each_mode_names_its_own_edition():
    draft, _ = name("draft", "3", "Thoroughfares", "v1.1-draft")
    meeting, _ = name("meeting", "3", "Thoroughfares", "v2.0")
    adopted, _ = name("adopted", "3", "Thoroughfares", "v2.0")
    assert len({draft, meeting, adopted}) == 3
    assert "Town Meeting Edition" in meeting
    assert "Adopted" in adopted


def test_unknown_mode_refuses():
    out, rc = name("bogus", "3", "Thoroughfares", "v1.1-draft")
    assert rc == 1
    assert out == ""
