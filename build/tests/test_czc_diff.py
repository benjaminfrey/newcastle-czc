"""build/czc_diff.py -- the substantive-change determination.

Every count asserted here comes from two REAL tags, or from a tree materialised
from the v1.0 tag and then edited. None pins the live working tree: it will
diverge from v1.0 the first time a real amendment is drafted.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import czc_diff  # noqa: E402
import manifest  # noqa: E402
import section_fixtures as fx  # noqa: E402

REPO = BUILD.parent
A2 = "article-02-data.json"
INV = "exhibits/street-types/inventory.json"
USE_COLS = ("use_col1", "use_col2")
# The calibrated positive control: commit 13b2a50 changed exactly this cell.
D3_CELL = ("D3 / NEIGHBORHOOD BUSINESS", "use_col2", "COMMERCIAL GOODS", "entries",
           "Retail & Service, General")
RIGHT_CHANGED = {"D2 / NEIGHBORHOOD RESIDENTIAL", "D3 / NEIGHBORHOOD BUSINESS",
                 "D4 / VILLAGE RESIDENTIAL", "D5 / VILLAGE BUSINESS", "D6 / TOWN CENTER",
                 "SD / HISTORIC", "SD / HIGHWAY COMMERCIAL", "SD / RURAL HIGHWAY",
                 "SD / CAMPUS", "SD / MARINE", "SD / FABRICATION"}


def _show(ref: str, rel: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), "show", f"{ref}:source/{rel}"],
                          capture_output=True, check=True).stdout


def _decl(article: str, rel: str) -> dict:
    return next(d for d in manifest.load()[article]["data_sources"] if d["path"] == rel)


def _cells(leaves: dict) -> dict:
    return {k: v for k, v in leaves.items()
            if len(k) == 5 and k[1] in USE_COLS and k[3] == "entries"}


# --- Article 2: the false zero that shipped ------------------------------------

def test_the_one_use_cell_that_changed_into_v1_0_is_found():
    """v0.24-draft -> v1.0 changed exactly one use cell. The text-only
    breakdown reported Article 2 at zero across that release; this comparator
    must find the cell, and the eleven districts' standards changes beside it."""
    old = czc_diff.json_leaves(_show("v0.24-draft", A2), _decl("2", A2))
    new = czc_diff.json_leaves(_show("v1.0", A2), _decl("2", A2))
    d = czc_diff.diff_maps(old, new)
    use_changes = {k: v for k, v in d.changed.items() if k[1] in USE_COLS}
    assert use_changes == {D3_CELL: ("rc", "rc sp")}
    assert not [k for k in [*d.added, *d.removed] if k[1] in USE_COLS]
    touched = {k[0] for k in [*d.changed, *d.added, *d.removed]}
    assert touched == RIGHT_CHANGED
    assert d.count() > 1


def test_v1_0_against_itself_reads_every_cell_and_finds_nothing():
    """'Nothing changed' alone proves nothing; the positive control is that all
    819 use cells were actually read."""
    leaves = czc_diff.json_leaves(_show("v1.0", A2), _decl("2", A2))
    assert len(_cells(leaves)) == 819
    assert czc_diff.diff_maps(leaves, dict(leaves)).count() == 0


def test_the_manifest_keys_article_2_by_code_and_name():
    assert _decl("2", A2)["key"] == "[].code+name"


def test_keying_article_2_by_code_alone_is_refused():
    """Seven districts are 'SD'. A code-only key would merge them into one record."""
    data = json.loads(_show("v1.0", A2))
    with pytest.raises(czc_diff.Refusal, match="not unique"):
        czc_diff.keyed_records(data, "[].code")
    assert len(czc_diff.keyed_records(data, "[].code+name")) == 13


def test_an_unknown_key_form_is_refused():
    with pytest.raises(czc_diff.Refusal, match="unknown key form"):
        czc_diff.keyed_records([], "records{}.id")


# --- Article 3's inventory: D7 ---------------------------------------------------

def test_inventory_type_changes_count_and_derived_fields_do_not():
    """v0.24-draft -> v1.0 re-typed ten segments R2 -> R3, and changed the
    DERIVED present_use on eleven. Only the ten are substance (decision D7)."""
    d = czc_diff.diff_maps(czc_diff.json_leaves(_show("v0.24-draft", INV), _decl("3", INV)),
                           czc_diff.json_leaves(_show("v1.0", INV), _decl("3", INV)))
    assert len(d.changed) == 10 and not d.added and not d.removed
    assert all(k[-1] == "type" and v == ("R2", "R3") for k, v in d.changed.items())


