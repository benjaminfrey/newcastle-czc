"""redline-text.py --source: a note in the text wherever a heading, table or
figure was added, removed or changed. Before this, a removed table or heading
left one empty line -- no trace, and a tally of 0/0."""
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
REPO = BUILD.parent
RT = BUILD / "redline-text.py"
ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"


def _text(ref, rel):
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{rel}"],
                          capture_output=True, text=True, check=True).stdout


def mark(tmp_path, old, new, *flags):
    o, n, out = tmp_path / "old.md", tmp_path / "new.md", tmp_path / "out.md"
    o.write_text(old)
    n.write_text(new)
    r = subprocess.run([sys.executable, str(RT), str(o), str(n), str(out), "--source", *flags],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    return out.read_text(), r.stderr


BOTH = pytest.mark.parametrize("flags", [(), ("--plain",)], ids=["pdf", "plain"])


def _sight(text):
    start = text.index("```{=typst}", text.index("b. To a point 4 ft above ground"))
    end = text.index("```\n", start + 10) + 4
    return text[start:end]


@BOTH
def test_a_deleted_table_leaves_a_note_in_both_modes(tmp_path, flags):
    old = _text("v1.0", ART3)
    new = old.replace(_sight(old), "", 1)
    out, err = mark(tmp_path, old, new, *flags)
    assert "*[Table or figure removed: “TABLE 3.2 SIGHT DISTANCE”]*" in out
    assert "1 structural change(s) noted" in err


@BOTH
def test_a_deleted_heading_leaves_a_note_in_both_modes(tmp_path, flags):
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR\n", "", 1)
    out, _ = mark(tmp_path, old, new, *flags)
    assert "*[Heading removed: “5. AMUSEMENT, OUTDOOR”]*" in out


@BOTH
def test_an_added_heading_stays_a_heading_and_gets_a_note(tmp_path, flags):
    old = _text("v1.0", ART7)
    new = old.replace("## 3. ADULT ESTABLISHMENT", "## 3. AGRICULTURE\n\nFarming.\n\n## 4. ADULT ESTABLISHMENT", 1)
    out, _ = mark(tmp_path, old, new, *flags)
    assert "\n## 3. AGRICULTURE\n\n*[Heading added]*\n" in out


@BOTH
def test_a_retitled_heading_says_what_it_read(tmp_path, flags):
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    out, _ = mark(tmp_path, old, new, *flags)
    assert "## 5. AMUSEMENT, OUTSIDE\n\n*[Heading changed — it read: “5. AMUSEMENT, OUTDOOR”]*" in out


@BOTH
def test_a_changed_table_is_noted_before_it_in_both_modes(tmp_path, flags):
    """The PDF path used to show a changed Table 3.2 exactly like an unchanged one."""
    old = _text("v1.0", ART3)
    sight = _sight(old)
    new = old.replace(sight, sight.replace("\n#", "\n// edited\n#", 1), 1)
    out, _ = mark(tmp_path, old, new, *flags)
    note = "*[Table or figure changed — shown in its current form, not marked: “TABLE 3.2 SIGHT DISTANCE”]*"
    assert note in out
    assert out.index(note) < out.index("TABLE 3.2 SIGHT DISTANCE", out.index(note) + len(note))


@BOTH
def test_a_new_table_is_noted(tmp_path, flags):
    old = _text("v1.0", ART3)
    new = old + "\n```{=typst}\n#block[\n  TABLE 3.9 NEW THING\n]\n```\n"
    out, _ = mark(tmp_path, old, new, *flags)
    assert "*[New table or figure, shown in full: “TABLE 3.9 NEW THING”]*" in out


@BOTH
def test_an_unchanged_article_carries_no_note(tmp_path, flags):
    old = _text("v1.0", ART3)
    out, err = mark(tmp_path, old, old, *flags)
    assert "*[" not in out                           # no structural note at all
    assert "0 structural change(s) noted" in err


def test_a_removed_split_marker_comment_stays_silent(tmp_path):
    """Ruling 5: whole-line comments are build structure, not Code text."""
    old = _text("v1.0", ART3)
    line = next(ln for ln in old.splitlines() if "The former TABLE 3.1a" in ln)
    out, err = mark(tmp_path, old, old.replace(line + "\n", "", 1))
    assert "*[" not in out
    assert "0 structural change(s) noted" in err


def test_the_legend_no_longer_says_a_removal_leaves_no_trace(tmp_path):
    old = _text("v1.0", ART7)
    out, _ = mark(tmp_path, old, old, "--plain")
    assert "leaves no trace" not in out
    assert "a note in italics and square brackets" in out
