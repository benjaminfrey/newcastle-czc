"""The chair's rulings of 2026-10-18 on the nine review-sheet questions."""

import pytest
from fastapi.testclient import TestClient

from portal_api.forms.definitions import load_definitions
from portal_api.main import create_app
from portal_api.ruleset import load_ruleset
from tests.test_screener import answers


@pytest.fixture
def c(engine, settings, outbox):
    settings.allow_draft_rules = True
    with TestClient(create_app(settings, outbox)) as client:
        yield client


def post(c, **kw):
    r = c.post("/api/screener", json=answers(**kw))
    assert r.status_code == 200, r.text
    return r.json()


def apps(res):
    return {(o["application"], o["certainty"]) for o in res["outcomes"]}


def by_app(res, key):
    return next(o for o in res["outcomes"] if o["application"] == key)


def build(**b):
    return {"kind": "new", "gross_floor_area_sf": 2000, **b}


# Q1 — any home, owner-occupied or rented, is the Residence use.

def test_building_a_home_runs_residence_through_the_use_table(c):
    cell = load_ruleset().cells[("d2", "residence")]
    res = post(c, project=["build"], building=build(new_dwelling_units=1, homes_added_last_5_years=0))
    expected = {"u": "use_permit", "rc": "residential_companion", "ex": "expanded_use", "sp": "special_permit"}[cell["code"]]
    assert (expected, "D2") in {(o["application"], o["district"]) for o in res["outcomes"]}


def test_residence_example_covers_owners_and_renters():
    defs = load_definitions(load_ruleset())
    ex = next(u.example for g in defs.groups for u in g.uses if u.use_key == "residence")
    assert "live there" in ex and "rent" in ex


# Q2 — Residential Companion shows 30 days (§15.d.1 via §17.c.1).

def test_residential_companion_shows_thirty_days(c):
    res = post(c, use_key="retail_service_general", property={"district_codes": ["D3"], "on_state_highway": False, "civic": False})
    assert [d["days"] for d in by_app(res, "residential_companion")["days"]] == [30]


# Q3 — divisions in the last five years.

def test_two_lots_with_no_recent_division_is_not_a_subdivision(c):
    res = post(c, project=["divide"], division={"lots_after": 2, "divided_last_5_years": False})
    assert "subdivision" not in {a for a, _ in apps(res)}
    assert any("isn't a subdivision" in n["text"] for n in res["notes"])


def test_two_lots_after_a_recent_division_may_be_a_subdivision(c):
    res = post(c, project=["divide"], division={"lots_after": 2, "divided_last_5_years": True})
    assert ("subdivision", "may_need") in apps(res)


def test_two_lots_with_history_unknown_keeps_the_caution(c):
    res = post(c, project=["divide"], division={"lots_after": 2, "divided_last_5_years": None})
    assert any("five years" in n["text"] and n["kind"] == "contact_town" for n in res["notes"])


# Q4 — additions over 10,000 sf are a Large Project Plan.

def test_small_addition_is_a_small_project(c):
    res = post(c, project=["build"], building={"kind": "addition", "gross_floor_area_sf": 800})
    assert apps(res) >= {("small_project_plan", "needed")}
    assert by_app(res, "small_project_plan")["why"]["cite"] == "8.10.b.3"


def test_large_addition_is_a_large_project_citing_the_ruling(c):
    res = post(c, project=["build"], building={"kind": "addition", "gross_floor_area_sf": 12000})
    o = by_app(res, "large_project_plan")
    assert o["certainty"] == "needed" and o["why"]["cite"] == "8.11.b.1"
    assert "chair" in o["why"]["ruling"].lower()


def test_addition_of_unknown_size_may_need_either(c):
    res = post(c, project=["build"], building={"kind": "addition"})
    assert {("small_project_plan", "may_need"), ("large_project_plan", "may_need")} <= apps(res)


# Q5/Q6 — rulings recorded on rules that keep their behaviour.

def test_rulings_are_recorded_on_their_rules():
    defs = load_definitions(load_ruleset())
    rules = {r.id: r for r in defs.rules}
    for rid in ("renovation-small", "renovation-large", "maine-dot", "addition-large", "homes-within-five-years",
                "divide-fewer-recent"):
        assert rules[rid].ruling and rules[rid].ruling["on"] == "2026-10-18", rid
    assert defs.applications["residential_companion"].ruling


# Q7 — homes added over five years count together.

def test_homes_over_five_years_count_together(c):
    res = post(c, project=["build"], building=build(new_dwelling_units=1, homes_added_last_5_years=2))
    assert ("subdivision", "needed") in apps(res)


def test_one_new_home_with_no_earlier_homes_is_not_a_subdivision(c):
    res = post(c, project=["build"], building=build(new_dwelling_units=1, homes_added_last_5_years=0))
    assert "subdivision" not in {a for a, _ in apps(res)}


def test_earlier_homes_unknown_may_be_a_subdivision(c):
    res = post(c, project=["build"], building=build(new_dwelling_units=1))
    assert ("subdivision", "may_need") in apps(res)


# Q8 — the CEO may send Small and Large Project Plans to the Planning Board.

def test_project_plans_say_the_ceo_may_send_them_to_the_board(c):
    small = by_app(post(c, project=["build"], building=build()), "small_project_plan")
    large = by_app(post(c, project=["build"], building=build(gross_floor_area_sf=20000)), "large_project_plan")
    assert "may send it to the Planning Board" in small["reviewer"]
    assert "may send it to the Planning Board" in large["reviewer"]
    board = [d for d in large["days"] if d.get("when")]
    assert [d["days"] for d in board] == [30, 30] and all(d["when"] == "if sent to the Planning Board" for d in board)
