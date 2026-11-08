"""Amendments flag the entries that cite what they changed (library plan 1, task 7)."""

import json
import shutil
from pathlib import Path

import pytest

from portal_api.library import is_live, load_library
from portal_api.library.changes import changed, flag, flagged, section_texts
from portal_api import ruleset
from portal_api.ruleset import PINNED_KEY

PINNED = Path(ruleset.__file__).parent / "rulesets" / PINNED_KEY


@pytest.fixture
def amended(tmp_path):
    """A copy of the pinned ruleset with 2.3.c.3's text changed, and 9.9.z.1 added."""
    out = tmp_path / "amended"
    shutil.copytree(PINNED, out)
    data = json.loads((out / "articles.json").read_text())
    node = next(n for n in data["nodes"] if n["id"] == f"{PINNED_KEY}:a2.s3.c.3")
    node["text"] += " As amended."
    data["nodes"].append({**node, "id": f"{PINNED_KEY}:a9.s9.z.1", "text": "New."})
    (out / "articles.json").write_text(json.dumps(data))
    return out


def test_section_texts_use_the_cite_form():
    texts = section_texts(PINNED)
    assert texts["1.1.a.1"] == "To implement the Comprehensive Plan of the Town of Newcastle."


def test_identical_rulesets_change_nothing():
    assert changed(section_texts(PINNED), section_texts(PINNED)) == frozenset()


def test_a_changed_subsection_flags_its_parent_cite(amended):
    c = changed(section_texts(PINNED), section_texts(amended))
    assert c == {"2.3.c.3", "9.9.z.1"}
    lib = load_library()
    assert ("setbacks", ("2.3.c.3",)) in flagged(lib, c)
    assert flagged(lib, frozenset({"2.3.c.3.a"}))[0][0] == "setbacks"   # a change under a cite counts


def test_flag_lists_only_entries_citing_changes(amended):
    c = changed(section_texts(PINNED), section_texts(amended))
    assert [i for i, _ in flagged(load_library(), c)] == ["setbacks"]


def test_apply_pulls_them(lib, amended):
    root = lib("guide", lambda d: None)
    assert flag(root, PINNED, amended, apply=True) == [["setbacks", ["2.3.c.3"]]]
    e = load_library(root).entries["setbacks"]
    assert (e.status, e.pulled_by, e.pulled_why) == ("pulled", "the amendment check", "Amended: 2.3.c.3")
    assert not is_live(e) and is_live(load_library(root).entries["use_table"])
    assert flag(root, PINNED, amended, apply=True) == []                 # already pulled


def test_no_live_entry_cites_a_section_changed_since_its_ruleset():
    rulesets = PINNED.parent
    pinned = section_texts(PINNED)
    for e in load_library().entries.values():
        if not is_live(e) or e.ruleset == PINNED_KEY:
            continue
        older = rulesets / e.ruleset
        assert older.exists(), f"{e.id}: approved against {e.ruleset}, which is not on disk to compare"
        c = changed(section_texts(older), pinned)
        assert not flagged(load_library(), c) or e.id not in dict(flagged(load_library(), c)), e.id
