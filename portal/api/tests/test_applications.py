import shutil

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.forms import formdefs
from portal_api.forms.definitions import DraftEntry
from portal_api.main import create_app
from tests.test_auth import _sign_in
from tests.test_property import _id, layers  # noqa: F401  (fixture)


@pytest.fixture
def app(engine, settings, outbox, layers):  # noqa: F811
    settings.allow_stale_parcels = True
    settings.allow_draft_rules = True
    return create_app(settings, outbox)


@pytest.fixture
def alice(app, outbox):
    with TestClient(app) as c:
        _sign_in(c, outbox, "alice@example.com")
        yield c


@pytest.fixture
def bob(app, outbox):
    with TestClient(app) as c:
        _sign_in(c, outbox, "bob@example.com")
        yield c


@pytest.fixture
def one_form_draft(monkeypatch):
    """Make every form look as if one entry were a draft (the guard must hold after approval)."""
    from portal_api.routes import applications as routes
    monkeypatch.setattr(routes, "form_drafts", lambda form: [DraftEntry("cover-sheet.v1.yaml", "deed_book")])


def lookup_property(client, map_lot="004-036"):
    return {"source": "lookup", "parcel_id": _id(client, map_lot)}


def create(client, form_key="use_permit", prop=None, **extra):
    r = client.post("/api/applications", json={"form_key": form_key,
                                              "property": prop or lookup_property(client), **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def get(client, app_id):
    r = client.get(f"/api/applications/{app_id}")
    assert r.status_code == 200, r.text
    return r.json()


def save(client, app_id, changes, base=None):
    base = get(client, app_id)["revision"] if base is None else base
    return client.put(f"/api/applications/{app_id}/answers", json={"base_revision": base, "changes": changes})


def current_values(body):
    return {(a["field_id"], a["item_id"]): a["value"] for a in body["answers"]}


def test_forms_endpoint_includes_code_text(alice):
    form = alice.get("/api/forms/use_permit").json()
    assert form["key"] == "use_permit" and form["version"] == 1
    fields = {f["id"]: f for s in form["sections"] for f in s["fields"]}
    assert fields["proposed_uses"]["why"]["cite"] == "8.15.b.1"
    assert "new Use or a change of Use" in fields["proposed_uses"]["why"]["text"]
    assert alice.get("/api/forms/no_such_form").status_code == 404


def test_create_requires_sign_in(app):
    with TestClient(app) as c:
        r = c.post("/api/applications", json={"form_key": "use_permit", "property": {"source": "manual", "map_lot": "4-36"}})
    assert r.status_code == 401


def test_create_from_lookup_snapshots_server_facts(alice, engine):
    prop = lookup_property(alice)
    prop["map_lot"] = "999-999"  # what a tampered browser might send; ignored
    app_id = create(alice, prop=prop)
    body = get(alice, app_id)
    assert body["property"]["map_lot"] == "004-036"
    assert body["property"]["verified"] is True
    assert body["property"]["facts"]["streets"][0]["name"] == "Sheepscot Road"
    assert "geometry" not in body["property"]["facts"]
    with engine.begin() as conn:
        assert conn.execute(text("SELECT parcels_as_of FROM property_snapshot")).scalar().isoformat() == "2012-04-01"


def test_manual_property_is_not_verified(alice):
    app_id = create(alice, form_key="entrance_permit",
                    prop={"source": "manual", "map_lot": "4-36", "district_code": None})
    body = get(alice, app_id)
    assert body["property"]["verified"] is False and body["property"]["source"] == "manual"
    missing = {m["field_id"] for m in body["missing"]}
    assert "mainedot_permit" in missing  # the road is unknown, so the MaineDOT question is asked
    assert "street_address" in missing and "lot_area" in missing


def test_manual_district_must_be_adopted(alice):
    r = alice.post("/api/applications", json={"form_key": "use_permit",
                                              "property": {"source": "manual", "map_lot": "4-36", "district_code": "D9"}})
    assert r.status_code == 422


def test_create_refused_while_form_has_drafts(engine, settings, outbox, layers, one_form_draft):  # noqa: F811
    settings.allow_stale_parcels = True  # production defaults otherwise: drafts are refused
    with TestClient(create_app(settings, outbox)) as c:
        _sign_in(c, outbox, "alice@example.com")
        assert c.get("/api/forms/use_permit").json() == {"detail": "form_not_approved"}
        r = c.post("/api/applications", json={"form_key": "use_permit", "property": lookup_property(c)})
    assert r.status_code == 503 and r.json() == {"detail": "form_not_approved"}


def test_answers_round_trip_and_history_is_kept(alice, engine):
    app_id = create(alice)
    assert save(alice, app_id, [{"field_id": "applicant_name", "item_id": None, "value": "Ada"}]).status_code == 200
    r = save(alice, app_id, [{"field_id": "applicant_name", "item_id": None, "value": "Ada Lovelace"}])
    assert r.status_code == 200 and r.json()["revision"] == 2
    assert current_values(get(alice, app_id))[("applicant_name", None)] == "Ada Lovelace"
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM answer WHERE field_id = 'applicant_name'")).scalar() == 2


def test_bad_change_saves_nothing(alice):
    app_id = create(alice)
    r = save(alice, app_id, [{"field_id": "applicant_name", "item_id": None, "value": "Ada"},
                             {"field_id": "existing_dwelling_units", "item_id": None, "value": -3}])
    assert r.status_code == 422
    assert r.json()["detail"] == [{"field_id": "existing_dwelling_units", "item_id": None, "reason": "out_of_range"}]
    body = get(alice, app_id)
    assert ("applicant_name", None) not in current_values(body) and body["revision"] == 0


def test_stale_revision_is_refused(alice):
    app_id = create(alice)
    assert save(alice, app_id, [{"field_id": "applicant_name", "item_id": None, "value": "Tab one"}], base=0).status_code == 200
    r = save(alice, app_id, [{"field_id": "applicant_name", "item_id": None, "value": "Tab two"}], base=0)
    assert r.status_code == 409 and r.json() == {"detail": "changed_elsewhere", "revision": 1}
    assert current_values(get(alice, app_id))[("applicant_name", None)] == "Tab one"


def test_item_answers_need_a_live_item(alice):
    app_id = create(alice, form_key="small_project_plan")
    body = get(alice, app_id)
    (building,) = [i for i in body["items"] if i["kind"] == "building"]
    ok = save(alice, app_id, [{"field_id": "stories", "item_id": building["id"], "value": 2}])
    assert ok.status_code == 200
    bad = save(alice, app_id, [{"field_id": "stories", "item_id": None, "value": 2}])
    assert bad.json()["detail"][0]["reason"] == "wrong_item"
    bad = save(alice, app_id, [{"field_id": "applicant_name", "item_id": building["id"], "value": "x"}])
    assert bad.json()["detail"][0]["reason"] == "wrong_item"


def test_items_add_and_remove_respect_min(alice):
    app_id = create(alice, form_key="small_project_plan")
    body = get(alice, app_id)
    (first,) = body["items"]
    r = alice.post(f"/api/applications/{app_id}/items", json={"kind": "building", "base_revision": body["revision"]})
    assert r.status_code == 201
    second, rev = r.json()["id"], r.json()["revision"]
    assert alice.post(f"/api/applications/{app_id}/items", json={"kind": "moat", "base_revision": rev}).status_code == 422
    r = alice.request("DELETE", f"/api/applications/{app_id}/items/{second}", json={"base_revision": rev})
    assert r.status_code == 200
    r = alice.request("DELETE", f"/api/applications/{app_id}/items/{first['id']}", json={"base_revision": r.json()["revision"]})
    assert r.status_code == 422 and r.json()["detail"] == "at_least_one"
    assert [i["id"] for i in get(alice, app_id)["items"]] == [first["id"]]


def test_notes_round_trip(alice):
    app_id = create(alice)
    r = alice.put(f"/api/applications/{app_id}/notes",
                  json={"base_revision": 0, "section_id": "proposed", "item_id": None, "text": "Weekends only."})
    assert r.status_code == 200
    assert get(alice, app_id)["notes"] == [{"section_id": "proposed", "item_id": None, "text": "Weekends only."}]
    r = alice.put(f"/api/applications/{app_id}/notes",
                  json={"base_revision": 1, "section_id": "nowhere", "item_id": None, "text": "x"})
    assert r.status_code == 422


def test_list_shows_only_mine(alice, bob):
    create(alice)
    assert [a["form_key"] for a in alice.get("/api/applications").json()] == ["use_permit"]
    assert alice.get("/api/applications").json()[0]["map_lot"] == "004-036"
    assert bob.get("/api/applications").json() == []


def test_other_applicant_gets_404_everywhere(alice, bob):
    app_id = create(alice, form_key="small_project_plan")
    item = get(alice, app_id)["items"][0]["id"]
    for method, url, body in [
        ("GET", f"/api/applications/{app_id}", None),
        ("PUT", f"/api/applications/{app_id}/answers", {"base_revision": 0, "changes": []}),
        ("POST", f"/api/applications/{app_id}/items", {"kind": "building", "base_revision": 0}),
        ("DELETE", f"/api/applications/{app_id}/items/{item}", {"base_revision": 0}),
        ("PUT", f"/api/applications/{app_id}/notes", {"base_revision": 0, "section_id": "project", "item_id": None, "text": "x"}),
        ("GET", "/api/applications/not-a-uuid", None),
    ]:
        assert bob.request(method, url, json=body).status_code == 404, (method, url)


def test_events_name_fields_not_values(alice, engine):
    app_id = create(alice)
    save(alice, app_id, [{"field_id": "applicant_phone", "item_id": None, "value": "207-555-0199"}])
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT kind, payload_json FROM event WHERE kind LIKE 'application.%' ORDER BY seq")).all()
    assert [r.kind for r in rows] == ["application.created", "application.answers_saved"]
    assert "applicant_phone" in rows[1].payload_json and "555" not in rows[1].payload_json


def test_use_key_prefills_uses_to_be_established(alice):
    app_id = create(alice, use_key="health_fitness_studio")
    assert current_values(get(alice, app_id))[("proposed_uses", None)] == ["health_fitness_studio"]
    r = alice.post("/api/applications", json={"form_key": "use_permit", "property": lookup_property(alice),
                                              "use_key": "castle"})
    assert r.status_code == 422


def test_application_keeps_its_form_version(alice, tmp_path, monkeypatch):
    forms_dir = tmp_path / "forms"
    shutil.copytree(formdefs.DIR, forms_dir)
    monkeypatch.setattr(formdefs, "DIR", forms_dir)
    app_id = create(alice)
    v2 = yaml.safe_load((forms_dir / "use-permit.v1.yaml").read_text())
    v2["version"] = 2
    v2["sections"] = [s for s in v2["sections"] if s["id"] != "use_documents_section"]
    (forms_dir / "use-permit.v2.yaml").write_text(yaml.safe_dump(v2))
    body = get(alice, app_id)
    assert body["form_version"] == 1 and body["newer_version"] is True
    form = alice.get("/api/forms/use_permit/v/1").json()
    assert "use_documents_section" in [s["id"] for s in form["sections"]]
    assert alice.get("/api/forms/use_permit").json()["version"] == 2


def test_private_responses_are_never_cached(alice):
    # Shared computers (the library, the Town Office): applicants' records must not sit in a
    # browser cache, and a cached copy must never stand in for the latest answers.
    app_id = create(alice)
    for url in (f"/api/applications/{app_id}", "/api/applications", "/api/me"):
        assert alice.get(url).headers.get("cache-control") == "no-store", url