def test_schema_growth_counts_only_substantive_fields():
    """addresses first appears at v0.24-draft, on all 214 segments. It is
    derived, so it must not count. The positive control: with the field filter
    removed, the same comparison DOES see it -- so the filter is what hides it."""
    decl = _decl("3", INV)
    old, new = _show("v0.23-draft", INV), _show("v0.24-draft", INV)
    d = czc_diff.diff_maps(czc_diff.json_leaves(old, decl), czc_diff.json_leaves(new, decl))
    assert not [k for k in [*d.changed, *d.added, *d.removed] if "addresses" in k]
    unfiltered = {k: v for k, v in decl.items() if k != "substantive_fields"}
    d_all = czc_diff.diff_maps(czc_diff.json_leaves(old, unfiltered),
                               czc_diff.json_leaves(new, unfiltered))
    assert [k for k in d_all.added if "addresses" in k]


# --- The flattener ------------------------------------------------------------

def test_a_row_inserted_at_the_top_does_not_cascade():
    """Labelled rows are keyed by label, so inserting one is one addition, not
    a change to every row below it."""
    old = {"r": {"t": [["A", "1"], ["B", "2"]]}}
    new = {"r": {"t": [["Z", "0"], ["A", "1"], ["B", "2"]]}}
    d = czc_diff.diff_maps(czc_diff.flatten(old), czc_diff.flatten(new))
    assert (len(d.changed), len(d.added), len(d.removed)) == (0, 1, 0)


def test_a_repeated_title_is_kept_apart():
    """D1's right side has two panels titled DESIGN STANDARDS."""
    leaves = czc_diff.flatten([{"title": "X", "body": "a"}, {"title": "X", "body": "b"}])
    assert leaves == {("X", "body"): "a", ("X [2]", "body"): "b"}


def test_an_unlabelled_list_falls_back_to_position():
    assert czc_diff.flatten({"p": ["one", "two"]}) == {("p", "[0]"): "one", ("p", "[1]"): "two"}


def test_an_absent_file_counts_every_leaf():
    """An Article's data file added (or deleted) is every leaf added (or removed)."""
    new = czc_diff.json_leaves(_show("v1.0", A2), _decl("2", A2))
    assert czc_diff.json_leaves(None, _decl("2", A2)) == {}
    d = czc_diff.diff_maps({}, new)
    assert len(d.added) == len(new) > 819 and not d.changed and not d.removed


def test_invalid_json_is_refused():
    with pytest.raises(czc_diff.Refusal, match="not valid JSON"):
        czc_diff.json_leaves(b"{", _decl("2", A2))


# --- Refusals: every way a real change could read as zero -----------------------

def test_a_path_collision_is_refused():
    with pytest.raises(czc_diff.Refusal, match="share the path"):
        czc_diff.flatten([{"title": "X", "b": 1}, {"title": "X", "b": 2},
                          {"title": "X [2]", "b": 3}])


def test_a_misspelt_substantive_field_is_refused():
    decl = dict(_decl("3", INV), substantive_fields=["typ"])
    with pytest.raises(czc_diff.Refusal, match="no record has"):
        czc_diff.json_leaves(_show("v1.0", INV), decl)


def test_substantive_fields_as_a_string_is_refused():
    decl = dict(_decl("3", INV), substantive_fields="type")
    with pytest.raises(czc_diff.Refusal, match="must be a list"):
        czc_diff.json_leaves(_show("v1.0", INV), decl)


def test_a_change_of_type_is_a_change():
    assert czc_diff.diff_maps({("a",): 1}, {("a",): True}).count() == 1
    assert czc_diff.diff_maps({("a",): 1}, {("a",): 1.0}).count() == 1
    assert czc_diff.diff_maps({("a",): ""}, {("a",): None}).count() == 1
    assert czc_diff.diff_maps({("a",): 1}, {("a",): 1}).count() == 0


def test_a_duplicate_json_key_is_refused():
    decl = {"path": "x.json", "key": "$top-level-keys-except-_meta"}
    with pytest.raises(czc_diff.Refusal, match="duplicate key"):
        czc_diff.json_leaves(b'{"S1": {"a": 1}, "S1": {"a": 2}}', decl)


