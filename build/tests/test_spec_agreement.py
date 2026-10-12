"""ADOPTION-SPEC.md must keep describing the machinery (Wave 4b, ruling 9).

Two agreements, each with a negative control that feeds the same comparison a
doctored text -- the real spec is never edited by a test:
  * the packet list in section 3.3 names exactly release_plan.ARTIFACT_KINDS;
  * every gate section 6.1 names appears by name in build-adoption.sh,
    build-release.sh or build-adopted.sh.
"""
import re
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import release_plan  # noqa: E402

SPEC = BUILD / "ADOPTION-SPEC.md"
SCRIPTS = ("build-adoption.sh", "build-release.sh", "build-adopted.sh")


def _block(text, tag):
    m = re.search(rf"<!-- {tag} -->(.*?)<!-- /{tag} -->", text, re.S)
    assert m, f"spec has no <!-- {tag} --> block"
    return m.group(1)


def _names(text, tag):
    """The first backticked token of every bullet in the marked block."""
    out = []
    for line in _block(text, tag).splitlines():
        m = re.match(r"\s*[-*]\s+`([^`]+)`", line)
        if m:
            out.append(m.group(1))
    return out


def packet_disagreement(text):
    listed, real = set(_names(text, "PACKET-KINDS")), set(release_plan.ARTIFACT_KINDS)
    return sorted(listed ^ real)


def missing_gates(text, scripts=None):
    if scripts is None:
        scripts = "\n".join((BUILD / n).read_text(encoding="utf-8") for n in SCRIPTS)
    names = _names(text, "GATES")
    assert names, "the GATES block names no gate"
    return [n for n in names if n not in scripts]


def _spec():
    return SPEC.read_text(encoding="utf-8")


def test_packet_list_matches_release_plan():
    assert packet_disagreement(_spec()) == []


def test_packet_list_negative_control():
    doctored = _spec().replace("<!-- /PACKET-KINDS -->", "- `bogus-kind`\n<!-- /PACKET-KINDS -->")
    assert packet_disagreement(doctored) == ["bogus-kind"]
    dropped = re.sub(r"- `summary`[^\n]*\n", "", _spec(), count=1)
    assert packet_disagreement(dropped) == ["summary"]


def test_gates_are_reachable_from_the_scripts():
    assert missing_gates(_spec()) == []


def test_gates_negative_control():
    doctored = _spec().replace("<!-- /GATES -->", "- `no_such_gate.py`\n<!-- /GATES -->")
    assert missing_gates(doctored) == ["no_such_gate.py"]
