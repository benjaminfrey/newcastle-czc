import dataclasses
import shutil
from pathlib import Path

import pytest
import yaml

import portal_api.guide.content as gc
from portal_api.guide.content import NEVER_WORDS, ContentError, load_content

FILES = ("openings.yaml", "turns.yaml", "entries.yaml", "wording.yaml")


@pytest.fixture
def copy(tmp_path):
    """A writable copy of the content, and a way to change one file's entries."""
    for f in FILES:
        shutil.copy(gc.DIR / f, tmp_path / f)

    def edit(name: str, change) -> Path:
        path = tmp_path / name
        data = yaml.safe_load(path.read_text())
        change(data)
        path.write_text(yaml.safe_dump(data, sort_keys=False))
        return tmp_path
    return edit


def all_draft(c):
    """`c` with every entry a draft again: the chair approved the content on 2026-11-06, and
    these tests are about what a draft does."""
    d = lambda e: dataclasses.replace(e, status="draft")  # noqa: E731
    return dataclasses.replace(
        c, openings={k: d(o) for k, o in c.openings.items()}, turns=tuple(d(t) for t in c.turns),
        entries={k: d(e) for k, e in c.entries.items()},
        wording={k: {**w, "status": "draft"} for k, w in c.wording.items()})


def _turn(data: list, turn_id: str) -> dict:
    return next(t for t in data if t["id"] == turn_id)


def test_content_loads():
    c = load_content()
    assert set(c.openings) == {"new_house", "change_of_use"}
    assert [t.order for t in c.turns] == sorted(t.order for t in c.turns)
    assert len(c.digest) == 64


def test_every_cite_resolves(copy):
    root = copy("turns.yaml", lambda d: _turn(d, "full_stories").update(cite="99.1.a"))
    with pytest.raises(ContentError, match="turns.yaml: full_stories"):
        load_content(root)


def test_every_entry_cite_resolves(copy):
    root = copy("entries.yaml", lambda d: d[0]["cites"].append("99.1.a"))
    with pytest.raises(ContentError, match="entries.yaml"):
        load_content(root)


def test_status_rules(copy):
    root = copy("turns.yaml", lambda d: _turn(d, "full_stories").pop("approved_on"))
    with pytest.raises(ContentError, match="approved_on"):
        load_content(root)


def test_answers_only_set_known_facts(copy):
    root = copy("turns.yaml", lambda d: _turn(d, "lot")["answers"][0].update(set={"lot.colour": "red"}))
    with pytest.raises(ContentError, match="lot.colour"):
        load_content(root)


@pytest.mark.parametrize("missing", ["fact", "min", "max"])
def test_number_turns_need_bounds_and_a_fact(copy, missing):
    root = copy("turns.yaml", lambda d: _turn(d, "floor_area").pop(missing))
    with pytest.raises(ContentError, match="floor_area"):
        load_content(root)


def test_templates_use_known_slots(copy):
    root = copy("wording.yaml", lambda d: d["confirm_build"].update(text="So you mean {owner}?"))
    with pytest.raises(ContentError, match="owner"):
        load_content(root)


def _readable(c) -> list[str]:
    out = []
    for t in c.turns:
        out += [t.ask, t.help or ""] + [x for a in t.answers for x in (a.label, a.hint or "")]
    for answers in c.use_answers.values():
        out += [x for a in answers for x in (a.label, a.hint or "")]
    for e in c.entries.values():
        out += [e.overline, e.answer, e.detail, e.why]
    for w in c.wording.values():
        out += [v for k, v in w.items() if k in ("text", "title", "body")]
    out += [o.label for o in c.openings.values()]
    return out


def test_no_never_words():
    for text in _readable(load_content()):
        assert not NEVER_WORDS.search(text), text
    assert NEVER_WORDS.search("Approved by the Town") and NEVER_WORDS.search("a permit issued today")
    assert not NEVER_WORDS.search("the Board's approval")  # whole words only
    assert not NEVER_WORDS.search("It fits within the limit")


def test_content_is_draft_until_the_chair_approves_it():
    for name in FILES:
        data = yaml.safe_load((gc.DIR / name).read_text())
        entries = data if isinstance(data, list) else list(data.values())
        for e in entries:
            assert e["status"] == "draft" or e.get("approved_by") == "Ben Frey, Planning Board chair", (name, e.get("id"))


def test_a_new_house_is_checked_as_a_residential_primary_building():
    """The chair, 2026-11-05: a new house uses the Residential column of Permitted Buildings and
    the Primary Building Placement panel, as the approved form already pairs them."""
    for t in load_content().turns:
        if t.standard and t.when and "new_house" in str(t.when):
            s = t.standard
            if s["source"] == "building_matrix":
                assert s.get("building") == "Residential", t.id
            else:
                assert s["field"].startswith("primary_building_placement."), t.id


# The chair approved the rest on 2026-11-06; "You're already covered" is never shown, so it stays a draft.
STILL_DRAFT = {("wording.yaml", "covered")}


def test_the_chair_approved_everything_shown_on_2026_11_06():
    for name in FILES:
        data = yaml.safe_load((gc.DIR / name).read_text())
        entries = data.items() if isinstance(data, dict) else ((e["id"], e) for e in data)
        for key, e in entries:
            if (name, key) in STILL_DRAFT:
                assert e["status"] == "draft", (name, key)
            else:
                assert e["status"] == "approved", (name, key)
