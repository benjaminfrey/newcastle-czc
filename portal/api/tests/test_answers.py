import pytest

from portal_api.forms.answers import AnswerError, Current, applicable, check_value, missing, printed
from portal_api.forms.formdefs import latest_version, load_form
from portal_api.ruleset import load_ruleset

BOUNDS = (-69.62, 44.0, -69.48, 44.1)
LOOKUP = {
    "map_lot": "004-036", "location": "461 SHEEPSCOT RD", "acres": 2.1,
    "districts": [{"code": "D2", "name": "D2 - Neighborhood Residential", "in_ruleset": True, "share": 1.0}],
    "streets": [{"name": "Sheepscot Road", "type": "R2", "type_name": "Rural Road", "ownership": "Town Way", "frontage_ft": 310},
                {"name": "Hall Street", "type": "S3", "type_name": "Neighborhood Street", "ownership": "Town Way", "frontage_ft": 90}],
    "on_state_highway": False,
}


@pytest.fixture(scope="module")
def forms():
    r = load_ruleset()
    return {k: load_form(k, latest_version(k), r) for k in ("use_permit", "small_project_plan", "entrance_permit")}


def field(forms, key, fid):
    return forms[key].field(fid)[1]


def reason(forms, key, fid, value):
    with pytest.raises(AnswerError) as exc:
        check_value(field(forms, key, fid), value, bounds=BOUNDS)
    return exc.value.reason


def cur(answers=None, items=(), prop=LOOKUP):
    return Current(answers=dict(answers or {}), items=list(items), property=prop, account={"email": "a@example.com"})


# ---- check_value ----

def test_check_value_happy_paths(forms):
    assert check_value(field(forms, "use_permit", "applicant_name"), "  Ada Lovelace ") == "Ada Lovelace"
    assert check_value(field(forms, "use_permit", "existing_dwelling_units"), 2) == 2.0
    assert check_value(field(forms, "use_permit", "applicant_is_owner"), False) is False
    assert check_value(field(forms, "small_project_plan", "roof_style"), "gable") == "gable"
    assert check_value(field(forms, "small_project_plan", "work_kinds"), ["addition", "renovation", "addition"]) == ["addition", "renovation"]
    assert check_value(field(forms, "use_permit", "proposed_uses"), ["residence"]) == ["residence"]
    assert check_value(field(forms, "entrance_permit", "entrance_location"), {"lon": -69.55, "lat": 44.05}, bounds=BOUNDS) \
        == {"lon": -69.55, "lat": 44.05}
    assert check_value(field(forms, "use_permit", "deed_book"), {"unknown": True}) == {"unknown": True}
    assert check_value(field(forms, "use_permit", "deed_book"), None) is None
    assert check_value(field(forms, "use_permit", "deed_book"), "   ") is None


def test_check_value_not_a_question(forms):
    assert reason(forms, "use_permit", "map_lot", "004-036") == "not_a_question"
    assert reason(forms, "use_permit", "signature", "Ada") == "not_a_question"


def test_check_value_wrong_type(forms):
    assert reason(forms, "use_permit", "existing_dwelling_units", "two") == "wrong_type"
    assert reason(forms, "use_permit", "existing_dwelling_units", True) == "wrong_type"
    assert reason(forms, "use_permit", "applicant_is_owner", "yes") == "wrong_type"
    assert reason(forms, "use_permit", "applicant_name", 5) == "wrong_type"
    assert reason(forms, "use_permit", "use_documents", ["x"]) == "wrong_type"
    assert reason(forms, "entrance_permit", "entrance_location", {"lon": "x", "lat": 1}) == "wrong_type"
    assert reason(forms, "use_permit", "existing_dwelling_units", float("nan")) == "wrong_type"


def test_check_value_not_an_option(forms):
    assert reason(forms, "small_project_plan", "roof_style", "dome") == "not_an_option"
    assert reason(forms, "small_project_plan", "work_kinds", ["addition", "moat"]) == "not_an_option"
    assert reason(forms, "use_permit", "proposed_uses", ["castle"]) == "not_an_option"


def test_check_value_out_of_range(forms):
    assert reason(forms, "small_project_plan", "windows_north", 101) == "out_of_range"
    assert reason(forms, "use_permit", "existing_dwelling_units", -1) == "out_of_range"
    assert reason(forms, "entrance_permit", "entrance_location", {"lon": -70.5, "lat": 44.05}) == "out_of_range"


def test_check_value_unknown_not_allowed(forms):
    assert reason(forms, "use_permit", "applicant_name", {"unknown": True}) == "unknown_not_allowed"


def test_check_value_too_long(forms):
    assert reason(forms, "use_permit", "applicant_name", "x" * 2001) == "too_long"
    assert reason(forms, "use_permit", "proposed_description", "x" * 10001) == "too_long"


# ---- applicable / missing / printed ----

