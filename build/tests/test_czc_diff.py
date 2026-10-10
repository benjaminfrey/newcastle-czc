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
