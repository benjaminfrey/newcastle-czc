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


def _code_lines(name):
    """The script's non-comment lines (whole-line `#` comments dropped)."""
    lines = (BUILD / name).read_text(encoding="utf-8").splitlines()
    return "\n".join(l for l in lines if not l.lstrip().startswith("#"))


def _gates(text):
    out = []
    for line in _block(text, "GATES").splitlines():
        m = re.match(r"\s*[-*]\s+`([^`]+)`\s+\S+\s+`([^`]+)`", line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def missing_gates(text, code=_code_lines):
    """Gates whose literal line is not in a non-comment line of the script named."""
    gates = _gates(text)
    assert gates, "the GATES block names no gate"
    for script, _ in gates:
        assert script in SCRIPTS, f"{script} is not one of {SCRIPTS}"
    return [(sc, st) for sc, st in gates if st not in code(sc)]


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
    doctored = _spec().replace("<!-- /GATES -->",
                               "- `build-adopted.sh` — `no such refusal anywhere` — x\n<!-- /GATES -->")
    assert missing_gates(doctored) == [("build-adopted.sh", "no such refusal anywhere")]


def test_gates_wrong_script_negative_control():
    real = "Refusing to freeze: source/ has uncommitted or untracked changes."
    assert real in _code_lines("build-adoption.sh")
    text = f"<!-- GATES -->\n- `build-release.sh` — `{real}` — x\n<!-- /GATES -->"
    assert missing_gates(text) == [("build-release.sh", real)]


def test_gates_ignore_comment_lines():
    text = "<!-- GATES -->\n- `build-adopted.sh` — `a comment only` — x\n<!-- /GATES -->"
    fake = lambda name: "\n".join(l for l in ["# a comment only", "echo hi"] if not l.startswith("#"))
    assert missing_gates(text, code=fake) == [("build-adopted.sh", "a comment only")]
