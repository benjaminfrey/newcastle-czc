import dataclasses

import pytest

from portal_api.guide.content import load_content
from portal_api.guide.engine import Action, AnswerRejected, Lot, apply, replay

LOT = Lot(map_lot="012-034", district_codes=("D4",), district_names=("Village Residential",),
          acres=0.5, frontage_ft=120, disputed=False)


def a(turn_id, value):
    return Action("answer", turn_id, value)


BACK = Action("back", None, None)
START = [a("lot", "yes"), a("confirm", "yes")]


@pytest.fixture(scope="module")
def content():
    return load_content()


def test_first_turn_is_the_lot(content):
    s = replay(content, "new_house", LOT, [])
    assert s.current.turn_id == "lot" and s.current.kind == "lot"
    assert s.current.facts_shown["map_lot"] == "012-034"
    assert s.current.facts_shown["acres"] == {"value": 0.5, "approximate": True}


def test_confirm_sentence_is_assembled_from_the_template(content):
    s = replay(content, "new_house", LOT, [a("lot", "yes")])
    assert s.current.ask == "So you'd like to build a new house on lot 012-034, in Village Residential. Is that right?"


def test_unsure_is_always_offered_last_and_never_ends(content):
    s = replay(content, "new_house", LOT, START)
    assert s.current.answers[-1]["id"] == "unsure"
    s2 = apply(content, s, LOT, a(s.current.turn_id, "unsure"))
    assert s2.current is not None and s2.current.turn_id != s.current.turn_id
    assert s.current.turn_id in s2.unsure


def test_number_out_of_its_turns_range_is_rejected(content):
    s = replay(content, "new_house", LOT, START)
    assert s.current.turn_id == "full_stories"
    with pytest.raises(AnswerRejected) as e:
        apply(content, s, LOT, a("full_stories", 9))
    assert e.value.reason == "out_of_range"


@pytest.mark.parametrize("value", ["three", True, None, float("nan"), float("inf")])
def test_number_that_is_not_a_number_is_rejected(content, value):
    s = replay(content, "new_house", LOT, START)
    with pytest.raises(AnswerRejected) as e:
        apply(content, s, LOT, a("full_stories", value))
    assert e.value.reason == "bad_value"


def test_answer_to_a_turn_that_is_not_current_is_rejected(content):
    s = replay(content, "new_house", LOT, START)
    with pytest.raises(AnswerRejected) as e:
        apply(content, s, LOT, a("floor_area", 2000))
    assert e.value.reason == "not_current"


def test_choice_must_be_one_of_the_answers(content):
    s = replay(content, "new_house", LOT, [])
    with pytest.raises(AnswerRejected) as e:
        apply(content, s, LOT, a("lot", "maybe"))
    assert e.value.reason == "not_an_answer"


def test_back_removes_the_last_answer(content):
    s = replay(content, "new_house", LOT, [*START, a("full_stories", 2), BACK])
    assert s.current.turn_id == "full_stories"
    assert "full_stories" not in s.facts.get("building", {})


def test_back_at_the_start_is_harmless(content):
    s = replay(content, "new_house", LOT, [BACK, BACK, a("lot", "yes"), BACK, BACK])
    assert s.current.turn_id == "lot" and s.history == ()


def test_replay_skips_answers_to_removed_turns(content):
    trimmed = dataclasses.replace(content, turns=tuple(t for t in content.turns if t.id != "full_stories"))
    s = replay(trimmed, "new_house", LOT, [*START, a("full_stories", 2), a("roof_floors", 0)])
    assert s.current.turn_id == "basement_exposed_5ft"
    assert s.facts["building"] == {"roof_floors": 0}


def test_knee_wall_is_asked_only_with_a_roof_floor(content):
    s = replay(content, "new_house", LOT, [*START, a("full_stories", 2), a("roof_floors", 0)])
    assert s.current.turn_id == "basement_exposed_5ft"
    s = replay(content, "new_house", LOT, [*START, a("full_stories", 2), a("roof_floors", 1)])
    assert s.current.turn_id == "top_knee_over_3ft"


