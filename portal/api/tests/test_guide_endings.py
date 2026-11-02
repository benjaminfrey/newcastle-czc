import dataclasses

import pytest

from portal_api.guide.content import NEVER_WORDS, load_content
from portal_api.guide.engine import Action, Lot, replay
from portal_api.ruleset import district_key_for, load_ruleset


def lot(*codes):
    return Lot(map_lot="012-034", district_codes=codes, district_names=codes, acres=0.5, frontage_ft=120)


def a(turn_id, value):
    return Action("answer", turn_id, value)


START = [a("lot", "yes"), a("confirm", "yes")]
STORIES = [a("full_stories", 2), a("roof_floors", 0), a("basement_exposed_5ft", "no")]
SIZE = [a("floor_area", 2000), a("dwelling_units", 1)]
D1_SETBACKS = [a("setback_front", 30), a("setback_side_1", 20), a("setback_side_2", 20), a("setback_rear", 20)]
CODES = ("D1", "D2", "D3", "D4", "D5", "D6")


@pytest.fixture(scope="module")
def content():
    return load_content()


def _group_of(content, use_key):
    return next(g for g, uses in content.use_answers.items() if any(u.id == use_key for u in uses))


def _listed(code, use_key):
    cell = load_ruleset().cells[(district_key_for(code), use_key)]
    return bool(cell.get("codes") or cell.get("code"))


def _use(content, codes, use_key):
    return replay(content, "change_of_use", lot(*codes),
                  [*START, a("use_group", _group_of(content, use_key)), a("use_key", use_key)])


def test_a_house_that_fits_is_ready_with_its_reviews(content):
    no_stories = dataclasses.replace(content, turns=tuple(t for t in content.turns if t.computed != "stories"))
    s = replay(no_stories, "new_house", lot("D1"), [*START, *SIZE, *D1_SETBACKS])
    assert s.current is None and s.ending["kind"] == "ready"
    assert "small_project_plan" in [r["application"] for r in s.ending["reviews"]]
    assert s.ending["title"] == "Your application is ready to send"


def test_no_new_house_is_ready_on_todays_ruleset(content):
    """Total Stories is a bare number everywhere but D6, and D6's side setback is unresolved:
    the coverage memo's question 1, seen from the applicant's side. Changes when the chair answers."""
    for code in CODES:
        s = replay(content, "new_house", lot(code), [*START, *STORIES, *SIZE, *D1_SETBACKS])
        while s.current is not None and s.current.turn_id.startswith("doesnt_fit:"):
            s = replay(content, "new_house", lot(code),
                       [*START, *STORIES, *SIZE, *D1_SETBACKS, a(s.current.turn_id, "keep_mine")])
        assert s.ending["kind"] == "town_judgment", code


def test_cannot_check_goes_to_the_town_not_to_no(content):
    s = replay(content, "new_house", lot("D4"), [*START, *STORIES, *SIZE, *D1_SETBACKS])
    assert s.ending["kind"] == "town_judgment"
    unsettled = {u["turn_id"]: u["reason"] for u in s.ending["unsettled"]}
    assert unsettled["basement_exposed_5ft"] == "not_checkable"


def test_unsure_goes_to_the_town(content):
    no_stories = dataclasses.replace(content, turns=tuple(t for t in content.turns if t.computed != "stories"))
    s = replay(no_stories, "new_house", lot("D1"), [*START, a("floor_area", "unsure"), a("dwelling_units", 1),
                                                     *D1_SETBACKS])
    assert s.ending["kind"] == "town_judgment"
    assert {"turn_id": "floor_area", "reason": "unsure"} in s.ending["unsettled"]


def test_use_not_listed_anywhere_on_the_lot_is_not_here_with_what_is_allowed(content):
    use_key = next(u["use_key"] for u in load_ruleset().uses if not _listed("D1", u["use_key"]))
    s = _use(content, ("D1",), use_key)
    assert s.ending["kind"] == "not_here"
    allowed = s.ending["allowed_uses"][0]
    assert allowed["district"] == "D1" and allowed["uses"]
    assert all(_listed("D1", u["use_key"]) for u in allowed["uses"])
    assert s.ending["entry"]["id"] == "use_not_listed"


def test_use_listed_in_one_of_two_districts_is_not_not_here(content):
    pair = next((x, y, u["use_key"]) for x in CODES for y in CODES for u in load_ruleset().uses
                if _listed(x, u["use_key"]) and not _listed(y, u["use_key"]))
    s = _use(content, pair[:2], pair[2])
    assert s.ending["kind"] != "not_here"


def test_a_listed_use_is_ready(content):
    code = next(c for c in CODES if _listed(c, "residence"))
    s = _use(content, (code,), "residence")
    assert s.ending["kind"] == "ready" and s.ending["reviews"]


def test_covered_is_never_an_ending(content):
    ends = [replay(content, "new_house", lot(c), [*START, *STORIES, *SIZE, *D1_SETBACKS]).ending for c in CODES]
    ends += [_use(content, ("D1",), u["use_key"]).ending for u in load_ruleset().uses]
    assert all(e is None or e["kind"] != "covered" for e in ends)


def test_ending_words_have_no_never_words(content):
    for key in ("no_permit", "covered", "ready", "town_judgment", "not_here"):
        w = content.wording[key]
        assert not NEVER_WORDS.search(w["title"]) and not NEVER_WORDS.search(w["body"])


def test_endings_bring_their_drafts(content):
    s = _use(content, ("D1",), "residence")
    assert any(d.startswith("wording.yaml: ") for d in s.drafts)