def test_a_declaration_without_a_key_is_refused():
    with pytest.raises(czc_diff.Refusal, match="has no key"):
        czc_diff.json_leaves(b"{}", {"path": "x.json"})


def test_keyed_records_refusal_paths():
    with pytest.raises(czc_diff.Refusal, match="needs a JSON object"):
        czc_diff.keyed_records([], "$top-level-keys-except-_meta")
    with pytest.raises(czc_diff.Refusal, match="needs a list of records"):
        czc_diff.keyed_records({"a": 1}, "[].x")
    with pytest.raises(czc_diff.Refusal, match="has no x"):
        czc_diff.keyed_records([{"y": 1}], "[].x")


# --- The markdown counts --------------------------------------------------------

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402
import section_map  # noqa: E402

ART3 = "article-03-streets-roads-driveways.md"
ART7 = "article-07-use-standards.md"
IDENTITY = adoption_map.AdoptionMap(baseline_version="v1.0",
                                    article_numbers={n: n for n in range(1, 10)},
                                    files={}, not_text_comparable={})
FM8 = '---\narticle-number: "8"\n---\n'


def _text(ref: str, rel: str) -> str:
    return _show(ref, rel).decode()


def _zero(counts: dict) -> bool:
    return counts == {"prose": 0, "heading": 0, "table": 0, "suppressed": 0}


def test_a_blank_line_is_not_a_change():
    """changed_line_count sees a blank line as a change; the determination must
    not. The positive control is the old counter seeing it."""
    old = _text("v1.0", ART7)
    new = old.replace("\n\n", "\n\n\n", 1)
    assert nz.changed_line_count(old, new, amap=IDENTITY) == 1
    assert _zero(czc_diff.markdown_counts(old, new))


def test_a_changed_prose_line_counts_twice():
    old = _text("v1.0", ART7)
    new = old.replace("ADULT ESTABLISHMENT\n\n", "ADULT ESTABLISHMENT\n\nAmended.\n\n", 1)
    assert new != old
    assert czc_diff.markdown_counts(old, new)["prose"] == 1          # one line added
    new2 = new.replace("Amended.", "Amended again.")
    assert czc_diff.markdown_counts(new, new2)["prose"] == 2         # one line out, one in


def test_an_edit_inside_a_raw_typst_table_counts_as_table_not_prose():
    """The redline renders a raw-Typst table unmarked, so this count is the only
    place the edit shows. It must still be SUBSTANTIVE (Task 3)."""
    old = _text("v1.0", ART3)
    new = old.replace("TABLE 3.2 SIGHT DISTANCE", "TABLE 3.2 SIGHT DISTANCES", 1)
    assert new != old
    assert czc_diff.markdown_counts(old, new) == {"prose": 0, "heading": 0, "table": 2,
                                                  "suppressed": 0}


def test_a_retitled_heading_counts_as_heading():
    old = _text("v1.0", ART7)
    new = old.replace("## 5. AMUSEMENT, OUTDOOR", "## 5. AMUSEMENT, OUTSIDE", 1)
    assert new != old
    assert czc_diff.markdown_counts(old, new) == {"prose": 0, "heading": 2, "table": 0,
                                                  "suppressed": 0}


def test_comments_and_frontmatter_are_not_changes():
    old = _text("v1.0", ART3)
    new = old.replace("<!-- The former TABLE 3.1a", "<!-- The retired TABLE 3.1a", 1)
    new = new.replace('article-number: "3"', 'article-number: "3"\nnote: "x"', 1)
    assert new != old
    assert _zero(czc_diff.markdown_counts(old, new))
    # Positive control: the same wording edit made OUTSIDE a comment counts.
    first = next(ln for ln in czc_diff.split_markdown(old)[0])
    outside = old.replace(first, first + " amended", 1)
    assert czc_diff.markdown_counts(old, outside)["prose"] == 2


def test_renaming_an_article_is_a_heading_change():
    old = _text("v1.0", ART3)
    new = old.replace('article-name: "Thoroughfares"', 'article-name: "Streets and Roads"', 1)
    assert new != old
    counts = czc_diff.markdown_counts(old, new)
    assert counts["heading"] == 2 and counts["prose"] == 0


def test_the_footer_date_is_not_a_change():
    old = _text("v1.0", ART3)
    new = old.replace('footer-date: "Draft v0.2-draft"',
                      'footer-date: "Adopted: September 14, 2026"', 1)
    assert new != old
    assert _zero(czc_diff.markdown_counts(old, new))


