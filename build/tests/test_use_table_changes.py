"""build/use_table_changes.py -- the Use Table Changes document.

Article 2's thirteen district pages are rendered from data; the redline shows
them unmarked. This document is the only place their changes are listed item
by item. Counts come from real tags or from trees materialised from v1.0.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import use_table_changes as utc  # noqa: E402

REPO = BUILD.parent
TYP = "article-02.typ"


def _typ(ref: str = "v1.0") -> str:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{TYP}"],
                          capture_output=True, text=True, check=True).stdout


def test_the_legend_is_read():
    leg = utc.parse_legend(_typ())
    assert leg["rows"] == {
        "u": ("Use Permit Required", "CEO"),
        "rc": ("Residential Companion Permit Required", "CEO"),
        "sp": ("Special Permit Required", "Planning Board"),
        "ex": ("Expanded Use Permit Required", "Planning Board"),
    }
    assert leg["glyphs"] == {"u": "●", "rc": "❶", "sp": "❷", "ex": "✪"}
    assert leg["note"] == "Note: Uses without u, rc, sp, or ex are not allowed in this District"


def test_this_reader_agrees_with_the_permit_review_apps():
    """Two readers of one legend block (ruling 12). This test is the only thing
    that keeps them together: never skip or xfail it."""
    sys.path.insert(0, str(REPO / "build" / "permit-review"))
    from ruleset_build.legend import parse_legend as app_parse_legend
    text = _typ()
    ours, app = utc.parse_legend(text), app_parse_legend(text)
    app_rows = {r["code"]: r for r in app if r["code"]}
    assert set(ours["rows"]) == set(app_rows) == {"u", "rc", "sp", "ex"}
    for code, (label, authority) in ours["rows"].items():
        assert label == app_rows[code]["permit"] + " Required"
        assert authority == app_rows[code]["authority"]
        assert ours["glyphs"][code] == app_rows[code]["glyph"]
    app_note = next(r["note"] for r in app if not r["code"])
    assert ours["note"].removeprefix("Note: ").rstrip(".") == app_note.rstrip(".")


def test_an_unchanged_legend_has_no_delta_and_a_changed_one_does():
    old = utc.parse_legend(_typ())
    assert utc.legend_delta(old, utc.parse_legend(_typ())) == []
    new = utc.parse_legend(_typ().replace("[Special Permit Required], [Planning Board]",
                                          "[Special Exception Required], [Board of Appeals]", 1))
    delta = utc.legend_delta(old, new)
    assert any("Special Exception Required" in s for s in delta)
    assert any("Board of Appeals" in s for s in delta)


def test_a_missing_legend_is_refused():
    with pytest.raises(utc.LegendError):
        utc.parse_legend("#let x = 1\n")


def test_status_words():
    leg = utc.parse_legend(_typ())
    assert utc.status_words("", leg) == "Not allowed"
    assert utc.status_words("rc sp", leg) == \
        "Residential Companion Permit (CEO) + Special Permit (Planning Board)"
    assert utc.status_words("zz", leg) == "`zz` (not in the legend)"


# --- fix round 1: a legend change is never silent -------------------------------

ROW_U = 'status("u"), [Use Permit Required], [CEO],'
NOTE_END = 'are not allowed in this District]'


def _rewrapped(text: str, note: bool = True) -> str:
    """Every run of spaces inside the legend rows (and the Note, if asked) becomes
    a newline plus indentation: the same legend, laid out differently."""
    head = text.index("USE TABLE LEGEND")
    end = text.index(NOTE_END) + len(NOTE_END)
    seg = "\n".join(re.sub(r"(?<=\S) +(?=\S)", "\n          ", ln)
                    if (("Note:" in ln and note) or ("Note:" not in ln and 'status("' in ln)) else ln
                    for ln in text[head:end].split("\n"))
    return text[:head] + seg + text[end:]


def _delta_or_refusal(old_text: str, new_text: str) -> list[str]:
    """A change must surface either as a non-empty delta or as a refusal."""
    try:
        new = utc.parse_legend(new_text)
    except utc.LegendError as e:
        return [f"refused: {e}"]
    return utc.legend_delta(utc.parse_legend(old_text), new)


def test_a_fifth_row_in_another_form_is_never_silent():
    text = _typ()
    ex_row = 'status("ex"), [Expanded Use Permit Required], [Planning Board],'
    assert ex_row in text
    edited = text.replace(ex_row, ex_row + '\n        status("zz"), [Zoning Permit Required], [CEO]', 1)
    edited = edited.replace('ex: "✪")', 'ex: "✪", zz: "◆")', 1)
    assert edited != text
    assert _delta_or_refusal(text, edited)


def test_a_clause_added_to_the_note_is_reported():
    text = _typ()
    assert NOTE_END in text
    edited = text.replace(NOTE_END, NOTE_END[:-1] + " except as provided in Section 3]", 1)
    delta = utc.legend_delta(utc.parse_legend(text), utc.parse_legend(edited))
    assert delta and any("except as provided in Section 3" in s for s in delta)


def test_a_rewrap_is_not_a_change():
    text = _typ()
    wrapped = _rewrapped(text)
    assert wrapped != text and "\n          " in wrapped
    old, new = utc.parse_legend(text), utc.parse_legend(wrapped)
    assert utc.legend_delta(old, new) == []
    assert not utc.legend_block_changed(old, new)
    # the agreement test, again, on rewrapped rows. (The app's Note regex needs
    # single spaces in "Uses without", so the Note is left unwrapped here: the app
    # refuses a rewrapped Note loudly, which is a difference but not a silent one.)
    rows_only = _rewrapped(text, note=False)
    assert rows_only != text
    sys.path.insert(0, str(REPO / "build" / "permit-review"))
    from ruleset_build.legend import parse_legend as app_parse_legend
    app_rows = {r["code"]: r for r in app_parse_legend(rows_only) if r["code"]}
    assert utc.parse_legend(rows_only)["rows"] == new["rows"]
    assert set(new["rows"]) == set(app_rows)
    for code, (label, authority) in new["rows"].items():
        assert label == " ".join(app_rows[code]["permit"].split()) + " Required"
        assert authority == " ".join(app_rows[code]["authority"].split())


def test_glyphs_and_rows_must_name_the_same_codes():
    edited = _typ().replace(', ex: "✪"', "", 1)
    assert edited != _typ()
    with pytest.raises(utc.LegendError, match="ex"):
        utc.parse_legend(edited)


def test_a_duplicate_code_is_refused():
    text = _typ()
    dup = text.replace(ROW_U, ROW_U + "\n        " + ROW_U, 1)
    assert dup != text
    with pytest.raises(utc.LegendError, match="`u`"):
        utc.parse_legend(dup)


def test_added_removed_and_glyph_changes_are_itemised():
    old = utc.parse_legend(_typ())
    no_ex = _typ().replace(', ex: "✪"', "", 1)
    no_ex = re.sub(r'\n[ \t]*status\("ex"\)[^\n]*', "", no_ex, count=1)
    assert 'status("ex")' not in no_ex.split("USE TABLE LEGEND")[1].split("Note:")[0]
    gone = utc.parse_legend(no_ex)
    assert any("`ex` removed" in s for s in utc.legend_delta(old, gone))
    assert any("`ex` added" in s for s in utc.legend_delta(gone, old))
    glyph = utc.legend_delta(old, utc.parse_legend(_typ().replace('u: "●"', 'u: "○"', 1)))
    assert any("symbol for `u` changed" in s and "●" in s and "○" in s for s in glyph)


def test_an_unitemisable_change_falls_back_to_the_block():
    """A change in the legend table's layout that no field captures still surfaces."""
    text = _typ()
    old = utc.parse_legend(text)
    marker = "columns: (auto, 1fr, auto), stroke: none,"
    assert marker in text
    new = utc.parse_legend(text.replace(marker, "columns: (auto, 2fr, auto), stroke: none,", 1))
    assert old["block"] != new["block"]
    delta = utc.legend_delta(old, new)
    assert len(delta) == 1 and "cannot itemise" in delta[0]
    assert utc.legend_block_changed(old, new)


