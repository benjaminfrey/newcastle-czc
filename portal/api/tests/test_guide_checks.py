import pytest

from portal_api.guide.checks import check_turn, counted_stories
from portal_api.guide.content import load_content
from portal_api.guide.engine import Action, Lot, replay


def lot(*codes, disputed=False):
    return Lot(map_lot="012-034", district_codes=codes, district_names=codes, acres=0.5, frontage_ft=120,
               disputed=disputed)


def a(turn_id, value):
    return Action("answer", turn_id, value)


START = [a("lot", "yes"), a("confirm", "yes")]
STORIES = [a("full_stories", 2), a("roof_floors", 0), a("basement_exposed_5ft", "no")]
UNTIL_SETBACKS = [*START, *STORIES, a("floor_area", 1800), a("dwelling_units", 1)]


@pytest.fixture(scope="module")
def content():
    return load_content()


def turn(content, turn_id):
    return content.turn(turn_id)


def side(content, value, *codes, facts_extra=None, disputed=False):
    facts = {"building": {"setback": {"side_1": value}}, **(facts_extra or {})}
    return check_turn(turn(content, "setback_side_1"), facts, lot(*codes, disputed=disputed))


def test_the_bound_itself_fits(content):
    c = side(content, 15, "D1")
    assert (c.result, c.room, c.min) == ("fits", 0, 15)


def test_short_of_a_minimum_is_outside_with_the_gap_and_nearest(content):
    c = side(content, 11, "D1")
    assert (c.result, c.gap, c.unit) == ("outside", 4, "ft")
    assert [n["value"] for n in c.nearest] == [15]


def _stories(content, codes, full, roof=0, knee=None, basement=False, unsure=()):
    b = {"full_stories": full, "roof_floors": roof, "basement_exposed_5ft": basement}
    if knee is not None:
        b["top_knee_over_3ft"] = knee
    std = turn(content, "full_stories").standard
    return check_turn(turn(content, "basement_exposed_5ft"), {"building": b}, lot(*codes), unsure=unsure,
                      standard=std)


def test_a_district_without_a_buildings_table_cannot_check_stories(content):
    c = _stories(content, ("SD-Conservation",), 3)
    assert (c.result, c.reason) == ("cannot_check", "not_checkable")


@pytest.mark.parametrize("full,result,gap", [(1, "outside", 1), (2, "fits", None), (4, "outside", 1)])
def test_range_checks_both_sides(content, full, result, gap):
    c = _stories(content, ("D6",), full)
    assert (c.result, c.gap) == (result, gap)


def test_two_districts_that_disagree_cannot_be_checked(content):
    c = check_turn(turn(content, "setback_rear"), {"building": {"setback": {"rear": 10}}}, lot("D1", "D6"))
    assert (c.result, c.reason) == ("cannot_check", "two_districts")


def test_two_districts_that_agree_use_the_stricter_bound(content):
    c = check_turn(turn(content, "setback_rear"), {"building": {"setback": {"rear": 20}}}, lot("D1", "D6"))
    assert (c.result, c.min, c.room) == ("fits", 15, 5)


def test_disputed_lot_makes_district_checks_uncertain(content):
    c = side(content, 30, "D1", facts_extra={"lot": {"confirmed": False}})
    assert (c.result, c.reason) == ("cannot_check", "lot_disputed")
    assert side(content, 30, "D1", disputed=True).reason == "lot_disputed"


def test_no_district_cannot_be_checked(content):
    assert side(content, 30, "SD-Civic").reason == "no_district"
    assert side(content, 30).reason == "no_district"


def test_unsure_input_cannot_be_checked(content):
    c = _stories(content, ("D6",), 2, unsure=("roof_floors",))
    assert (c.result, c.reason) == ("cannot_check", "unknown_input")


