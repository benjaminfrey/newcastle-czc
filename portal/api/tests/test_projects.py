"""The project routes (projects brief §5.4): every behaviour of the application routes they
replace, plus parts, the forms they pin, sending, and the lock."""

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
    settings.allow_test_lock = True
    return create_app(settings, outbox)


@pytest.fixture
def alice(app, outbox):
    with TestClient(app) as c:
        _sign_in(c, outbox, "alice@example.com")
        c.put("/api/me", json={"name": "Alice Abbott", "phone": "207-555-0100", "mailing_address": "PO Box 1"})
        yield c


@pytest.fixture
def bob(app, outbox):
    with TestClient(app) as c:
        _sign_in(c, outbox, "bob@example.com")
        yield c


@pytest.fixture
def one_form_draft(monkeypatch):
    """Make every form look as if one entry were a draft (the guard must hold after approval)."""
    from portal_api.routes import forms, projects
    fake = lambda form: [DraftEntry("cover-sheet.v1.yaml", "deed_book")]  # noqa: E731
    monkeypatch.setattr(forms, "form_drafts", fake)
    monkeypatch.setattr(projects, "form_drafts", fake)


def lookup_property(client, map_lot="004-036"):
    return {"source": "lookup", "parcel_id": _id(client, map_lot)}


