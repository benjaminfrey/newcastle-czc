"""HTML comments in an article's markdown are STRUCTURE: build-standalone.sh and
build-full-czc.sh seat native-Typst units at them. A redline that marks one
corrupts the document's layout rather than its prose."""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REDLINE = REPO / "build" / "redline-text.py"
SPLITTER = REPO / "build" / "split-article-03.py"
MARKER = "<!-- TYPE-PAGES -->"

BODY_WITH = f"""---
article-number: 3
article-name: Thoroughfares
---

## 1. PURPOSE

This Article governs thoroughfares.

{MARKER}

## 2. TYPES

The ten Types follow.
"""
BODY_WITHOUT = BODY_WITH.replace(f"\n{MARKER}\n", "\n")


def mark(tmp_path, old_text, new_text):
    old = tmp_path / "old.md"; old.write_text(old_text)
    new = tmp_path / "new.md"; new.write_text(new_text)
    out = tmp_path / "out.md"
    r = subprocess.run([sys.executable, str(REDLINE), str(old), str(new), str(out),
                        "--source"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.read_text(), r.stderr


def split(tmp_path, marked_text):
    src = tmp_path / "marked.md"; src.write_text(marked_text)
    a, b, c = (tmp_path / n for n in ("a.md", "b.md", "c.md"))
    r = subprocess.run([sys.executable, str(SPLITTER), str(src), str(a), str(b), str(c)],
                       capture_output=True, text=True)
    return r.returncode, (a, b, c)


def test_a_deleted_marker_is_not_resurrected(tmp_path):
    """THE NEGATIVE CONTROL THAT MATTERS. The marker is gone from the new side,
    so the marked file must not contain it -- and must therefore not split. A
    test written against an 'exit 2' premise would pass against the real bug,
    which is that the split SUCCEEDS at a position the document does not have."""
    marked, _ = mark(tmp_path, BODY_WITH, BODY_WITHOUT)
    assert "~~<!--" not in marked, "the deleted marker was struck and resurrected"
    assert "TYPE-PAGES" not in marked, "the deleted marker survived into the marked file"
    rc, _ = split(tmp_path, marked)
    assert rc != 0, (
        "the marked file still split -- the plates would be seated where the new "
        "source has no marker")


def test_an_added_marker_survives_bare_and_splits(tmp_path):
    """An inserted marker was never fatal -- it survived as a Typst span and the
    splitter dropped the matched line, so the span never reached the page. It
    must now survive BARE, so the marked file is also a valid source."""
    marked, _ = mark(tmp_path, BODY_WITHOUT, BODY_WITH)
    # The pre-change output was `#text(fill: ...)[\<!-- TYPE-PAGES -->]`{=typst}:
    # it contained MARKER as a substring (the `<` is backslash-escaped), so a bare
    # `MARKER in marked` cannot fail. Require the marker to be its own bare line.
    assert f"\n{MARKER}\n" in marked, "the marker is not a bare line of its own"
    assert "#text" not in marked, "the marker is still wrapped in a Typst span"
    assert f"~~{MARKER}~~" not in marked
    rc, (a, b, c) = split(tmp_path, marked)
    assert rc == 0, "an added marker must still split"
    assert a.read_text().strip(), "segment a is empty"
    assert b.read_text().strip(), "segment b is empty"


def test_an_unchanged_marker_is_untouched(tmp_path):
    marked, _ = mark(tmp_path, BODY_WITH, BODY_WITH)
    assert MARKER in marked
    assert "~~" not in marked


def test_narrowness_prose_mentioning_the_token_is_still_marked(tmp_path):
    """Only a line that is WHOLLY an HTML comment is structure. Prose that
    happens to contain the token must still be redlined."""
    old = BODY_WITH.replace("This Article governs thoroughfares.",
                            "The TYPE-PAGES list is informative.")
    new = BODY_WITH.replace("This Article governs thoroughfares.",
                            "The TYPE-PAGES list is binding.")
    marked, _ = mark(tmp_path, old, new)
    assert "informative" in marked and "binding" in marked
    assert "~~" in marked, "a changed prose line mentioning the token was not marked"


def test_the_tally_does_not_count_structure(tmp_path):
    _, err_struct = mark(tmp_path, BODY_WITHOUT, BODY_WITH)
    assert "0 line(s) removed, 0 line(s) added" in err_struct, (
        f"inserting only a marker counted as a prose change: {err_struct}")


def test_the_integrated_build_refuses_a_missing_marker(tmp_path):
    """SECOND NEGATIVE CONTROL. build-standalone.sh exits 1 on a damaged marker;
    the integrated build appended the plates after the prose and shipped a
    document whose plates sit in the wrong place."""
    src = tmp_path / "src"
    subprocess.run(["cp", "-R", str(REPO / "source") + "/.", str(src) + "/"], check=True)
    prose = next(src.glob("article-03-*.md"))
    # The real source marker is `<!-- TYPE-PAGES: <long explanation> -->`, NOT the
    # bare MARKER used above, so replacing MARKER would be a silent no-op and the
    # build would (correctly) succeed. Damage the line that actually carries it.
    lines = prose.read_text().splitlines(keepends=True)
    hits = [i for i, ln in enumerate(lines) if "TYPE-PAGES" in ln]
    assert len(hits) == 1, f"expected exactly one TYPE-PAGES line in the source, got {hits}"
    lines[hits[0]] = "<!-- MARKER DAMAGED -->\n"
    prose.write_text("".join(lines))
    assert "TYPE-PAGES" not in prose.read_text(), "the fixture was not actually damaged"
    out = tmp_path / "out"
    r = subprocess.run(["bash", "build/build-full-czc.sh", "v0.97-draft", "October 7, 2026"],
                       cwd=REPO, capture_output=True, text=True,
                       env={**os.environ, "SRC_DIR": str(src), "OUT_DIR": str(out)})
    assert r.returncode != 0, (
        "the integrated build accepted a damaged split marker and appended the "
        "plates after the prose")
    assert "marker is missing or damaged" in r.stderr, r.stderr   # rc 2 -> the specific claim
    assert "exit 2" not in r.stderr


# Marker present on BOTH sides but at different positions, with prose now sitting
# where the old marker was. difflib pairs the removed marker with the new prose
# line as a 1:1 REPLACE, which is a different dispatch path from delete/insert.
OLD_MOVED = f"""---
article-number: 3
article-name: Thoroughfares
---

## 1. PURPOSE

{MARKER}

## 2. TYPES

The ten Types follow.
"""
NEW_MOVED = f"""---
article-number: 3
article-name: Thoroughfares
---

## 1. PURPOSE

The Types are shown below.

## 2. TYPES

The ten Types follow.

{MARKER}
"""


def test_the_fixture_really_is_a_one_to_one_replace():
    """Guards the next test's premise: if difflib stopped classifying this as a
    replace, test_a_moved_marker... would silently exercise the delete path."""
    spec = __import__("importlib.util").util.spec_from_file_location("rt", REDLINE)
    rt = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(rt)
    a = rt.prepare_source(rt.split_frontmatter(OLD_MOVED)[1])[0]
    b = rt.prepare_source(rt.split_frontmatter(NEW_MOVED)[1])[0]
    import difflib
    ops = difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    assert any(t == "replace" and (i2 - i1, j2 - j1) == (1, 1)
               and a[i1] == MARKER for t, i1, i2, j1, j2 in ops), ops


def test_a_moved_marker_is_not_word_diffed_into_a_false_split_point(tmp_path):
    """The replace path. The word-diffed pseudo-marker at the OLD position came
    first in the file, and split-article-03.py takes the FIRST substring hit, so
    it split there and exited 0 -- plates seated where the new source has no
    marker. The real marker is later, and must be the one that splits."""
    marked, _ = mark(tmp_path, OLD_MOVED, NEW_MOVED)
    assert marked.count("TYPE-PAGES") == 1, (
        f"expected only the real marker, got a second (word-diffed) one:\n{marked}")
    rc, (a, b, c) = split(tmp_path, marked)
    assert rc == 0
    assert "The Types are shown below." in a.read_text()
    assert "The ten Types follow." in a.read_text(), (
        "split at the false marker: Section 2 text landed after the split point")


def test_the_tally_agrees_with_the_output_for_a_moved_marker(tmp_path):
    """_markable excludes structure from the tally, so the output must not mark
    a marker either -- otherwise stderr says 0/0 while the file carries marks."""
    marked, err = mark(tmp_path, OLD_MOVED, NEW_MOVED)
    assert "~~<!--" not in marked and "\\<!--" not in marked
    assert "0 line(s) removed, 1 line(s) added" in err, err


def test_inline_comment_in_changed_prose_is_still_marked(tmp_path):
    """Guards against simplifying the predicate to `'<!--' in ln`."""
    old = BODY_WITH.replace("This Article governs thoroughfares.",
                            "Real prose is informative. <!-- note -->")
    new = BODY_WITH.replace("This Article governs thoroughfares.",
                            "Real prose is binding. <!-- note -->")
    marked, _ = mark(tmp_path, old, new)
    assert "informative" in marked and "binding" in marked
    assert "~~" in marked, "a changed prose line with a trailing comment was not marked"


def test_an_edited_marker_is_emitted_bare_and_the_tally_agrees(tmp_path):
    """An edited marker is a 1:1 replace too. It used to be word-diffed (a red
    span inside the comment) while the tally, which excludes structure, said 0/0."""
    edited = BODY_WITH.replace(MARKER, "<!-- TYPE-PAGES v2 -->")
    marked, err = mark(tmp_path, BODY_WITH, edited)
    assert "\n<!-- TYPE-PAGES v2 -->\n" in marked
    assert "~~" not in marked and "#text" not in marked
    assert "0 line(s) removed, 0 line(s) added" in err, err
