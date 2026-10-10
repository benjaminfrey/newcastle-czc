"""--plain: the redline markdown a resident can read, and the only redline that
survives in the repository (releases/**/*.pdf is gitignored). Decision D1."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REDLINE = REPO / "build" / "redline-text.py"

OLD = """---
article-number: 7
article-name: Use Standards
---

## 1. PURPOSE

A farm stand is permitted in D1.

| Use | D1 | D2 |
|---|---|---|
| Farm stand | P | N |
"""
NEW = """---
article-number: 7
article-name: Use Standards
---

## 1. PURPOSE

A farm stand is permitted in D1 and D2.

| Use | D1 | D2 |
|---|---|---|
| Farm stand | P | P |
"""

# A plain (non-typst) fenced block, so that any `{=typst}` in the output can only
# be redline MARKUP and never the block's own content.
FIG_OLD = OLD + "\n```\nfigure version one\n```\n"
FIG_NEW = NEW + "\n```\nfigure version two\n```\n"

NOTE = "<!-- unmarked: new or regenerated figure -->"
VISIBLE = "*[figure new or regenerated \u2014 shown unmarked]*"
SIGIL = "\u2295"


def run_files(tmp_path, old, new, *flags):
    o = tmp_path / "old.md"; o.write_text(old)
    n = tmp_path / "new.md"; n.write_text(new)
    out = tmp_path / f"out{'-'.join(f.strip('-') for f in flags) or '-default'}.md"
    r = subprocess.run([sys.executable, str(REDLINE), str(o), str(n), str(out),
                        *flags], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return out.read_text(), r.stderr


def run(tmp_path, *flags):
    return run_files(tmp_path, OLD, NEW, *flags)


def assert_no_typst(text):
    assert "{=typst}" not in text
    assert "rgb(" not in text
    assert "#text(" not in text


def test_plain_emits_no_typst(tmp_path):
    text, _ = run(tmp_path, "--source", "--plain")
    assert_no_typst(text)


def test_plain_marks_additions_bold_and_deletions_struck(tmp_path):
    text, _ = run(tmp_path, "--source", "--plain")
    assert "**" in text, "no bold addition found"
    assert "~~" in text, "no struck deletion found"


def test_the_tally_is_identical_with_and_without_the_flag(tmp_path):
    """The flag changes RENDERING, never what counts as a change.

    This passes before the flag exists (the flag is ignored), so it is a guard
    and not a RED test -- the non-zero assertion stops it passing vacuously."""
    _, err_typst = run(tmp_path, "--source")
    _, err_plain = run(tmp_path, "--source", "--plain")
    assert err_typst == err_plain, f"{err_typst!r} != {err_plain!r}"
    assert re.search(r"[1-9]\d* line\(s\) removed, [1-9]\d* line\(s\) added", err_plain), err_plain


def test_the_tally_is_identical_in_every_mode(tmp_path):
    for mode in ("--source", "--full", "--digest"):
        _, a = run_files(tmp_path, FIG_OLD, FIG_NEW, mode)
        _, b = run_files(tmp_path, FIG_OLD, FIG_NEW, mode, "--plain")
        assert a == b, f"{mode}: {a!r} != {b!r}"


def test_plain_round_trips_through_pandoc_gfm(tmp_path):
    """pandoc must accept it AND see the marks: <strong> for additions, <del> for
    deletions. (rc==0 alone passes on Typst spans, which gfm reads as text.)"""
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not installed")
    text, _ = run(tmp_path, "--source", "--plain")
    src = tmp_path / "plain.md"; src.write_text(text)
    r = subprocess.run(["pandoc", "-f", "gfm", "-t", "html", str(src)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "<strong>" in r.stdout and "<del>" in r.stdout, r.stdout


def test_a_regenerated_figure_is_declared_unmarked(tmp_path):
    """A text diff cannot mark a regenerated figure. In plain mode the
    limitation must be visible in the text rather than inferred from its
    absence."""
    old = OLD + "\n```{=typst}\n#old_figure()\n```\n"
    new = NEW + "\n```{=typst}\n#new_figure()\n```\n"
    text, _ = run_files(tmp_path, old, new, "--source", "--plain")
    assert NOTE in text
    assert "#new_figure()" in text
    assert "#old_figure()" not in text


def pandoc_out(text, to):
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc not installed")
    r = subprocess.run(["pandoc", "-f", "gfm", "-t", to], input=text,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_the_figure_note_precedes_the_new_block_and_pandoc_keeps_it_a_block(tmp_path):
    text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, "--source", "--plain")
    # the comment stays a WHOLE LINE of its own (is_unmarkable_structure reads it),
    # the visible companion is a separate line, and the block follows
    # Wave 3b: a structural change now leaves a note (Ben, 2026-10-10)
    assert (NOTE + "\n\n*[New table or figure, shown in full: \u201can untitled table or figure\u201d]*"
            "\n\n```\nfigure version two\n```") in text
    assert "CodeBlock" in pandoc_out(text, "native")


def test_the_figure_disclosure_reaches_rendered_output(tmp_path):
    """The HTML comment renders as nothing, so on its own the disclosure would be
    the inference-from-absence it exists to prevent. The reader must SEE it."""
    for mode in ("--source", "--full"):
        text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, mode, "--plain")
        seen = pandoc_out(text, "plain")       # visible text only: comments are dropped
        # Wave 3b: --source now says it with the structural note (Ben, 2026-10-10); --full is unchanged
        if mode == "--source":
            assert "New table or figure, shown in full" in seen, (mode, seen)
        else:
            assert "figure new or regenerated" in seen and "shown unmarked" in seen, (mode, seen)
        assert "figure version two" in seen
        assert "<em>" in pandoc_out(text, "html") or "_[figure" in pandoc_out(text, "gfm")


def test_an_unchanged_figure_is_not_declared_unmarked(tmp_path):
    text, _ = run_files(tmp_path, FIG_NEW, FIG_NEW.replace("permitted in D1 and D2",
                                                          "permitted in D1 and D2 only"),
                        "--source", "--plain")
    assert NOTE not in text


def test_plain_full_mode_emits_no_typst_including_the_native_block_note(tmp_path):
    text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, "--full", "--plain")
    assert_no_typst(text)
    assert NOTE in text
    assert "native-Typst block added or updated" not in text, "the bolded sentence should be the comment"
    assert "figure version two" in text


def test_plain_digest_mode_emits_no_typst(tmp_path):
    """The digest builds its breadcrumbs, rules and summary line out of Typst."""
    text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, "--digest", "--plain")
    assert_no_typst(text)
    assert "PURPOSE" in text, "breadcrumb lost"
    assert "changed passage" in text, "summary lost"


def test_plain_digest_with_no_changes_emits_no_typst(tmp_path):
    text, _ = run_files(tmp_path, OLD, OLD, "--digest", "--plain")
    assert_no_typst(text)
    assert "No textual changes" in text


def test_without_the_flag_nothing_changes(tmp_path):
    """NEGATIVE CONTROL for the default path: the Typst form must still be the
    Typst form. Every existing call site passes no --plain. (Passes before the
    change by design.)"""
    text, _ = run(tmp_path, "--source")
    assert "{=typst}" in text, "the Typst path lost its spans"
    assert "rgb(" in text


def test_the_plain_note_survives_a_redline_of_a_redline(tmp_path):
    """The note is a whole-line HTML comment, which is structure: fed back in as
    OLD it must not be struck as prose or counted as a change."""
    plain, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, "--source", "--plain")
    text, err = run_files(tmp_path, plain, plain, "--source", "--plain")
    assert "0 line(s) removed, 0 line(s) added" in err, err
    assert "~~<!--" not in text


# --- whole-line insertions are distinguishable from the Code's own bold --------

TERMS_OLD = """---
article-number: 9
article-name: Definitions
---