def test_unclosed_frontmatter_swallows_nothing():
    prose, _, _ = czc_diff.split_markdown(
        '---\narticle-number: "7"\n\nReal prose.\n\n---\n\nMore prose.\n')
    assert "Real prose." in prose and "More prose." in prose


def test_a_deleted_article_counts_every_line_removed():
    old = _text("v1.0", ART7)
    prose, headings, _ = czc_diff.split_markdown(old)
    counts = czc_diff.markdown_counts(old, "")
    assert counts["prose"] == len(prose) > 100
    assert counts["heading"] == len(headings)


def test_a_renumbered_reference_into_another_article_is_renumber_only():
    """Article 8 refers to Article 7 Section 4; a section is inserted into
    Article 7, so the reference becomes Section 5. Not a change in Article 8's
    substance -- with the map."""
    old, new = FM8 + "See Article 7 Section 4.\n", FM8 + "See Article 7 Section 5.\n"
    with_map = czc_diff.markdown_counts(old, new, smap={7: {4: 5}})
    assert with_map == {"prose": 0, "heading": 0, "table": 0, "suppressed": 1}
    assert czc_diff.markdown_counts(old, new)["prose"] == 2          # the control


def test_a_retargeted_reference_is_always_substantive():
    """Decision D8. Old §4 became §5; a reference that now says §6 points at
    different content."""
    old, new = FM8 + "See Article 7 Section 4.\n", FM8 + "See Article 7 Section 6.\n"
    assert czc_diff.markdown_counts(old, new, smap={7: {4: 5}})["prose"] == 2


def test_a_new_article_counts_every_line():
    new = _text("v1.0", ART7)
    counts = czc_diff.markdown_counts(None, new)
    prose, headings, blocks = czc_diff.split_markdown(new)
    assert counts["prose"] == len(prose) > 100
    assert counts["heading"] == len(headings) == 190     # 66 sections and their lettered sub-sections, + article-name and article-number


def test_a_section_inserted_into_article_7_is_one_heading_and_one_line(tmp_path):
    """With the derived map, inserting a section is exactly the inserted heading
    and its sentence; the 64 renumbered headings are suppressed. Without the
    map, every shifted heading counts -- the control."""
    tree = fx.copy_source(tmp_path / "src")
    p = tree / ART7
    p.write_text(fx.insert_section(p.read_text(), 3, "AGRICULTURE", "Farming is permitted."))
    smap = {int(a): {int(o): n for o, n in m.items()}
            for a, m in section_map.derive("v1.0", tree)["articles"].items()}
    old, new = _text("v1.0", ART7), p.read_text()
    assert czc_diff.markdown_counts(old, new, smap=smap) == {
        "prose": 1, "heading": 1, "table": 0, "suppressed": 64}
    assert czc_diff.markdown_counts(old, new)["heading"] > 100


# --- The determination -----------------------------------------------------------

CLI = [sys.executable, str(BUILD / "czc_diff.py")]


@pytest.fixture(scope="module")
def base_tree(tmp_path_factory):
    """ALL of source/ at v1.0, materialised once and copied per test."""
    return fx.copy_full_source(tmp_path_factory.mktemp("v1") / "source")


@pytest.fixture(scope="module")
def v1():
    return czc_diff.Side(ref="v1.0")


@pytest.fixture
def tree(tmp_path, base_tree):
    return Path(shutil.copytree(base_tree, tmp_path / "source"))


def _edit_json(tree, rel, fn, indent=2):
    p = tree / rel
    data = json.loads(p.read_text())
    fn(data)
    p.write_text(json.dumps(data, indent=indent, ensure_ascii=False) + "\n")


def _flip_d3(data):
    rec = next(r for r in data if (r["code"], r["name"]) == ("D3", "NEIGHBORHOOD BUSINESS"))
    cat = next(c for c in rec["use_col2"] if c["title"] == "COMMERCIAL GOODS")
    entry = next(e for e in cat["entries"] if e[0] == "Retail & Service, General")
    assert entry[1] == "rc sp"
    entry[1] = "rc"


def _others_unchanged(result, *except_):
    return all(c.verdict == "UNCHANGED" for n, c in result.items() if n not in except_)