def create(client, parts=("use",), prop=None, **extra):
    r = client.post("/api/projects", json={"parts": list(parts), "property": prop or lookup_property(client), **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def get(client, pid):
    r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 200, r.text
    return r.json()


def save(client, pid, changes, base=None):
    base = get(client, pid)["revision"] if base is None else base
    return client.put(f"/api/projects/{pid}/answers", json={"base_revision": base, "changes": changes})


def values(body):
    return {(a["field_id"], a["part_id"]): a["value"] for a in body["answers"]}


def part_ids(body, kind):
    return [p["id"] for p in body["parts"] if p["kind"] == kind]


def add_part(client, pid, kind, source=None, base=None):
    base = get(client, pid)["revision"] if base is None else base
    return client.post(f"/api/projects/{pid}/parts", json={"kind": kind, "base_revision": base, "copy_from": source})


def remove_part(client, pid, part_id, base=None):
    base = get(client, pid)["revision"] if base is None else base
    return client.request("DELETE", f"/api/projects/{pid}/parts/{part_id}", json={"base_revision": base})


# ---- Creating a project ----

def test_create_requires_sign_in(app):
    with TestClient(app) as c:
        r = c.post("/api/projects", json={"parts": ["use"], "property": {"source": "manual", "map_lot": "4-36"}})
    assert r.status_code == 401


def test_create_needs_known_parts(alice):
    prop = lookup_property(alice)
    r = alice.post("/api/projects", json={"parts": [], "property": prop})
    assert r.status_code == 422 and r.json()["detail"] == "no_parts"
    r = alice.post("/api/projects", json={"parts": ["moat"], "property": prop})
    assert r.status_code == 422 and r.json()["detail"] == "unknown_part"
    r = alice.post("/api/projects", json={"parts": ["driveway", "driveway"], "property": prop})
    assert r.status_code == 422 and r.json()["detail"] == "already_there"


def test_create_pins_the_forms_its_parts_need(alice):
    body = get(alice, create(alice, ("building", "driveway")))
    assert body["forms"] == {"cover_sheet": 1, "entrance_permit": 1, "project_questions": 1, "small_project_plan": 1}
    assert [p["kind"] for p in body["parts"]] == ["building", "driveway"]
    assert [s["id"] for s in body["form"]["steps"]] == ["your_lot", "about_you", "the_work", "building", "driveway"]
    body = get(alice, create(alice, ("divide",)))
    assert body["forms"] == {"cover_sheet": 1, "project_questions": 1}


def test_title_defaults_to_the_parts_and_the_street(alice):
    body = get(alice, create(alice, ("building", "driveway")))
    assert body["title"] == "A new building and a driveway at Sheepscot Road"
    body = get(alice, create(alice, ("use",), title="  Yoga studio  "))
    assert body["title"] == "Yoga studio"


def test_create_from_lookup_snapshots_server_facts(alice, engine):
    prop = lookup_property(alice)
    prop["map_lot"] = "999-999"  # what a tampered browser might send; ignored
    body = get(alice, create(alice, prop=prop))
    assert body["property"]["map_lot"] == "004-036" and body["property"]["verified"] is True
    assert body["property"]["facts"]["streets"][0]["name"] == "Sheepscot Road"
    assert "geometry" not in body["property"]["facts"]
    with engine.begin() as conn:
        assert conn.execute(text("SELECT parcels_as_of FROM property_snapshot")).scalar().isoformat() == "2012-04-01"


def test_manual_property_is_not_verified(alice):
    body = get(alice, create(alice, ("driveway",), prop={"source": "manual", "map_lot": "4-36", "district_code": None}))
    assert body["property"]["verified"] is False and body["property"]["source"] == "manual"
    missing = {m["field_id"] for m in body["missing"]}
    assert "mainedot_permit" in missing  # the road is unknown, so the MaineDOT question is asked
    assert "street_address" in missing and "lot_area" in missing


def test_manual_district_must_be_adopted(alice):
    r = alice.post("/api/projects", json={"parts": ["use"],
                                          "property": {"source": "manual", "map_lot": "4-36", "district_code": "D9"}})
    assert r.status_code == 422


def test_create_refused_while_forms_have_drafts(engine, settings, outbox, layers, one_form_draft):  # noqa: F811
    settings.allow_stale_parcels = True  # production defaults otherwise: drafts are refused
    with TestClient(create_app(settings, outbox)) as c:
        _sign_in(c, outbox, "alice@example.com")
        assert c.get("/api/forms/use_permit").json() == {"detail": "form_not_approved"}
        r = c.post("/api/projects", json={"parts": ["use"], "property": lookup_property(c)})
    assert r.status_code == 503 and r.json() == {"detail": "form_not_approved"}


def test_the_parts_endpoint_lists_the_tiles(alice):
    parts = alice.get("/api/parts").json()
    assert [p["id"] for p in parts] == ["building", "addition", "renovation", "site", "use", "driveway", "divide", "other"]
    assert parts[0] == {"id": "building", "label": "A new building", "step": "New buildings",
                        "icon": "building-cottage", "repeats": True}


# ---- Answers ----

def test_the_account_fills_the_applicant(alice):
    body = get(alice, create(alice))
    assert "applicant_name" not in {m["field_id"] for m in body["missing"]}
    fields = {f["id"]: f for s in body["form"]["sections"] for f in s["fields"]}
    assert fields["applicant_name"]["source"] == "account"


def test_answers_round_trip_and_history_is_kept(alice, engine):
    pid = create(alice)
    assert save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Ada"}]).status_code == 200
    r = save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Ada Lovelace"}])
    assert r.status_code == 200 and r.json()["revision"] == 2
    assert values(get(alice, pid))[("owner_name", None)] == "Ada Lovelace"
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM answer WHERE field_id = 'owner_name'")).scalar() == 2


def test_bad_change_saves_nothing(alice):
    pid = create(alice)
    r = save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Ada"},
                          {"field_id": "existing_dwelling_units", "part_id": None, "value": "lots"}])
    assert r.status_code == 422 and r.json()["detail"][0]["reason"] == "wrong_type"
    body = get(alice, pid)
    assert ("owner_name", None) not in values(body) and body["revision"] == 0


def test_stale_revision_is_refused(alice):
    pid = create(alice)
    assert save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Tab one"}], base=0).status_code == 200
    r = save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Tab two"}], base=0)
    assert r.status_code == 409 and r.json() == {"detail": "changed_elsewhere", "revision": 1}
    assert values(get(alice, pid))[("owner_name", None)] == "Tab one"


def test_work_kinds_are_worked_out_from_the_parts(alice):
    pid = create(alice, ("building", "site"))
    body = get(alice, pid)
    work = next(a for a in body["answers"] if a["field_id"] == "work_kinds")
    assert work["value"] == ["new_building", "site"] and work["derived"] is True
    r = save(alice, pid, [{"field_id": "work_kinds", "part_id": None, "value": ["renovation"]}])
    assert r.json()["detail"][0]["reason"] == "not_a_question"