## 1. DEFINITIONS

**Absolute Height:** The vertical distance.
"""
TERMS_NEW = TERMS_OLD + """
**Abandoned or Vacated:** A use that has stopped.

- **Added Item:** listed.
"""


def paragraphs(html):
    return [re.sub(r"\s+", " ", m).strip() for m in re.findall(r"<(?:p|li)>(.*?)</(?:p|li)>", html, re.S)]


def test_an_added_defined_term_is_distinguishable_from_an_unchanged_one_when_rendered(tmp_path):
    """The measurement that found the collision: the Code bolds every defined
    term, so a bold-only addition rendered like the unchanged term beside it.
    Compare what a reader SEES, not what the markdown contains."""
    for mode in ("--source", "--full"):
        text, _ = run_files(tmp_path, TERMS_OLD, TERMS_NEW, mode, "--plain")
        html = pandoc_out(text, "html")
        paras = paragraphs(html)
        unchanged = next(p for p in paras if "Absolute Height" in p)
        added = next(p for p in paras if "Abandoned or Vacated" in p)
        shape = lambda p: re.sub(r"Absolute Height|Abandoned or Vacated", "TERM", p)
        assert shape(added) != shape(unchanged), (mode, added, unchanged)
        visible = lambda p: re.sub(r"<[^>]+>", "", p)
        assert visible(added).startswith(SIGIL), (mode, added)
        assert not visible(unchanged).startswith(SIGIL)


def test_the_sigil_marks_whole_line_additions_of_every_kind(tmp_path):
    text, _ = run_files(tmp_path, TERMS_OLD, TERMS_NEW, "--source", "--plain")
    assert f"- {SIGIL} **" in text, "list item addition"
    text, _ = run_files(tmp_path, OLD, NEW.replace("| Farm stand | P | P |",
                                                   "| Farm stand | P | P |\n| Roadside stand | P | P |"),
                        "--source", "--plain")
    assert f"| {SIGIL} **Roadside stand** |" in text, text
    text, _ = run_files(tmp_path, OLD, NEW + "\n## 2. NEW SECTION\n", "--full", "--plain")
    assert f"## {SIGIL} **2. NEW SECTION**" in text, text


def test_inline_word_changes_keep_plain_bold_with_no_sigil(tmp_path):
    """Word-level changes inside an otherwise unchanged line stay **bold**: that
    case was already unambiguous and D1 settled it."""
    text, _ = run(tmp_path, "--source", "--plain")
    changed = next(l for l in text.splitlines() if "farm stand is permitted" in l.lower())
    assert "**D1 and D2.**" in changed and SIGIL not in changed, changed


LEGEND_MARK = "Redline key:"


def test_plain_output_carries_the_convention_legend_once(tmp_path):
    for mode in ("--source", "--full", "--digest"):
        text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, mode, "--plain")
        assert text.count(LEGEND_MARK) == 1, (mode, text[:300])
        legend = next(l for l in text.splitlines() if LEGEND_MARK in l)
        assert "**bold**" in legend and "~~struck~~" in legend and SIGIL in legend
        seen = pandoc_out(text, "plain")
        assert LEGEND_MARK in seen


def test_the_legend_follows_the_frontmatter_in_source_mode(tmp_path):
    """--source output is a document the build reads: YAML front-matter must stay first."""
    text, _ = run(tmp_path, "--source", "--plain")
    assert text.startswith("---\narticle-number: 7\n")
    assert text.index(LEGEND_MARK) > text.index("article-name: Use Standards\n---")


def test_without_the_flag_there_is_no_legend_and_no_sigil(tmp_path):
    for mode in ("--source", "--full", "--digest"):
        text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, mode)
        assert LEGEND_MARK not in text and SIGIL not in text and VISIBLE not in text


# -- the --source legend must claim only what --source keeps -------------------
#
# --source marks prose and table rows word by word. A heading or block that was
# added, removed or changed leaves an italic bracketed note at that spot instead
# (Wave 3b). Each test below pins the BEHAVIOUR the legend's limits clause describes, so the clause cannot go on
# being printed after the code stops keeping it (or the reverse).

SECTION_OLD = "# Article\n\n## 1. KEPT\n\nBody.\n\n## 2. REMOVED SECTION\n\n```\nold figure\n```\n"
SECTION_NEW = "# Article\n\n## 1. KEPT\n\nBody.\n\n## 3. ADDED SECTION\n\nBody.\n"


def test_the_source_legend_names_what_source_does_not_mark(tmp_path):
    text, _ = run_files(tmp_path, SECTION_OLD, SECTION_NEW, "--source", "--plain")
    legend = next(l for l in text.splitlines() if LEGEND_MARK in l)
    # Wave 3b: a structural change now leaves a note (Ben, 2026-10-10)
    assert "Only prose and the rows of simple tables are marked word by word" in legend
    assert "a note in italics and square brackets" in legend and "leaves no trace" not in legend
    assert "covers prose and table rows only" not in legend      # the old sentence read as a promise about tables
    assert "Summary of Changes" in legend
    assert "marks a line that is new in its entirety" in legend
    assert "at the start of a line" not in legend


def test_the_other_modes_do_not_carry_the_source_only_exclusions(tmp_path):
    # Wave 3b: a structural change now leaves a note (Ben, 2026-10-10)
    for mode in ("--source", "--full", "--digest"):
        text, _ = run_files(tmp_path, SECTION_OLD, SECTION_NEW, mode, "--plain")
        legend = next(l for l in text.splitlines() if LEGEND_MARK in l)
        assert "leaves no trace" not in legend, mode


def test_what_the_source_legend_admits_is_what_the_code_does(tmp_path):
    """The limits clause is TRUE: a removed heading and a removed block leave a
    note (not their text), and a heading carries no mark and no sigil."""
    text, _ = run_files(tmp_path, SECTION_OLD, SECTION_NEW, "--source", "--plain")
    # Wave 3b: a structural change now leaves a note (Ben, 2026-10-10)
    # the old heading text appears only inside a note; the removed block's rows are gone
    assert text.count("REMOVED SECTION") == 1 and "it read: \u201c2. REMOVED SECTION\u201d]*" in text
    assert "*[Table or figure removed: " in text, "a removed block left no note"
    assert "old figure" not in text, "the removed block's own text must not reappear"
    assert "\n## 3. ADDED SECTION\n\n*[Heading changed" in text, "the retitled heading lost its text or its note"