def test_two_real_tags():
    """v0.24-draft -> v1.0, against v1.0 -> v1.0 in the same test: the second
    alone would pass with no code at all."""
    r = czc_diff.determine(czc_diff.Side(ref="v0.24-draft"), czc_diff.Side(ref="v1.0"))
    a2, a3 = r[2], r[3]
    assert a2.verdict == "SUBSTANTIVE" and a2.prose == 0 and a2.data > 1
    assert a2.data_detail[A2].changed[D3_CELL] == ("rc", "rc sp")
    assert any(n.startswith("article-02.typ:") for n in a2.needs_call)
    assert (a3.prose, a3.heading, a3.table, a3.data) == (2, 0, 0, 10)
    assert a3.verdict == "SUBSTANTIVE"
    assert {n.split(":")[0] for n in a3.needs_call} == {"street-type-inventory.typ",
                                                         "street-type-map.typ"}
    assert _others_unchanged(r, 2, 3)
    same = czc_diff.determine(czc_diff.Side(ref="v1.0"), czc_diff.Side(ref="v1.0"))
    assert _others_unchanged(same) and not any(c.needs_call for c in same.values())


def test_flipping_one_use_status_reports_exactly_that_cell(tree, v1):
    """The negative control the spec names: one status flipped, one cell reported."""
    _edit_json(tree, A2, _flip_d3)
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[2].data == 1
    assert r[2].data_detail[A2].changed == {D3_CELL: ("rc sp", "rc")}
    assert r[2].verdict == "SUBSTANTIVE" and _others_unchanged(r, 2)


def test_reformatting_a_data_file_is_not_a_change(tree, v1):
    _edit_json(tree, A2, lambda d: None, indent=4)
    assert (tree / A2).read_bytes() != _show("v1.0", A2)          # the bytes really differ
    assert _others_unchanged(czc_diff.determine(v1, czc_diff.Side(root=tree)))


def test_a_derived_inventory_field_is_not_substance(tree, v1):
    def change(d):
        seg = next(s for s in d["segments"] if s["id"] == "camp-road-1")
        seg["present_use"] = "Something else"
    _edit_json(tree, INV, change)
    assert _others_unchanged(czc_diff.determine(v1, czc_diff.Side(root=tree)))


def test_every_field_of_a_type_is_substance(tree, v1):
    """types.json declares no substantive_fields, so every leaf counts."""
    _edit_json(tree, "exhibits/cross-sections/types.json",
               lambda d: d["S1"].__setitem__("name", "MAIN STREET, AMENDED"))
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].data == 1 and r[3].verdict == "SUBSTANTIVE" and not r[3].needs_call


def test_a_regenerated_figure_alone_needs_a_call(tree, v1):
    """S1.svg is generated from types.json. Changed while types.json did not is
    an anomaly -- or a change to its other input -- and a person decides."""
    (tree / "exhibits/cross-sections/S1.svg").write_text(
        (tree / "exhibits/cross-sections/S1.svg").read_text() + "<!-- x -->\n")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].verdict == "NEEDS-CALL"
    assert any("S1.svg" in n and "did not" in n for n in r[3].needs_call)


def test_a_figure_regenerated_with_its_source_is_counted_through_the_source(tree, v1):
    _edit_json(tree, "exhibits/cross-sections/types.json",
               lambda d: d["S1"].__setitem__("name", "MAIN STREET, AMENDED"))
    (tree / "exhibits/cross-sections/S1.svg").write_text(
        (tree / "exhibits/cross-sections/S1.svg").read_text() + "<!-- x -->\n")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].data == 1 and not r[3].needs_call


def test_a_binary_exhibit_needs_a_call(tree, v1):
    sprite = next(p for p in sorted((tree / "exhibits/cross-sections/sprites").rglob("*"))
                  if p.is_file() and p.name != "NOTICE.md")
    sprite.write_bytes(sprite.read_bytes() + b"\0")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].verdict == "NEEDS-CALL"
    assert any("changed (binary)" in n for n in r[3].needs_call)


def test_a_layout_unit_change_needs_a_call(tree, v1):
    """Ruling 5: the use-table legend lives in article-02.typ, so a changed
    layout unit is never silently zero."""
    (tree / "article-02.typ").write_text((tree / "article-02.typ").read_text() + "\n// x\n")
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[2].verdict == "NEEDS-CALL" and _others_unchanged(r, 2)