def test_steps_count_the_projects_own_steps(content):
    s = replay(content, "new_house", LOT, START)
    assert (s.current.step.n, s.current.step.of, s.current.step.label) == (3, 4, "The building")
    s = replay(content, "change_of_use", LOT, START)
    assert (s.current.step.n, s.current.step.of, s.current.step.label) == (3, 3, "The use")


def test_use_answers_follow_the_chosen_group(content):
    s = replay(content, "change_of_use", LOT, [*START, a("use_group", "home")])
    assert s.current.turn_id == "use_key"
    assert [x["id"] for x in s.current.answers][:2] == ["residence", "tourist_rental"]


def test_no_on_so_you_mean_shows_the_opening_picker(content):
    s = replay(content, "new_house", LOT, [a("lot", "yes"), a("confirm", "no")])
    assert s.current.turn_id == "pick_opening"
    assert {x["id"] for x in s.current.answers} == {"new_house", "change_of_use"}
    with pytest.raises(AnswerRejected):
        apply(content, s, LOT, a("pick_opening", "change_of_use"))  # the start route restarts it


def test_same_actions_give_identical_states(content):
    actions = [*START, a("full_stories", 2), a("roof_floors", 1), a("top_knee_over_3ft", "no"),
               a("basement_exposed_5ft", "no"), a("floor_area", 1800), a("dwelling_units", 1)]
    first = repr(replay(content, "new_house", LOT, actions))
    assert all(repr(replay(content, "new_house", LOT, actions)) == first for _ in range(50))


def test_free_text_is_not_an_action():
    with pytest.raises(AnswerRejected):
        replay(load_content(), "new_house", LOT, [Action("note", None, "please read me")])


def test_drafts_list_what_the_state_shows(content):
    s = replay(content, "new_house", LOT, START)
    assert "turns.yaml: full_stories" in s.drafts and "openings.yaml: new_house" in s.drafts
    assert "entries.yaml: how_stories_count" in s.drafts and "wording.yaml: unsure" in s.drafts


# --- plan 3: Change ("revisit") ---

D1 = dataclasses.replace(LOT, district_codes=("D1",), district_names=("Rural",))
STORIES_1 = [a("full_stories", 2), a("roof_floors", 1), a("top_knee_over_3ft", "no"), a("basement_exposed_5ft", "no")]


def revisit(turn_id):
    return Action("revisit", turn_id, None)


def test_revisit_asks_that_turn_again(content):
    s = replay(content, "new_house", LOT, [*START, *STORIES_1, a("floor_area", 1800)])
    s2 = apply(content, s, LOT, revisit("full_stories"))
    assert s2.current.turn_id == "full_stories"
    assert "floor_area" in dict(s2.live)


def test_revisit_keeps_later_answers_that_still_apply(content):
    s = replay(content, "new_house", LOT, [*START, *STORIES_1, a("floor_area", 1800)])
    s = apply(content, s, LOT, revisit("roof_floors"))
    s = apply(content, s, LOT, a("roof_floors", 0))
    assert s.current.turn_id == "dwelling_units"
    assert "top_knee_over_3ft" not in [sh.turn_id for sh, _ in s.history]
    assert dict(s.live)["floor_area"] == 1800


def test_revisit_clears_the_doesnt_fit_choice(content):
    before = [*START, *STORIES_1, a("floor_area", 1800), a("dwelling_units", 1), a("setback_front", 30),
              a("setback_side_1", 11), a("doesnt_fit:setback_side_1", "keep_mine")]
    s = replay(content, "new_house", D1, before)
    s = apply(content, s, D1, revisit("setback_side_1"))
    s = apply(content, s, D1, a("setback_side_1", 11))
    assert s.current.turn_id == "doesnt_fit:setback_side_1"


def test_revisit_of_an_unanswered_turn_is_refused(content):
    s = replay(content, "new_house", LOT, START)
    with pytest.raises(AnswerRejected) as e:
        apply(content, s, LOT, revisit("floor_area"))
    assert e.value.reason == "not_answered"


def test_replay_of_a_recorded_revisit_matches_apply(content):
    actions = [*START, *STORIES_1, a("floor_area", 1800), revisit("roof_floors"), a("roof_floors", 0)]
    s = replay(content, "new_house", LOT, [])
    for act in actions:
        s = apply(content, s, LOT, act)
    assert s == replay(content, "new_house", LOT, actions)
