import pytest
from fastapi.testclient import TestClient

from portal_api.main import create_app
from portal_api.ruleset import load_ruleset

APP_FOR = {"u": "use_permit", "rc": "residential_companion", "ex": "expanded_use", "sp": "special_permit"}


@pytest.fixture
def draft_client(engine, settings, outbox):
    settings.allow_draft_rules = True
    with TestClient(create_app(settings, outbox)) as c:
        yield c


def answers(**kw):
    base = {"project": ["use"], "property": {"district_codes": ["D2"], "on_state_highway": False, "civic": False},
            "use_key": None, "building": {"kind": None, "gross_floor_area_sf": None, "dwelling_units": None},
            "division": {"lots_after": None}}
    base.update(kw)
    return base


def _apps(r):
    return {(o["application"], o["district"]) for o in r.json()["outcomes"]}


def _first_cell(code, district="d2"):
    return next(k[1] for k, c in load_ruleset().cells.items() if k[0] == district and c["code"] == code)


def test_use_from_the_table(draft_client):
    r = draft_client.post("/api/screener", json=answers(use_key=_first_cell("u")))
    assert ("use_permit", "D2") in _apps(r)
    o = next(o for o in r.json()["outcomes"] if o["application"] == "use_permit")
    assert o["reviewer"] == "Code Enforcement Officer" and o["days"][0]["days"] == 30
    assert o["why"]["cite"] == "8.15.b.1" and "new Use or a change of Use" in o["why"]["text"]
    assert o["district_name"] == "Neighborhood Residential (D2)"
    assert o["in_portal"] is True


def test_use_in_two_districts_shows_both(draft_client):
    cells = load_ruleset().cells
    use = next(u for (d, u), c in cells.items()
               if d == "d1" and c["code"] in APP_FOR and cells[("d6", u)]["code"] in APP_FOR
               and cells[("d6", u)]["code"] != c["code"])
    res = draft_client.post("/api/screener", json=answers(
        use_key=use, property={"district_codes": ["D1", "D6"], "on_state_highway": False, "civic": False}))
    assert {(APP_FOR[cells[("d1", use)]["code"]], "D1"), (APP_FOR[cells[("d6", use)]["code"]], "D6")} <= _apps(res)


def test_use_not_listed_in_district(draft_client):
    res = draft_client.post("/api/screener", json=answers(use_key=_first_cell(""))).json()
    (nl,) = res["not_listed"]
    assert nl["district"] == "D2" and "variance can't be granted for a use" in nl["text"]
    assert "Neighborhood Residential (D2)" in nl["text"] and nl["cite"] == "8.19.b.1"


def test_the_two_permit_cell_needs_both(draft_client):
    res = draft_client.post("/api/screener", json=answers(
        use_key="retail_service_general", property={"district_codes": ["D3"], "on_state_highway": False, "civic": False}))
    assert {("residential_companion", "D3"), ("special_permit", "D3")} <= _apps(res)


def test_no_district_yet_asks_for_the_property(draft_client):
    res = draft_client.post("/api/screener", json=answers(
        use_key=_first_cell("u"), property={"district_codes": [], "on_state_highway": None, "civic": False})).json()
    assert res["outcomes"] == [] and any("Find your property" in n["text"] for n in res["notes"])


def test_small_and_large_project_by_floor_area(draft_client):
    small = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "gross_floor_area_sf": 10000, "dwelling_units": 1}))
    large = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "gross_floor_area_sf": 10001, "dwelling_units": 1}))
    assert {a for a, _ in _apps(small)} == {"small_project_plan"}
    assert {a for a, _ in _apps(large)} == {"large_project_plan"}


def test_unknown_building_size_gives_both_with_the_threshold(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["build"])).json()
    assert any("10,000 square feet" in n["text"] for n in res["notes"])


def test_three_homes_is_a_subdivision(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["build"], building={"kind": "new", "gross_floor_area_sf": 3000, "dwelling_units": 3}))
    assert "subdivision" in {a for a, _ in _apps(res)}


def test_dividing_into_two_lots_says_ask_the_ceo(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["divide"], division={"lots_after": 2})).json()
    assert res["outcomes"] == [] and any(n["kind"] == "contact_town" for n in res["notes"])


def test_driveway_on_a_state_highway_adds_maine_dot(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["driveway"], property={"district_codes": ["D1"], "on_state_highway": True, "civic": False})).json()
    assert {o["application"] for o in res["outcomes"]} == {"entrance_permit"}
    assert any("Maine Department of Transportation" in n["text"] for n in res["notes"])


def test_civic_land_is_town_only(draft_client):
    res = draft_client.post("/api/screener", json=answers(project=["build", "use"], use_key=_first_cell("u"),
        property={"district_codes": ["SD-Civic"], "on_state_highway": False, "civic": True})).json()
    assert res["outcomes"] == [] and res["town_only"] is True


def test_draft_rules_are_refused_by_default(engine, settings, outbox):
    with TestClient(create_app(settings, outbox)) as c:
        r = c.post("/api/screener", json=answers(use_key=_first_cell("u")))
        assert r.status_code == 503 and r.json() == {"detail": "screener_not_approved"}
        assert c.get("/api/screener/uses").status_code == 503


def test_uses_endpoint_quotes_the_code(draft_client):
    groups = draft_client.get("/api/screener/uses").json()
    u = next(u for g in groups for u in g["uses"] if u["use_key"] == "dispatch_service")
    assert u["definition"] == load_ruleset().definitions["DISPATCH SERVICE"]["definition"]
    assert u["code_name"] == "Dispatch Service" and u["example"]


def test_bad_answers_are_422(draft_client):
    assert draft_client.post("/api/screener", json=answers(project=["fly"])).status_code == 422
    assert draft_client.post("/api/screener", json=answers(project=[])).status_code == 422
    assert draft_client.post("/api/screener", json=answers(use_key="time_machine")).status_code == 422