def test_part_answers_need_a_live_part_of_the_right_kind(alice):
    pid = create(alice, ("building", "driveway"))
    body = get(alice, pid)
    (building,), (driveway,) = part_ids(body, "building"), part_ids(body, "driveway")
    assert save(alice, pid, [{"field_id": "stories", "part_id": building, "value": 2}]).status_code == 200
    for change in ({"field_id": "stories", "part_id": None, "value": 2},
                   {"field_id": "stories", "part_id": driveway, "value": 2},
                   {"field_id": "owner_name", "part_id": building, "value": "x"}):
        assert save(alice, pid, [change]).json()["detail"][0]["reason"] == "wrong_part"


def test_homes_question_asked_when_a_new_building_has_homes(alice):
    pid = create(alice, ("building",))
    (b1,) = part_ids(get(alice, pid), "building")
    assert "homes_last_5_years" not in {m["field_id"] for m in get(alice, pid)["missing"]}
    save(alice, pid, [{"field_id": "dwelling_units", "part_id": b1, "value": 2}])
    assert "homes_last_5_years" in {m["field_id"] for m in get(alice, pid)["missing"]}


def test_notes_round_trip(alice):
    pid = create(alice)
    r = alice.put(f"/api/projects/{pid}/notes",
                  json={"base_revision": 0, "section_id": "proposed", "part_id": None, "text": "Weekends only."})
    assert r.status_code == 200
    assert get(alice, pid)["notes"] == [{"section_id": "proposed", "part_id": None, "text": "Weekends only."}]
    r = alice.put(f"/api/projects/{pid}/notes",
                  json={"base_revision": 1, "section_id": "nowhere", "part_id": None, "text": "x"})
    assert r.status_code == 422


def test_title_renames(alice):
    pid = create(alice)
    assert alice.put(f"/api/projects/{pid}/title", json={"base_revision": 0, "title": " Studio "}).status_code == 200
    assert get(alice, pid)["title"] == "Studio"
    assert alice.put(f"/api/projects/{pid}/title", json={"base_revision": 1, "title": "   "}).status_code == 422


def test_list_shows_only_mine(alice, bob):
    pid = create(alice, ("building",))
    (row,) = alice.get("/api/projects").json()
    assert row["id"] == pid and row["map_lot"] == "004-036" and row["status"] == "draft"
    assert row["first_part"] == "building" and row["left"] > 0
    # "2 things left" counts rows (Your lot, About you, the parts), as the dashboard does, not answers.
    assert row["left"] <= len(get(alice, pid)["form"]["steps"])
    assert bob.get("/api/projects").json() == []


def test_other_applicant_gets_404_everywhere(alice, bob):
    pid = create(alice, ("building",))
    part = get(alice, pid)["parts"][0]["id"]
    for method, url, body in [
        ("GET", f"/api/projects/{pid}", None),
        ("PUT", f"/api/projects/{pid}/answers", {"base_revision": 0, "changes": []}),
        ("POST", f"/api/projects/{pid}/parts", {"kind": "building", "base_revision": 0}),
        ("DELETE", f"/api/projects/{pid}/parts/{part}", {"base_revision": 0}),
        ("PUT", f"/api/projects/{pid}/notes", {"base_revision": 0, "section_id": "project", "part_id": None, "text": "x"}),
        ("PUT", f"/api/projects/{pid}/title", {"base_revision": 0, "title": "x"}),
        ("POST", f"/api/projects/{pid}/submit", {"base_revision": 0}),
        ("POST", f"/api/projects/{pid}/lock", {"base_revision": 0}),
        ("GET", "/api/projects/not-a-uuid", None),
    ]:
        assert bob.request(method, url, json=body).status_code == 404, (method, url)


def test_events_name_fields_not_values(alice, engine):
    pid = create(alice)
    save(alice, pid, [{"field_id": "owner_phone", "part_id": None, "value": "207-555-0199"}])
    with engine.begin() as conn:
        rows = conn.execute(text("SELECT kind, payload_json FROM event WHERE kind LIKE 'project.%' ORDER BY seq")).all()
    assert [r.kind for r in rows] == ["project.created", "project.answers_saved"]
    assert "owner_phone" in rows[1].payload_json and "555" not in rows[1].payload_json