@pytest.mark.parametrize("full,roof,knee,basement,count", [
    (2, 0, None, False, 2), (2, 1, False, False, 2), (2, 1, True, False, 3),
    (2, 2, False, False, 3), (2, 1, False, True, 3), (1, 2, True, True, 4),
])
def test_counted_stories_follows_5_7_c(full, roof, knee, basement, count):
    b = {"full_stories": full, "roof_floors": roof, "basement_exposed_5ft": basement}
    if knee is not None:
        b["top_knee_over_3ft"] = knee
    assert counted_stories({"building": b}) == count


def test_counted_stories_is_unknown_while_an_input_is():
    assert counted_stories({"building": {"full_stories": 2, "roof_floors": 1, "basement_exposed_5ft": False}}) is None
    assert counted_stories({"building": {"full_stories": 2}}) is None


def test_the_chairs_three_story_house(content):
    """Three floors, one of them inside the roof with low knee walls: two stories in the Code's
    sense, which D6's 2-3 range allows."""
    s = replay(content, "new_house", lot("D6"), [*START, a("full_stories", 2), a("roof_floors", 1),
                                                  a("top_knee_over_3ft", "no"), a("basement_exposed_5ft", "no")])
    checked = [sh for sh, _ in s.history if sh.check]
    assert [sh.turn_id for sh in checked] == ["basement_exposed_5ft"]
    assert checked[0].check["result"] == "fits" and checked[0].check["value"] == 2


def test_outside_inserts_doesnt_fit_with_nearest_first(content):
    s = replay(content, "new_house", lot("D1"), [*UNTIL_SETBACKS, a("setback_front", 25), a("setback_side_1", 11)])
    assert s.current.turn_id == "doesnt_fit:setback_side_1"
    assert [x["id"] for x in s.current.answers] == ["nearest", "keep_mine", "talk_to_town", "unsure"]
    assert s.current.answers[0]["label"] == "Make it 15 ft"
    assert s.current.ask == "That's 4 ft short of the limit here. Here's the nearest version that fits."
    s2 = replay(content, "new_house", lot("D1"),
                [*UNTIL_SETBACKS, a("setback_front", 25), a("setback_side_1", 11), a("doesnt_fit:setback_side_1", "nearest")])
    assert s2.facts["building"]["setback"]["side_1"] == 15 and s2.current.turn_id == "setback_side_2"
    assert dict(s2.checks)["setback_side_1"]["result"] == "fits"


def test_keeping_my_number_marks_it_for_the_town_and_continues(content):
    s = replay(content, "new_house", lot("D1"),
               [*UNTIL_SETBACKS, a("setback_front", 25), a("setback_side_1", 11), a("doesnt_fit:setback_side_1", "keep_mine")])
    assert s.kept == (("setback_side_1", "keep_mine"),) and s.current.turn_id == "setback_side_2"
    assert s.facts["building"]["setback"]["side_1"] == 11


def test_stories_that_dont_fit_offer_no_number(content):
    s = replay(content, "new_house", lot("D6"), [*START, a("full_stories", 4), a("roof_floors", 0),
                                                  a("basement_exposed_5ft", "no")])
    assert [x["id"] for x in s.current.answers] == ["keep_mine", "talk_to_town", "unsure"]


def test_two_districts_that_both_miss_by_different_amounts_cannot_be_checked(content):
    """D1 wants 15 ft and D4 8 ft: 5 ft misses both, but by how much depends on where the house sits."""
    c = side(content, 5, "D1", "D4")
    assert (c.result, c.reason, c.nearest) == ("cannot_check", "two_districts", ())


def test_two_districts_with_the_same_limit_that_both_miss_are_outside(content):
    c = side(content, 5, "D1", "D1")
    assert (c.result, c.gap) == ("outside", 10)


def test_d6_side_setback_past_5_ft_is_the_boards_call(content):
    """D6 note 5: the Planning Board may widen the side setback, but not beyond 15 ft."""
    c = side(content, 10, "D6")
    assert (c.result, c.reason) == ("cannot_check", "board_decides")
    c = side(content, 16, "D6")
    assert (c.result, c.gap, [n["value"] for n in c.nearest]) == ("outside", 11, [5])