def test_an_edited_raw_table_is_substantive_though_the_redline_shows_no_mark(tree, v1):
    p = tree / ART3
    p.write_text(p.read_text().replace("TABLE 3.2 SIGHT DISTANCE", "TABLE 3.2 SIGHT DISTANCES", 1))
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert (r[3].prose, r[3].table) == (0, 2) and r[3].verdict == "SUBSTANTIVE"


def test_an_ignored_file_is_not_a_change(tree, v1):
    p = tree / "exhibits/street-types/inventory-sample.json"
    p.write_text(p.read_text() + "\n")
    assert _others_unchanged(czc_diff.determine(v1, czc_diff.Side(root=tree)))


# --- Refusals: never guess -----------------------------------------------------

def test_an_unclaimed_changed_file_is_refused(tree, v1):
    (tree / "exhibits/new-thing.json").write_text("{}\n")
    with pytest.raises(czc_diff.Refusal, match="exhibits/new-thing.json"):
        czc_diff.determine(v1, czc_diff.Side(root=tree))


def test_a_changed_shared_file_is_refused(tree, v1):
    """Ruled by Ben Frey, 2026-10-09."""
    doc = copy.deepcopy(manifest.load())
    doc["shared"] = [A2]
    _edit_json(tree, A2, _flip_d3)
    with pytest.raises(czc_diff.Refusal, match="shared"):
        czc_diff.determine(v1, czc_diff.Side(root=tree), doc=doc)


def test_unwiring_article_2s_data_is_refused_not_reported_as_zero(tree, v1):
    """The spec's second control. 'Article 2 reports zero' is the failure that
    already shipped; without the data_sources wiring the file is unclaimed and
    the determination refuses instead."""
    doc = copy.deepcopy(manifest.load())
    doc["2"]["data_sources"] = []
    _edit_json(tree, A2, _flip_d3)
    with pytest.raises(czc_diff.Refusal, match="no Article claims"):
        czc_diff.determine(v1, czc_diff.Side(root=tree), doc=doc)


def test_the_old_code_only_key_is_refused(tree, v1):
    doc = copy.deepcopy(manifest.load())
    doc["2"]["data_sources"][0]["key"] = "[].code"
    _edit_json(tree, A2, _flip_d3)
    with pytest.raises(czc_diff.Refusal, match="not unique"):
        czc_diff.determine(v1, czc_diff.Side(root=tree), doc=doc)


def test_broken_json_is_refused(tree, v1):
    (tree / INV).write_text("{")
    with pytest.raises(czc_diff.Refusal, match="not valid JSON"):
        czc_diff.determine(v1, czc_diff.Side(root=tree))


def test_a_bad_ref_is_refused():
    with pytest.raises(czc_diff.Refusal, match="not a commit"):
        czc_diff.Side(ref="no-such-ref-xyz")


# --- The CLI --------------------------------------------------------------------

def _cli(*args):
    return subprocess.run([*CLI, *args], capture_output=True, text=True, cwd=REPO)


def test_the_cli_reports_and_writes_json(tmp_path):
    out = tmp_path / "d.json"
    r = _cli("--old", "v0.24-draft", "--new-ref", "v1.0", "--json", str(out))
    assert r.returncode == 0, r.stderr
    doc = json.loads(out.read_text())
    assert doc["articles"]["2"]["verdict"] == "SUBSTANTIVE"
    assert {"path": czc_diff.leaf_label(D3_CELL), "old": "rc", "new": "rc sp"} in \
        doc["articles"]["2"]["data_detail"][A2]["changed"]
    assert sorted(doc["articles"], key=int) == [str(n) for n in range(1, 10)]


def test_the_cli_refuses_with_exit_1_and_writes_nothing(tmp_path):
    out = tmp_path / "d.json"
    r = _cli("--old", "no-such-ref-xyz", "--new-ref", "v1.0", "--json", str(out))
    assert r.returncode == 1 and "refusing" in r.stderr and not out.exists()


def test_a_section_map_with_a_ref_new_side_is_refused(tmp_path):
    m = tmp_path / "m.json"
    m.write_text("{}")
    r = _cli("--old", "v1.0", "--new-ref", "v1.0", "--section-map", str(m))
    assert r.returncode == 1 and "--new-dir" in r.stderr