def test_project_keeps_its_form_version(alice, tmp_path, monkeypatch):
    forms_dir = tmp_path / "forms"
    shutil.copytree(formdefs.DIR, forms_dir)
    monkeypatch.setattr(formdefs, "DIR", forms_dir)
    pid = create(alice)
    v2 = yaml.safe_load((forms_dir / "use-permit.v1.yaml").read_text())
    v2["version"] = 2
    (forms_dir / "use-permit.v2.yaml").write_text(yaml.safe_dump(v2))
    assert get(alice, pid)["forms"]["use_permit"] == 1
    assert alice.get("/api/forms/use_permit").json()["version"] == 2


def test_private_responses_are_never_cached(alice):
    pid = create(alice)
    for url in (f"/api/projects/{pid}", "/api/projects", "/api/me"):
        assert alice.get(url).headers.get("cache-control") == "no-store", url


def test_no_streets_layer_means_the_road_is_unknown(alice, engine):
    with engine.begin() as conn:
        conn.execute(text("UPDATE gis_import SET active = false WHERE layer = 'streets'"))
    body = get(alice, create(alice, ("driveway",)))
    assert body["property"]["facts"]["on_state_highway"] is None
    assert "mainedot_permit" in {m["field_id"] for m in body["missing"]}


def test_forms_endpoint_includes_code_text(alice):
    form = alice.get("/api/forms/use_permit").json()
    assert form["key"] == "use_permit" and form["version"] == 1
    fields = {f["id"]: f for s in form["sections"] for f in s["fields"]}
    assert fields["proposed_uses"]["why"]["cite"] == "8.15.b.1"
    assert alice.get("/api/forms/no_such_form").status_code == 404


# ---- Parts (Review Focus 2) ----

def test_adding_and_removing_a_part_repins(alice, engine):
    pid = create(alice, ("use",))
    assert add_part(alice, pid, "driveway").status_code == 201
    body = get(alice, pid)
    assert "entrance_permit" in body["forms"] and "driveway" in [s["id"] for s in body["form"]["steps"]]
    (driveway,) = part_ids(body, "driveway")
    assert save(alice, pid, [{"field_id": "driveway_width", "part_id": None, "value": 12}]).status_code == 200
    assert remove_part(alice, pid, driveway).status_code == 200
    body = get(alice, pid)
    assert "entrance_permit" not in body["forms"]
    assert ("driveway_width", None) not in values(body)
    assert "driveway_width" not in {m["field_id"] for m in body["missing"]}
    with engine.begin() as conn:  # still in the history
        assert conn.execute(text("SELECT count(*) FROM answer WHERE field_id = 'driveway_width'")).scalar() == 1


def test_a_single_part_cannot_be_added_twice(alice):
    pid = create(alice, ("driveway",))
    r = add_part(alice, pid, "driveway")
    assert r.status_code == 422 and r.json()["detail"] == "already_there"
    assert add_part(alice, pid, "moat").json()["detail"] == "unknown_part"


def test_the_last_part_cannot_be_removed(alice):
    pid = create(alice, ("use",))
    (use,) = part_ids(get(alice, pid), "use")
    r = remove_part(alice, pid, use)
    assert r.status_code == 422 and r.json()["detail"] == "at_least_one"


def test_an_addition_walks_the_components_section(alice):
    pid = create(alice, ("addition",))
    (a1,) = part_ids(get(alice, pid), "addition")
    assert save(alice, pid, [{"field_id": "added_floor_area", "part_id": a1, "value": 300}]).status_code == 200
    assert values(get(alice, pid))[("added_floor_area", a1)] == 300


# ---- Copy Building 1 ----

def spp_fields(client):
    form = client.get("/api/forms/small_project_plan").json()
    return {f["id"]: f for s in form["sections"] for f in s["fields"]}


def building_one(client):
    pid = create(client, ("building",))
    (b1,) = part_ids(get(client, pid), "building")
    return pid, b1


