"""The guide shows only what its mode allows (library plan 1, task 4).

Public: live entries only. The LAN copy: everything not pulled, with what isn't live marked as a
draft. A standard with no entry goes to the Town and shows no number (decision 12).
"""

import pytest

from portal_api.guide.content import load_content
from portal_api.guide.engine import Action, Lot, _Build, replay
from portal_api.guide.packet import checklist_of
from portal_api.library.view import View, using
from portal_api.main import create_app

LOT = Lot(map_lot="004-036", district_codes=("D1",), district_names=("Rural",), acres=2.0, frontage_ft=300)
START = [Action("answer", "lot", "yes"), Action("answer", "confirm", "yes")]
STORIES = [Action("answer", "full_stories", 2), Action("answer", "roof_floors", 0),
           Action("answer", "basement_exposed_5ft", "no")]


def _draft(d):
    e = next(e for e in d["entries"] if e["id"] == "how_stories_count")
    e.update(status="draft")
    e.pop("approved_by")
    e.pop("approved_on")


def _claim_stories(d):
    base = next(e for e in d["entries"] if e["id"] == "how_stories_count")
    base.update(standards=["building:total_stories"], answer="At most {stories}.",
                slots={"stories": {"standard": "building:total_stories", "part": "max"}})


def _state(root, view, actions=START):
    with using(view):
        c = load_content(library_root=root)
        return c, replay(c, "new_house", LOT, actions)


def test_public_with_drafts_will_not_start(settings):
    with pytest.raises(RuntimeError, match="public_with_drafts"):
        create_app(settings.model_copy(update={"public": True, "allow_draft_rules": True}))
    create_app(settings.model_copy(update={"public": True}))


def test_public_shows_only_live_entries(lib):
    root = lib("guide", _draft)
    _, s = _state(root, View(public=True))
    assert s.current.turn_id == "full_stories" and s.current.ask
    assert s.current.why is None and not any("how_stories_count" in d for d in s.drafts)


def test_lan_shows_a_draft_and_marks_it(lib):
    root = lib("guide", _draft)
    _, s = _state(root, View())
    assert s.current.why["id"] == "how_stories_count"
    assert "library/guide: how_stories_count" in s.drafts


def test_a_pulled_entry_is_shown_in_neither_mode():
    for public in (True, False):
        _, s = _state(None, View(public=public, pulled=frozenset({"how_stories_count"})))
        assert s.current.why is None


def test_a_standard_with_no_entry_goes_to_the_town():
    _, s = _state(None, View(covers_standards=True), START + STORIES)
    chk = dict(s.checks)["basement_exposed_5ft"]
    assert (chk["result"], chk["reason"]) == ("cannot_check", "no_entry")
    assert chk["min"] is None and chk["max"] is None


def test_without_covering_the_old_checks_stand():
    _, s = _state(None, View(), START + STORIES)
    assert dict(s.checks)["basement_exposed_5ft"]["result"] == "fits"


def test_a_standard_with_an_entry_carries_it_filled_in(lib):
    root = lib("guide", _claim_stories)
    _, s = _state(root, View(covers_standards=True), START)
    assert s.current.turn_id == "full_stories"
    assert s.current.why["answer"] == "At most 2 stories."
    assert s.current.why["interpretations"]                       # D1's numbers rest on the chair's Q6 reading
    _, s = _state(root, View(covers_standards=True), START + STORIES)
    assert dict(s.checks)["basement_exposed_5ft"]["result"] == "fits"


def test_the_packet_keeps_each_entry_id_and_version(lib):
    root = lib("guide", _claim_stories)
    c, s = _state(root, View(covers_standards=True), START + STORIES)
    with using(View(covers_standards=True)):
        build = _Build(c, "new_house", LOT)
        town, fits = checklist_of(s, lambda t: t, lambda t: build.why_for(c.turn(t)))
    rows = [r for r in town + fits if r["why"]]
    assert rows and all({"id", "version"} <= set(r["why"]) for r in rows)
