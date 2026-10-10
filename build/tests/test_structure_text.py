"""Plain-words names for headings and raw-Typst blocks, and which of them
changed. The redline's in-text notes and the disclosure page both use these, so
the two say the same thing."""
import subprocess
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import czc_diff  # noqa: E402
import structure_text as st  # noqa: E402

REPO = BUILD.parent
ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"


def _text(ref, rel):
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{rel}"],
                          capture_output=True, text=True, check=True).stdout


def _blocks(text):
    return czc_diff.split_markdown(text)[2]


def test_the_four_article_3_tables_are_named_by_their_captions():
    caps = [st.block_caption(b) for b in _blocks(_text("v1.0", ART3))]
    assert len(caps) == 4
    assert [c.split()[1] for c in caps] == ["3.4", "3.5", "3.2", "3.3"]
    assert all(c.startswith("TABLE ") for c in caps)
    assert "TABLE 3.2 SIGHT DISTANCE" in caps


def test_a_block_with_no_caption_is_untitled():
    assert st.block_caption("```{=typst}\n// only a comment\n#line()\n```") == st.UNTITLED


def test_heading_labels():
    assert st.heading_label("## 5. AMUSEMENT, OUTDOOR") == "5. AMUSEMENT, OUTDOOR"
    assert st.heading_label("### a. DEFINITION {#def}") == "a. DEFINITION"


def test_labels_never_carry_a_split_marker_token():
    """split-article-03.py finds its markers by substring: a note carrying the
    token would split Article 3 at the wrong place and still exit 0."""
    for raw in ("## TYPE-PAGES note", "```{=typst}\nTABLE 9.1 STREET-TYPE-EXHIBITS\n```"):
        label = st.heading_label(raw) if raw.startswith("#") else st.block_caption(raw)
        assert "TYPE-PAGES" not in label and "STREET-TYPE-EXHIBITS" not in label


def test_v1_0_against_itself_changes_nothing_and_sees_every_heading():
    text = _text("v1.0", ART7)
    assert all(v == [] for v in czc_diff.structural_changes(text, text).values())
    assert len(czc_diff.split_markdown(text)[1]) > 100          # the control: headings were read


def test_a_retitled_heading_is_a_change_not_an_add_and_a_remove():
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    sc = czc_diff.structural_changes(old, new)
    assert sc["headings_changed"] == [("5. AMUSEMENT, OUTDOOR", "5. AMUSEMENT, OUTSIDE")]
    assert sc["headings_added"] == sc["headings_removed"] == []


def test_tables_added_removed_and_changed_are_named():
    old = _text("v1.0", ART3)
    blocks = _blocks(old)
    sight = next(b for b in blocks if "TABLE 3.2" in b)
    eng = next(b for b in blocks if "TABLE 3.5" in b)
    new = old.replace(sight, sight.replace("TABLE 3.2 SIGHT DISTANCE", "TABLE 3.2 SIGHT DISTANCE ", 1)
                      .replace("\n#", "\n// edited\n#", 1), 1)       # same caption, different content
    new = new.replace(eng, "", 1)                                   # removed
    new += "\n```{=typst}\n#block[\n  TABLE 3.9 NEW THING\n]\n```\n"  # added
    sc = czc_diff.structural_changes(old, new)
    assert sc["tables_changed"] == ["TABLE 3.2 SIGHT DISTANCE"]
    assert sc["tables_removed"] == [st.block_caption(eng)]
    assert sc["tables_added"] == ["TABLE 3.9 NEW THING"]


def test_a_new_article_lists_every_heading_as_added():
    new = _text("v1.0", ART7)
    sc = czc_diff.structural_changes(None, new)
    assert len(sc["headings_added"]) == len(czc_diff.split_markdown(new)[1])