# --- The document ------------------------------------------------------------------

import czc_diff  # noqa: E402
import section_fixtures as fx  # noqa: E402

CLI = [sys.executable, str(BUILD / "use_table_changes.py")]
A2 = "article-02-data.json"


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


@pytest.fixture
def tree(tmp_path, base_tree):
    return Path(shutil.copytree(base_tree, tmp_path / "source"))


def _edit(tree, fn):
    p = tree / A2
    data = json.loads(p.read_text())
    fn(data)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _record(data, code, name):
    return next(r for r in data if (r["code"], r["name"]) == (code, name))


def _section(md: str, n: int) -> str:
    """The text of section `## n.` up to the next `## `."""
    start = md.index(f"## {n}. ")
    nxt = md.find("\n## ", start + 1)
    return md[start:nxt if nxt != -1 else len(md)]


def _run(*args):
    return subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=REPO)


def test_v0_24_to_v1_0_reports_the_one_cell_and_the_standards(tmp_path):
    """The calibrated positive control (ruling 10). The D3 cell is the only
    changed use; the eleven districts' standards changes are reported in their
    own section; the total equals the determination's Article 2 data count."""
    out = tmp_path / "u.md"
    r = _run("v0.24-draft", str(out), "--new-ref", "v1.0", "--json", str(tmp_path / "u.json"))
    assert r.returncode == 0, r.stderr
    md = out.read_text()
    uses = _section(md, 2)
    assert [ln for ln in uses.splitlines() if ln.startswith("- ")] == [
        "- **Retail & Service, General** (COMMERCIAL GOODS): Residential Companion Permit (CEO) "
        "→ Residential Companion Permit (CEO) + Special Permit (Planning Board)"]
    assert "No use was added or removed" in _section(md, 3)
    standards = _section(md, 5)
    for district in ("D2 NEIGHBORHOOD RESIDENTIAL", "SD MARINE", "SD FABRICATION"):
        assert district in standards
    assert "No change to the legend" in _section(md, 1)
    total = json.loads((tmp_path / "u.json").read_text())["total"]
    det = czc_diff.determine(czc_diff.Side(ref="v0.24-draft"), czc_diff.Side(ref="v1.0"))
    assert total == det[2].data > 1