def test_a_section_inserted_into_article_7_end_to_end(tree, tmp_path):
    p = tree / ART7
    p.write_text(fx.insert_section(p.read_text(), 3, "AGRICULTURE", "Farming is permitted."))
    m = tmp_path / "map.json"
    d = subprocess.run([sys.executable, str(BUILD / "section_map.py"), "derive", "v1.0",
                        "--new-dir", str(tree), "--out", str(m)],
                       capture_output=True, text=True, cwd=REPO)
    assert d.returncode == 0, d.stderr
    out = tmp_path / "d.json"
    r = _cli("--old", "v1.0", "--new-dir", str(tree), "--section-map", str(m), "--json", str(out))
    assert r.returncode == 0, r.stderr
    a = json.loads(out.read_text())["articles"]
    assert (a["7"]["prose"], a["7"]["heading"], a["7"]["suppressed"]) == (1, 1, 64)
    assert a["7"]["verdict"] == "SUBSTANTIVE"
    assert all(a[str(n)]["verdict"] == "UNCHANGED" for n in range(1, 10) if n != 7)


def test_the_live_tree_runs_and_ignores_git_ignored_junk():
    """The live source/ holds .DS_Store files and inventory.json.bak-* backups,
    which git ignores. They are not part of the Code and must not be refused as
    unclaimed. No count is pinned: the live tree moves."""
    r = _cli("--old", "v1.0")
    assert r.returncode == 0, r.stderr
    rows = [ln.split() for ln in r.stdout.splitlines()]
    assert [row[0] for row in rows if row and row[0].isdigit()] == [str(n) for n in range(1, 10)]

# --- Fix round 1 ---------------------------------------------------------------

S1_SVG = "exhibits/cross-sections/S1.svg"
TYPES = "exhibits/cross-sections/types.json"


def _touch_svg(tree):
    (tree / S1_SVG).write_text((tree / S1_SVG).read_text() + "<!-- x -->\n")


def test_a_figure_beside_a_reindented_source_still_needs_a_call(tree, v1):
    """Re-indenting types.json changes its bytes and scores zero; it must not
    'explain' an edited figure."""
    _edit_json(tree, TYPES, lambda d: None, indent=4)
    _touch_svg(tree)
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].verdict == "NEEDS-CALL" and r[3].data == 0
    assert any("S1.svg" in n and "did not" in n for n in r[3].needs_call)


def test_a_figure_beside_a_meta_only_source_change_still_needs_a_call(tree, v1):
    _edit_json(tree, TYPES, lambda d: d["_meta"].__setitem__("note", "reworded"))
    _touch_svg(tree)
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[3].verdict == "NEEDS-CALL" and r[3].data == 0
    assert any("S1.svg" in n and "did not" in n for n in r[3].needs_call)


def test_prose_for_an_article_not_in_the_manifest_is_refused(tree, v1):
    (tree / "article-00-x.md").write_text("Some text.\n")
    with pytest.raises(czc_diff.Refusal, match="Article 0"):
        czc_diff.determine(v1, czc_diff.Side(root=tree))


def test_a_non_ascii_file_name_is_seen_and_refused(tree, v1):
    (tree / "exhibits/café.json").write_text("{}\n")
    with pytest.raises(czc_diff.Refusal, match="exhibits/café.json"):
        czc_diff.determine(v1, czc_diff.Side(root=tree))


def test_an_article_outside_the_manifest_is_refused_by_the_cli():
    r = _cli("--old", "v1.0", "--new-ref", "v1.0", "--article", "12")
    assert r.returncode == 1 and "Article 12 is not in build/article-manifest.json" in r.stderr


def test_a_refusal_leaves_no_stale_json(tmp_path):
    out = tmp_path / "d.json"
    out.write_text('{"old": "stale"}')
    r = _cli("--old", "no-such-ref-xyz", "--new-ref", "v1.0", "--json", str(out))
    assert r.returncode == 1 and not out.exists()


def test_a_deleted_prose_file_counts_every_old_line(tree, v1):
    (tree / ART7).unlink()
    prose, _, _ = czc_diff.split_markdown(_text("v1.0", ART7))
    r = czc_diff.determine(v1, czc_diff.Side(root=tree))
    assert r[7].verdict == "SUBSTANTIVE" and r[7].prose == len(prose)


def test_article_flag_does_not_narrow_a_refusal(tree):
    (tree / "exhibits/new-thing.json").write_text("{}\n")
    r = _cli("--old", "v1.0", "--new-dir", str(tree), "--article", "7")
    assert r.returncode == 1 and "exhibits/new-thing.json" in r.stderr
