"""Tests for the render pipeline: render/findings_to_md.py's node renderer,
and an end-to-end proof that render/build-findings.sh + style/findings-
template.typ actually produce a PDF.

Run offline (uses a real pandoc/typst subprocess for the end-to-end tests —
skipped automatically if either binary is not on PATH):

    cd build/permit-review && python3 -m pytest tests/test_render.py -v
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from render import findings_to_md as f2m  # noqa: E402

HAVE_PANDOC = subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0
HAVE_TYPST = subprocess.run(["which", "typst"], capture_output=True).returncode == 0
HAVE_PDFINFO = subprocess.run(["which", "pdfinfo"], capture_output=True).returncode == 0
requires_toolchain = pytest.mark.skipif(
    not (HAVE_PANDOC and HAVE_TYPST),
    reason="pandoc and/or typst not on PATH",
)


# --------------------------------------------------------------------------- #
# Escaping — the load-bearing correctness property. Ordinance text and
# applicant-supplied strings can contain characters Typst treats as syntax;
# getting this wrong either breaks the build or silently changes the text.
# --------------------------------------------------------------------------- #


def test_typst_escape_escapes_every_special_character():
    # Backslash is covered separately below — it escapes by doubling, so the
    # generic "preceded by a backslash" check below doesn't apply to it.
    raw = "50% # setback [see] <note> @ref _emph_ *bold* $x$ `code`"
    escaped = f2m.typst_escape(raw)
    for ch in "#[]<>@_*$`":
        # Every occurrence of ch in escaped output must be preceded by a backslash.
        for i, c in enumerate(escaped):
            if c == ch:
                assert escaped[i - 1] == "\\", f"unescaped {ch!r} in {escaped!r}"


def test_typst_escape_handles_backslash_before_other_escapes():
    # A literal backslash must become \\ , not be consumed by a later escape.
    assert f2m.typst_escape("a\\b") == "a\\\\b"


def test_typst_escape_converts_newlines_to_typst_linebreaks():
    result = f2m.typst_escape("line one\nline two")
    assert "\\\n" in result
    assert "line one" in result and "line two" in result


def test_typst_escape_is_idempotent_on_plain_text():
    assert f2m.typst_escape("Newcastle Planning Board") == "Newcastle Planning Board"


def test_md_escape_escapes_markdown_syntax_characters():
    raw = "M&T *Bank* [Trust] (Est. 1900)"
    escaped = f2m.md_escape(raw)
    assert "\\*Bank\\*" in escaped
    assert "\\[Trust\\]" in escaped
    assert "\\(Est\\. 1900\\)" in escaped


# --------------------------------------------------------------------------- #
# Node -> markdown fragments: each type produces the expected raw_attribute
# block (or plain markdown), calling the matching template helper by name.
# --------------------------------------------------------------------------- #


def test_heading_node_produces_atx_markdown():
    md = f2m.node_to_md(f2m.heading("Findings of Fact", level=1))
    assert md.strip() == "# Findings of Fact"


def test_heading_level_is_clamped_to_1_through_4():
    assert f2m.node_to_md({"type": "heading", "level": 9, "text": "X"}).startswith("####")
    assert f2m.node_to_md({"type": "heading", "level": 0, "text": "X"}).startswith("# ")


def test_standard_node_calls_the_standard_helper():
    md = f2m.node_to_md(f2m.standard("Setback shall be 20 ft min."))
    assert "```{=typst}" in md
    assert "#standard[Setback shall be 20 ft min.]" in md
    assert "#provenance" not in md  # no citation supplied -> no call at all


def test_standard_node_with_citation_calls_provenance():
    md = f2m.node_to_md(f2m.standard("Setback shall be 20 ft min.", citation="Art. 2, D1"))
    assert '#provenance("Art. 2, D1")' in md


def test_standard_node_escapes_typst_special_characters_in_body():
    md = f2m.node_to_md(f2m.standard("Setback #1 [min] shall be 20 ft."))
    assert "#standard[Setback \\#1 \\[min\\] shall be 20 ft.]" in md


def test_finding_unresolved_boardq_call_their_named_helpers():
    assert "#finding[The proposed setback is 25 ft.]" in f2m.node_to_md(
        f2m.finding("The proposed setback is 25 ft.")
    )
    assert "#unresolved[TBD…]" in f2m.node_to_md(f2m.unresolved("TBD…"))
    assert "#boardq[Is this consistent with the plan?]" in f2m.node_to_md(
        f2m.boardq("Is this consistent with the plan?")
    )


def test_motionblock_node_emits_all_eight_fields_as_none_by_default():
    md = f2m.node_to_md(f2m.motionblock())
    assert "#motionblock(" in md
    for typst_name in ("motion", "moved-by", "second", "discussion", "yea", "nay", "abstain", "result"):
        assert f"{typst_name}: none" in md


def test_motionblock_node_rejects_unknown_fields():
    with pytest.raises(ValueError):
        f2m.motionblock(bogus_field="x")


def test_motionblock_node_passes_through_supplied_values():
    md = f2m.node_to_md(f2m.motionblock(moved_by="A. Member", yea="5"))
    assert 'moved-by: "A. Member"' in md
    assert 'yea: "5"' in md
    assert "motion: none" in md  # untouched fields stay blank


def test_conditions_node_empty_list_still_renders_a_call():
    md = f2m.node_to_md(f2m.conditions([]))
    assert "#conditions(())" in md


def test_conditions_node_with_items():
    md = f2m.node_to_md(f2m.conditions(["Item one.", "Item two."]))
    assert "#conditions((" in md
    assert "[Item one.]" in md
    assert "[Item two.]" in md


def test_signaturegrid_node_handles_dicts_and_plain_strings():
    md = f2m.node_to_md(
        f2m.signaturegrid([{"name": "A. Member", "title": "Chair"}, "B. Member"])
    )
    assert '(name: "A. Member", title: "Chair")' in md
    assert '"B. Member"' in md


def test_kv_node_renders_bold_labels_with_hard_breaks():
    md = f2m.node_to_md(f2m.kv([("Applicant", "Jane Doe")]))
    assert "**Applicant:** Jane Doe  " in md  # trailing 2 spaces = markdown <br>


def test_table_node_renders_a_pipe_table_with_header_separator():
    md = f2m.node_to_md(f2m.table(["A", "B"], [["1", "2"]]))
    lines = md.strip().splitlines()
    assert lines[0] == "| A | B |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| 1 | 2 |"


def test_raw_node_passes_typst_through_unescaped():
    md = f2m.node_to_md(f2m.raw("#v(4pt)"))
    assert "#v(4pt)" in md


def test_unknown_node_type_raises():
    with pytest.raises(ValueError):
        f2m.node_to_md({"type": "not-a-real-type"})


def test_render_nodes_joins_multiple_nodes():
    md = f2m.render_nodes([f2m.heading("Title", level=1), f2m.para("Body text.")])
    assert "# Title" in md
    assert "Body text." in md


# --------------------------------------------------------------------------- #
# The mechanism claim itself: prove pandoc's typst writer drops fenced-Div
# classes but preserves raw_attribute {=typst} blocks verbatim. This is the
# empirical justification documented in findings_to_md.py's module docstring
# — a regression here would mean the whole render pipeline stopped working
# for a reason that has nothing to do with our own code.
# --------------------------------------------------------------------------- #


@requires_toolchain
def test_pandoc_drops_fenced_div_classes_when_writing_typst():
    result = subprocess.run(
        ["pandoc", "--from=markdown+raw_attribute", "-t", "typst"],
        input="::: {.standard}\nHello\n:::\n",
        capture_output=True,
        text=True,
        check=True,
    )
    assert ".standard" not in result.stdout
    assert "#standard" not in result.stdout


@requires_toolchain
def test_pandoc_passes_raw_attribute_typst_blocks_through_verbatim():
    result = subprocess.run(
        ["pandoc", "--from=markdown+raw_attribute", "-t", "typst"],
        input='```{=typst}\n#standard[Hello]\n```\n',
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "#standard[Hello]"


# --------------------------------------------------------------------------- #
# End-to-end: findings_to_md.render_nodes() -> build-findings.sh -> a real,
# paginated PDF with a working running head / footer / DRAFT watermark.
# --------------------------------------------------------------------------- #


@requires_toolchain
def test_end_to_end_render_produces_a_pdf(tmp_path):
    nodes = [
        f2m.heading("Findings of Fact and Conclusions of Law", level=1),
        f2m.heading("Findings of Fact", level=1),
        f2m.standard("Primary Frontage Line Length (min) Required: 250 ft.", citation="Art. 2, D1"),
        f2m.finding("The proposed lot has 300 ft of frontage."),
        f2m.unresolved("Proposed setback: ______"),
        f2m.boardq("Does the Board find the record sufficient?"),
        f2m.heading("Decision of the Planning Board", level=1),
        f2m.motionblock(),
        f2m.conditions([]),
        f2m.signaturegrid([{"name": "Test Signer", "title": "Chair"}, "Test Signer Two"]),
    ]
    md_path = tmp_path / "test-findings.md"
    md_path.write_text(f2m.render_nodes(nodes), encoding="utf-8")

    exports_dir = APP_ROOT / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    out_path = exports_dir / "pytest-end-to-end-findings.pdf"
    script = APP_ROOT / "render" / "build-findings.sh"

    result = subprocess.run(
        ["bash", str(script), str(md_path), str(out_path),
         "January 15, 2026", "TEST — not a real case"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert out_path.exists()
    assert out_path.stat().st_size > 0

    if HAVE_PDFINFO:
        info = subprocess.run(["pdfinfo", str(out_path)], capture_output=True, text=True, check=True)
        match = re.search(r"^Pages:\s+(\d+)", info.stdout, re.MULTILINE)
        assert match is not None
        assert int(match.group(1)) >= 1

    out_path.unlink()  # data/ is scratch; leave no litter behind a test run


@requires_toolchain
def test_build_findings_refuses_to_write_outside_data_exports(tmp_path):
    md_path = tmp_path / "test-findings.md"
    md_path.write_text("# Hello\n", encoding="utf-8")
    escaped_out = tmp_path / "escaped.pdf"  # NOT under data/exports/
    script = APP_ROOT / "render" / "build-findings.sh"

    result = subprocess.run(
        ["bash", str(script), str(md_path), str(escaped_out)],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "data/exports" in result.stderr
    assert not escaped_out.exists()


@requires_toolchain
def test_draft_watermark_only_appears_when_requested(tmp_path):
    import os

    md_path = tmp_path / "draft-toggle.md"
    md_path.write_text(f2m.render_nodes([f2m.heading("Hi", level=1), f2m.para("Body.")]), encoding="utf-8")
    exports_dir = APP_ROOT / "data" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    on_path = exports_dir / "pytest-draft-on.pdf"
    off_path = exports_dir / "pytest-draft-off.pdf"
    script = APP_ROOT / "render" / "build-findings.sh"

    r_on = subprocess.run(
        ["bash", str(script), str(md_path), str(on_path)],
        capture_output=True, text=True, env={**os.environ, "DRAFT": "1"},
    )
    r_off = subprocess.run(
        ["bash", str(script), str(md_path), str(off_path)],
        capture_output=True, text=True, env={**os.environ, "DRAFT": "0"},
    )
    assert r_on.returncode == 0, r_on.stderr
    assert r_off.returncode == 0, r_off.stderr
    # A DRAFT watermark pushes the file size up noticeably (extra glyph
    # outlines/paint ops on every page); a page-count-only check wouldn't
    # catch a watermark silently failing to render.
    assert on_path.stat().st_size != off_path.stat().st_size

    on_path.unlink()
    off_path.unlink()