def test_nothing_to_report_exits_2_and_writes_nothing(tmp_path):
    out = tmp_path / "u.md"
    r = _run("v1.0", str(out), "--new-ref", "v1.0")
    assert r.returncode == 2 and not out.exists()


def test_the_three_districts_without_a_matrix_are_named(tmp_path):
    out = tmp_path / "u.md"
    assert _run("v0.24-draft", str(out), "--new-ref", "v1.0").returncode == 0
    assert ("No Permitted Buildings matrix: SD CONSERVATION, SD CAMPUS, SD MARINE"
            in _section(out.read_text(), 4))


def test_a_legend_wording_change_alone_is_reported(tree, tmp_path):
    """The spec's negative control: all 819 cells untouched, only the legend's
    words changed. A cell-diff-only document reports nothing."""
    p = tree / TYP
    p.write_text(p.read_text().replace("[Special Permit Required]",
                                       "[Special Exception Required]", 1))
    out = tmp_path / "u.md"
    r = _run("v1.0", str(out), "--new-dir", str(tree), "--json", str(tmp_path / "u.json"))
    assert r.returncode == 0, r.stderr
    assert "Special Exception Required" in _section(out.read_text(), 1)
    assert json.loads((tmp_path / "u.json").read_text())["total"] == 0
    det = czc_diff.determine(czc_diff.Side(ref="v1.0"), czc_diff.Side(root=tree))
    assert det[2].verdict == "NEEDS-CALL"                            # and the determination flags it


def test_an_unitemisable_legend_change_shows_both_texts(tree, tmp_path):
    """A legend change no sentence can itemise still prints the before and after
    legend text, each in its own block."""
    p = tree / TYP
    text = p.read_text()
    assert ROW_U in text
    p.write_text(text.replace(ROW_U, ROW_U.replace("[CEO]", "[ CEO ]"), 1))
    assert utc.legend_block_changed(utc.parse_legend(text), utc.parse_legend(p.read_text()))
    out = tmp_path / "u.md"
    r = _run("v1.0", str(out), "--new-dir", str(tree))
    assert r.returncode == 0, r.stderr
    legend = _section(out.read_text(), 1)
    assert "cannot itemise" in legend
    assert "Before:" in legend and "After:" in legend
    assert legend.count("```") == 4
    assert "[ CEO ]" in legend.split("After:")[1]
    assert "[ CEO ]" not in legend.split("After:")[0]
    assert not any(g in out.read_text() for g in "●❶❷✪")           # ruling 11: no glyph, anywhere
    assert '#let glyphs' not in legend and 'status("' not in legend