def test_copy_brings_exactly_the_copies_fields(alice):
    pid, b1 = building_one(alice)
    fields = spp_fields(alice)
    changes = [{"field_id": "building_class", "part_id": b1, "value": "residential_accessory"},
               {"field_id": "mass_width", "part_id": b1, "value": 24},
               {"field_id": "roof_style", "part_id": b1, "value": fields["roof_style"]["options"][0]["value"]},
               {"field_id": "building_name", "part_id": b1, "value": "Garage"},
               {"field_id": "setback_front", "part_id": b1, "value": 30}]
    assert save(alice, pid, changes).status_code == 200
    r = add_part(alice, pid, "building", source=b1)
    assert r.status_code == 201, r.text
    b2 = r.json()["id"]
    got = values(get(alice, pid))
    copied = {f for (f, i), v in got.items() if i == b2 and v != fields[f].get("default")}
    assert copied == {"building_class", "mass_width", "roof_style"}


def test_copy_keeps_unknowns_and_skips_blanks(alice):
    pid, b1 = building_one(alice)
    fields = spp_fields(alice)
    unknowable = next(fid for fid, f in fields.items() if f.get("copies") and f["allow_unknown"])
    assert save(alice, pid, [{"field_id": unknowable, "part_id": b1, "value": {"unknown": True}}]).status_code == 200
    b2 = add_part(alice, pid, "building", source=b1).json()["id"]
    got = values(get(alice, pid))
    assert got[(unknowable, b2)] == {"unknown": True} and ("mass_depth", b2) not in got


def test_copy_from_another_project_is_404(alice):
    _, other_b1 = building_one(alice)
    pid, _ = building_one(alice)
    assert add_part(alice, pid, "building", source=other_b1).status_code == 404
    assert add_part(alice, pid, "building", source="not-a-uuid").status_code == 404


def test_copy_from_an_addition_into_buildings_is_422(alice):
    pid, _ = building_one(alice)
    a1 = add_part(alice, pid, "addition").json()["id"]
    r = add_part(alice, pid, "building", source=a1)
    assert r.status_code == 422 and r.json()["detail"] == "wrong_kind"


def test_copy_at_the_maximum_is_422_too_many(alice):
    pid, b1 = building_one(alice)
    for _ in range(19):
        assert add_part(alice, pid, "building").status_code == 201
    r = add_part(alice, pid, "building", source=b1)
    assert r.status_code == 422 and r.json()["detail"] == "too_many"


def test_copy_writes_nothing_when_refused(alice):
    pid, _ = building_one(alice)
    before = get(alice, pid)
    assert add_part(alice, pid, "building", source="00000000-0000-0000-0000-000000000000").status_code == 404
    after = get(alice, pid)
    assert after["parts"] == before["parts"] and after["answers"] == before["answers"]
    assert after["revision"] == before["revision"]


# ---- Sending and the lock (Review Focus 1) ----

def finish_use_project(client):
    """A use project with every required answer, ready to send."""
    pid = create(client, ("use",))
    for _ in range(5):
        body = get(client, pid)
        if not body["missing"]:
            return pid
        form = {f["id"]: f for s in body["form"]["sections"] for f in s["fields"]}
        changes = []
        for m in body["missing"]:
            f = form[m["field_id"]]
            v = {"text": "x", "longtext": "x", "number": 1, "yesno": True, "date": "2026-10-25",
                 "choice": f["options"][0]["value"] if f["options"] else None,
                 "multichoice": [f["options"][0]["value"]] if f["options"] else None,
                 "uses": ["health_fitness_studio"]}[f["type"]]
            changes.append({"field_id": m["field_id"], "part_id": m["part_id"], "value": v})
        assert save(client, pid, changes).status_code == 200, changes
    raise AssertionError(get(client, pid)["missing"])


def test_submit_refuses_while_anything_required_is_blank(alice):
    pid = create(alice)
    r = alice.post(f"/api/projects/{pid}/submit", json={"base_revision": 0})
    assert r.status_code == 422 and r.json()["detail"] == "incomplete" and r.json()["missing"]