def ids(rows):
    return [(f.id, item) for _, f, item in rows]


def test_not_owner_adds_owner_questions(forms):
    form = forms["use_permit"]
    owner = [i for i, _ in ids(applicable(form, cur({("applicant_is_owner", None): True})))]
    assert "owner_name" not in owner
    not_owner = [i for i, _ in ids(applicable(form, cur({("applicant_is_owner", None): False})))]
    assert {"owner_name", "owner_email", "owner_phone", "owner_address"} <= set(not_owner)


def test_floor_heights_follow_stories(forms):
    form = forms["small_project_plan"]
    items = [("b1", "building", 0), ("b2", "building", 1)]
    rows = ids(applicable(form, cur({("stories", "b1"): 1, ("stories", "b2"): 3}, items)))
    assert ("floor_height_2", "b1") not in rows
    assert {("floor_height_2", "b2"), ("floor_height_3", "b2")} <= set(rows)
    assert ("floor_height_4", "b2") not in rows
    # Each building gets every Building Form section before the next building starts.
    order = [r for r in rows if r[1] in ("b1", "b2")]
    first_b2 = order.index(("building_name", "b2"))
    assert all(item == "b1" for _, item in order[:first_b2])


def test_components_ask_roof_only_for_additions_and_garages(forms):
    form = forms["small_project_plan"]
    items = [("b1", "building", 0), ("c1", "component", 0), ("c2", "component", 1)]
    rows = ids(applicable(form, cur({("component_kind", "c1"): "deck", ("component_kind", "c2"): "garage"}, items)))
    assert ("component_roof_style", "c1") not in rows
    assert ("component_roof_style", "c2") in rows  # an attached garage (redesign: no attached/detached question)
    assert ("component_height", "c1") in rows


def test_hidden_answers_are_kept_not_counted(forms):
    form = forms["use_permit"]
    answers = {("applicant_is_owner", None): False, ("owner_name", None): "Grace Hopper"}
    c = cur(answers)
    assert any(f.id == "owner_name" for _, rows in [(s, r) for s, _, r in printed(form, c)] for f, _ in rows)
    answers[("applicant_is_owner", None)] = True
    c = cur(answers)
    assert ("owner_name", None) in c.answers  # kept
    assert "owner_name" not in [f for f, _ in missing(form, c)]
    assert all(f.id != "owner_name" for _, _, rows in printed(form, c) for f, _ in rows)
    answers[("applicant_is_owner", None)] = False
    shown_again = {f.id: v for _, _, rows in printed(form, cur(answers)) for f, v in rows}
    assert shown_again["owner_name"] == "Grace Hopper"


def test_unknown_is_not_missing(forms):
    form = forms["use_permit"]
    assert "lot_width" in [f for f, _ in missing(form, cur())]
    assert "lot_width" not in [f for f, _ in missing(form, cur({("lot_width", None): {"unknown": True}}))]


def test_removed_item_drops_its_questions(forms):
    form = forms["small_project_plan"]
    rows = ids(applicable(form, cur(items=[("b1", "building", 0)])))
    assert ("building_name", "b1") in rows
    assert not any(item == "b1" for _, item in ids(applicable(form, cur(items=[]))))


def test_prefilled_property_values_are_not_missing(forms):
    form = forms["use_permit"]
    gone = [f for f, _ in missing(form, cur())]
    assert "lot_area" not in gone and "street_address" not in gone and "street_frontage" not in gone
    manual = {"map_lot": "004-036", "location": None, "acres": None, "districts": [], "streets": [], "on_state_highway": None}
    gone = [f for f, _ in missing(form, cur(prop=manual))]
    assert "lot_area" in gone and "street_address" in gone


def test_printed_resolves_property_and_derived_fields(forms):
    form = forms["use_permit"]
    c = cur({("applicant_name", None): "Ada Lovelace", ("lot_area", None): 2.4})
    values = {(s.id, f.id): v for s, _, rows in printed(form, c) for f, v in rows}
    assert values[("location", "map_lot")] == "004-036"
    assert values[("location", "street_address")] == "461 SHEEPSCOT RD"
    assert values[("site", "zoning_district")] == "D2 - Neighborhood Residential"
    assert values[("site", "lot_area")] == 2.4  # the applicant's correction wins
    assert values[("site", "street_frontage")] == 400
    assert values[("applicant", "applicant_email")] == "a@example.com"
    assert values[("use_header", "use_applicant_name")] == "Ada Lovelace"
    assert values[("use_header", "use_map_lot")] == "004-036"
    assert values[("certification", "signature")] is None
    sp = forms["entrance_permit"]
    values = {(s.id, f.id): v for s, _, rows in printed(sp, cur()) for f, v in rows}
    assert values[("entrance", "lot_streets")] == "Sheepscot Road (Rural Road), about 310 ft; Hall Street (Neighborhood Street), about 90 ft"
