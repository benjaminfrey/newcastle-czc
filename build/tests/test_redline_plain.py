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

NOTE = "<!-- unmarked: regenerated figure -->"


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


def test_the_figure_note_precedes_the_new_block_and_pandoc_keeps_it_a_block(tmp_path):
    text, _ = run_files(tmp_path, FIG_OLD, FIG_NEW, "--source", "--plain")
    assert NOTE + "\n```\nfigure version two\n```" in text
    if shutil.which("pandoc"):
        r = subprocess.run(["pandoc", "-f", "gfm", "-t", "native"], input=text,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "CodeBlock" in r.stdout and "figure version two" in r.stdout


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