def test_sent_then_edited_then_locked_then_refused(alice, engine):
    pid = finish_use_project(alice)
    rev = get(alice, pid)["revision"]
    r = alice.post(f"/api/projects/{pid}/submit", json={"base_revision": rev})
    assert r.status_code == 200 and r.json()["status"] == "submitted"
    body = get(alice, pid)
    assert body["status"] == "submitted" and body["submitted_at"]
    # Still editable after Send.
    assert save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Ada"}]).status_code == 200
    rev = get(alice, pid)["revision"]
    assert alice.post(f"/api/projects/{pid}/lock", json={"base_revision": rev - 1}).status_code == 409
    r = alice.post(f"/api/projects/{pid}/lock", json={"base_revision": rev})
    assert r.status_code == 200 and r.json()["seq"] == 1
    with engine.begin() as conn:
        snap = conn.execute(text("SELECT snapshot FROM submission WHERE project_id = :p"), {"p": pid}).scalar()
    assert {"field_id": "owner_name", "part_id": None, "value": "Ada", "derived": False} in snap["answers"]
    # Every write now answers 409 locked, and nothing is half-applied.
    rev = get(alice, pid)["revision"]
    assert save(alice, pid, [{"field_id": "owner_name", "part_id": None, "value": "Eve"}]).json() == {"detail": "locked"}
    assert add_part(alice, pid, "driveway").status_code == 409
    assert alice.put(f"/api/projects/{pid}/title", json={"base_revision": rev, "title": "x"}).status_code == 409
    assert alice.post(f"/api/projects/{pid}/submit", json={"base_revision": rev}).status_code == 409
    assert values(get(alice, pid))[("owner_name", None)] == "Ada"


def test_a_draft_cannot_be_locked(alice):
    pid = create(alice)
    r = alice.post(f"/api/projects/{pid}/lock", json={"base_revision": 0})
    assert r.status_code == 409 and r.json()["detail"] == "not_sent"


def test_the_lock_seam_is_off_by_default(engine, settings, outbox, layers):  # noqa: F811
    settings.allow_stale_parcels = True
    settings.allow_draft_rules = True
    with TestClient(create_app(settings, outbox)) as c:
        _sign_in(c, outbox, "alice@example.com")
        pid = create(c)
        assert c.post(f"/api/projects/{pid}/lock", json={"base_revision": 0}).status_code == 404


def test_the_screener_route_is_gone(alice):
    assert alice.post("/api/screener", json={"project": ["use"]}).status_code in (404, 405)


# ---- Needs on the project (Task 4) ----

def test_the_project_carries_its_needs(alice):
    body = get(alice, create(alice, ("building", "driveway")))
    building = next(p for p in body["needs"]["permits"] if p["key"] == "building_permit")
    # The building's size isn't given yet, so it may need either plan (the rules' size-unknown case).
    assert [r["name"] for r in building["reviews"]] == ["Small Project Plan", "Large Project Plan", "Structure", "Entrances"]
    assert body["needs"]["application_fees_total"] >= 30


def test_needs_are_withheld_while_any_rule_is_a_draft(alice, app, monkeypatch):
    import dataclasses

    from portal_api.forms import definitions as d
    from portal_api.routes import projects as routes
    pid = create(alice, ("driveway",))
    real = d.load_definitions

    def with_a_draft(ruleset):
        defs = real(ruleset)
        return dataclasses.replace(defs, rules=[dataclasses.replace(defs.rules[0], status="draft"), *defs.rules[1:]])

    monkeypatch.setattr(routes, "load_definitions", with_a_draft)
    app.state.settings.allow_draft_rules = False
    assert get(alice, pid)["needs"] == {"refused": "not_approved"}


def test_the_lock_records_each_review_and_starts_its_clock(alice, engine):
    pid = finish_use_project(alice)
    rev = get(alice, pid)["revision"]
    alice.post(f"/api/projects/{pid}/submit", json={"base_revision": rev})
    assert alice.post(f"/api/projects/{pid}/lock", json={"base_revision": rev + 1}).status_code == 200
    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT r.review_key, r.use_key, r.permit_key, r.reviewer, r.status, r.submitted_at = s.locked_at AS at_lock"
            " FROM review r JOIN submission s ON s.id = r.submission_id WHERE s.project_id = :p"), {"p": pid}).all()
        snap = conn.execute(text("SELECT snapshot FROM submission WHERE project_id = :p"), {"p": pid}).scalar()
    assert [(r.review_key, r.use_key, r.permit_key, r.status, r.at_lock) for r in rows] == \
        [("residential_companion", "health_fitness_studio", "use_permit", "waiting", True)]  # on this lot's district
    assert snap["needs"]["permits"][0]["key"] == "use_permit"
    clock = get(alice, pid)["needs"]["permits"][0]["reviews"][0]["clocks"][0]
    assert clock["due_words"].startswith("Decision due by ")