def test_a_blank_status_is_written_not_allowed(tree, tmp_path):
    def change(d):
        rec = _record(d, "D1", "RURAL")
        entry = next(e for c in rec["use_col1"] + rec["use_col2"] for e in c["entries"]
                     if e[1] == "")
        entry[1] = "u"
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    assert "Not allowed → Use Permit (CEO)" in _section(out.read_text(), 2)


def test_the_soft_hyphen_category_prints_whole(tree, tmp_path):
    """D4's TRANSPORTATION & UTILITIES is split in the data at a soft hyphen;
    its cells sit under a category titled 'ITIES'. Print the word whole."""
    def change(d):
        cat = next(c for c in _record(d, "D4", "VILLAGE RESIDENTIAL")["use_col1"]
                   if c["title"] == "ITIES")
        cat["entries"][0][1] = "ex" if cat["entries"][0][1] != "ex" else "u"
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    uses = _section(out.read_text(), 2)
    assert "(TRANSPORTATION & UTILITIES)" in uses and "(ITIES)" not in uses
    assert "\xad" not in out.read_text()


def test_a_use_added_under_the_empty_half_prints_whole(tree, tmp_path):
    def change(d):
        cat = next(c for c in _record(d, "D4", "VILLAGE RESIDENTIAL")["use_col1"]
                   if c["title"].endswith("\xad"))
        cat["entries"].append(["Test Depot", "u"])
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    md = out.read_text()
    assert "(TRANSPORTATION & UTILITIES)" in _section(md, 3) and "UTIL)" not in md
    assert "\xad" not in md


def test_section_5_reads_plainly(tmp_path):
    out = tmp_path / "u.md"
    assert _run("v0.24-draft", str(out), "--new-ref", "v1.0").returncode == 0
    standards = _section(out.read_text(), 5)
    assert "New table: ROOF PITCH" in standards and "Gable added: “5/12 min”" in standards
    for leak in ("› body", "kind", "[0]", "entries"):
        assert leak not in standards


def test_an_added_use_is_an_event_distinct_from_a_change(tree, tmp_path):
    def change(d):
        cat = next(c for c in _record(d, "D1", "RURAL")["use_col1"] if c["title"] == "RECREATION")
        cat["entries"].append(["Farm Stand", "u"])
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    md = out.read_text()
    assert "Farm Stand" in _section(md, 3) and "Farm Stand" not in _section(md, 2)


def test_a_matrix_change_names_its_row_and_column(tree, tmp_path):
    def change(d):
        m = _record(d, "D3", "NEIGHBORHOOD BUSINESS")["matrix"]
        row = next(r for r in m["rows"] if r[0] == "Building Width")
        assert row[1] == "50 ft"                                      # the v1.0 value
        row[1] = "60 ft"
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    assert "- Building Width › Residential: “50 ft” → “60 ft”" in _section(out.read_text(), 4).splitlines()


def test_an_inserted_matrix_column_is_not_misattributed(tree, tmp_path):
    def change(d):
        m = _record(d, "D3", "NEIGHBORHOOD BUSINESS")["matrix"]
        m["cols"].insert(1, "Civic")
        for row in m["rows"]:
            row.insert(2, "x")
    _edit(tree, change)
    out = tmp_path / "u.md"
    assert _run("v1.0", str(out), "--new-dir", str(tree)).returncode == 0
    matrix = _section(out.read_text(), 4)
    assert "Building Width › Residential:" not in matrix
    assert "Column 2 heading" in matrix
    assert "headed “Mixed-Use” before, “Civic” now" in matrix


def test_the_document_renders_through_the_memo_builder(tmp_path):
    """The document is a memo, not an Article: build-memo.sh renders it."""
    import pymupdf
    md, pdf = tmp_path / "u.md", tmp_path / "u.pdf"
    assert _run("v0.24-draft", str(md), "--new-ref", "v1.0").returncode == 0
    r = subprocess.run(["bash", str(BUILD / "build-memo.sh"), str(md), str(pdf),
                        "Use Table Changes", "Newcastle Core Zoning Code"],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    text = "".join(page.get_text() for page in pymupdf.open(pdf))
    assert "Retail & Service, General" in text
