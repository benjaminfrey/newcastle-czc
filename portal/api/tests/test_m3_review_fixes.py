"""Fixes from the M3 whole-branch review."""

import pytest
from fastapi.testclient import TestClient

from portal_api.main import create_app
from tests.test_screener import _apps, _first_cell, answers


@pytest.fixture
def draft_client(engine, settings, outbox):
    settings.allow_draft_rules = True
    with TestClient(create_app(settings, outbox)) as c:
        yield c


def _post(c, **kw):
    return c.post("/api/screener", json=answers(**kw)).json()


def _certain(res):
    return {(o["application"], o["certainty"]) for o in res["outcomes"]}


# 1. Fewer than three lots can still be a subdivision (3+ lots within 5 years).

def test_two_lots_is_not_called_not_a_subdivision(draft_client):
    res = _post(draft_client, project=["divide"], division={"lots_after": 2})
    text = " ".join(n["text"] for n in res["notes"])
    assert "isn't a subdivision" not in text and "five years" in text


# 2. Small or Large Project Plan depends on the kind of work, not only new floor area.

def test_a_large_renovation_is_a_large_project(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "renovation", "total_floor_area_sf": 15000})
    assert ("large_project_plan", "needed") in _certain(res)
    o = next(o for o in res["outcomes"] if o["application"] == "large_project_plan")
    assert o["why"]["cite"] == "8.11.b.3"


def test_a_small_renovation_is_a_small_project_citing_renovations(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "renovation", "total_floor_area_sf": 4000})
    o = next(o for o in res["outcomes"] if o["application"] == "small_project_plan")
    assert o["why"]["cite"] == "8.10.b.2"


def test_a_big_parking_lot_is_a_large_project(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "site", "parking_spaces": 60})
    assert ("large_project_plan", "needed") in _certain(res)


def test_an_addition_cites_additions(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "addition", "gross_floor_area_sf": 12000})
    o = next(o for o in res["outcomes"] if o["application"] == "small_project_plan")
    assert o["why"]["cite"] == "8.10.b.3" and o["certainty"] == "may_need"


def test_new_building_of_unknown_size_may_need_either(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "new"})
    assert {("small_project_plan", "may_need"), ("large_project_plan", "may_need")} <= _certain(res)


def test_building_results_mention_large_project_impacts(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "new", "gross_floor_area_sf": 800})
    assert any(n["cite"] == "8.11.b.1" for n in res["notes"])


# 4. In production, any draft refuses the answer — even an answer where no rule fired.

def test_no_rule_firing_is_still_refused_while_rules_are_drafts(engine, settings, outbox):
    with TestClient(create_app(settings, outbox)) as c:
        r = c.post("/api/screener", json=answers(project=["divide"], division={"lots_after": None}))
        assert r.status_code == 503 and r.json() == {"detail": "screener_not_approved"}


def test_dividing_with_lots_unknown_may_be_a_subdivision(draft_client):
    res = _post(draft_client, project=["divide"])
    assert ("subdivision", "may_need") in _certain(res)


# 5. Only a lot that is wholly Civic is town-only; the server decides, not the client.

def test_a_sliver_of_civic_keeps_the_rest_of_the_lot(draft_client):
    res = _post(draft_client, project=["use"], use_key=_first_cell("u"),
                property={"district_codes": ["D2", "SD-Civic"], "on_state_highway": False, "civic": True})
    assert res["town_only"] is False and ("use_permit", "D2") in _apps_of(res)
    assert any("Civic" in n["text"] for n in res["notes"])


def test_a_wholly_civic_lot_is_town_only_even_if_the_client_says_not(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "new", "gross_floor_area_sf": 500},
                property={"district_codes": ["SD-Civic"], "on_state_highway": False, "civic": False})
    assert res["town_only"] is True and res["outcomes"] == []


def _apps_of(res):
    return {(o["application"], o["district"]) for o in res["outcomes"]}


# 6. The MaineDOT note is conditional and shows when the road is unknown.

def test_maine_dot_note_is_conditional(draft_client):
    res = _post(draft_client, project=["driveway"], property={"district_codes": ["D1"], "on_state_highway": True, "civic": False})
    note = next(n["text"] for n in res["notes"] if "Maine Department of Transportation" in n["text"])
    assert note.startswith("If the entrance will be onto a State highway")


def test_maine_dot_note_shows_when_the_road_is_unknown(draft_client):
    res = _post(draft_client, project=["driveway"], property={"district_codes": ["D1"], "on_state_highway": None, "civic": False})
    assert any("Maine Department of Transportation" in n["text"] for n in res["notes"])


def test_no_maine_dot_note_on_a_town_road(draft_client):
    res = _post(draft_client, project=["driveway"], property={"district_codes": ["D1"], "on_state_highway": False, "civic": False})
    assert not any("Maine Department of Transportation" in n["text"] for n in res["notes"])


# 7. Subdivision by homes counts new homes; converting a building points to §12.b.2.

def test_two_new_homes_are_not_a_subdivision(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "new", "gross_floor_area_sf": 2000, "new_dwelling_units": 2})
    assert "subdivision" not in {a for a, _ in _apps_of(res)}


def test_three_new_homes_are_a_subdivision(draft_client):
    res = _post(draft_client, project=["build"], building={"kind": "new", "gross_floor_area_sf": 6000, "new_dwelling_units": 3})
    assert ("subdivision", "needed") in _certain(res)


def test_a_residential_use_mentions_conversions(draft_client):
    res = _post(draft_client, project=["use"], use_key="residence")
    assert any(n["cite"] == "8.12.b.2" for n in res["notes"])


def test_unknown_answer_fields_are_refused(draft_client):
    # A renamed field (dwelling_units → new_dwelling_units) must not be silently ignored.
    r = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "dwelling_units": 3}))
    assert r.status_code == 422
