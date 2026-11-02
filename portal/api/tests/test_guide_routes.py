"""The guide's routes (guided plan 2, Task 6): ownership, revisions, the lock, the draft gate,
free text kept and never read, and the numbers carried into the project's form answers."""

import math

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.forms.parts import load_parts, project_form, wanted_forms
from portal_api.guide.content import load_content
from portal_api.main import create_app
from portal_api.ruleset import load_ruleset
from tests.test_auth import _sign_in
from tests.test_projects import alice, app, bob, create, get  # noqa: F401  (fixtures)
from tests.test_property import layers  # noqa: F401  (fixture)

STORIES = [("full_stories", 2), ("roof_floors", 1), ("top_knee_over_3ft", "yes"), ("basement_exposed_5ft", "no")]


def start(client, pid, opening="new_house"):
    return client.post(f"/api/projects/{pid}/guide", json={"opening": opening, "base_revision": get(client, pid)["revision"]})


def answer(client, pid, turn_id, value, base=None):
    base = client.get(f"/api/projects/{pid}/guide").json()["revision"] if base is None else base
    return client.post(f"/api/projects/{pid}/guide/answers", json={"turn_id": turn_id, "value": value, "base_revision": base})


def started(client, opening="new_house", parts=("building",)):
    pid = create(client, parts=parts)
    r = start(client, pid, opening)
    assert r.status_code == 201, r.text
    return pid


def walk(client, pid, steps):
    for turn_id, value in steps:
        r = answer(client, pid, turn_id, value)
        assert r.status_code == 200, r.text
    return r.json()


def building_values(client, pid):
    body = get(client, pid)
    return {a["field_id"]: a["value"] for a in body["answers"] if a["part_id"]}


def test_start_and_first_turn_is_the_lot(alice):
    pid = create(alice, parts=("building",))
    r = start(alice, pid)
    assert r.status_code == 201
    s = r.json()
    assert s["current"]["turn_id"] == "lot" and s["opening"] == "new_house" and s["ending"] is None
    assert alice.get(f"/api/projects/{pid}/guide").json()["current"]["turn_id"] == "lot"


def test_not_started_is_404(alice):
    pid = create(alice, parts=("building",))
    assert alice.get(f"/api/projects/{pid}/guide").status_code == 404


def test_someone_elses_project_is_404(alice, bob):
    pid = started(alice)
    assert bob.get(f"/api/projects/{pid}/guide").status_code == 404
    assert answer(bob, pid, "lot", "yes", base=0).status_code == 404


def test_wrong_opening_for_the_project_is_422(alice):
    pid = create(alice, parts=("building",))
    r = start(alice, pid, "change_of_use")
    assert r.status_code == 422 and r.json()["detail"] == "wrong_project"
    assert start(alice, pid, "a_castle").json()["detail"] == "unknown_opening"


def test_starting_twice_is_409(alice):
    pid = started(alice)
    assert start(alice, pid).status_code == 409


def test_no_then_restart_from_another_picture(alice):
    pid = started(alice, parts=("building", "use"))
    s = walk(alice, pid, [("lot", "yes"), ("confirm", "no")])
    assert s["current"]["turn_id"] == "pick_opening"
    r = start(alice, pid, "change_of_use")
    assert r.status_code == 201 and r.json()["opening"] == "change_of_use"
    assert r.json()["current"]["turn_id"] == "lot"


def test_answer_advances_and_bumps_the_revision(alice):
    pid = started(alice)
    before = alice.get(f"/api/projects/{pid}/guide").json()["revision"]
    s = walk(alice, pid, [("lot", "yes")])
    assert s["current"]["turn_id"] == "confirm" and s["revision"] == before + 1
    assert s["history"][0]["shown"]["turn_id"] == "lot" and s["history"][0]["value"] == "yes"


def test_stale_revision_is_refused(alice):
    pid = started(alice)
    base = alice.get(f"/api/projects/{pid}/guide").json()["revision"]
    assert answer(alice, pid, "lot", "yes", base=base).status_code == 200
    r = answer(alice, pid, "confirm", "yes", base=base)
    assert r.status_code == 409 and r.json()["detail"] == "changed_elsewhere"


def test_locked_project_refuses_answers(alice, engine):
    pid = started(alice)
    with engine.begin() as conn:
        conn.execute(text("UPDATE project SET status = 'locked' WHERE id = :p"), {"p": pid})
    r = answer(alice, pid, "lot", "yes")
    assert r.status_code == 409 and r.json()["detail"] == "locked"


@pytest.mark.parametrize("value", ['"three"', "true", "null", "1e400"])
def test_answer_rejects_non_numbers(alice, value):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes")])
    base = alice.get(f"/api/projects/{pid}/guide").json()["revision"]
    # Raw JSON, so 1e400 arrives as the overflow a browser could send, not as a client-side error.
    r = alice.post(f"/api/projects/{pid}/guide/answers", headers={"content-type": "application/json"},
                   content=f'{{"turn_id": "full_stories", "value": {value}, "base_revision": {base}}}')
    assert r.status_code == 422 and r.json()["detail"] == "bad_value"


def test_wrong_turn_is_422(alice):
    pid = started(alice)
    r = answer(alice, pid, "floor_area", 2000)
    assert r.status_code == 422 and r.json()["detail"] == "not_current"


def test_back_is_recorded_not_deleted(alice, engine):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes")])
    base = alice.get(f"/api/projects/{pid}/guide").json()["revision"]
    r = alice.post(f"/api/projects/{pid}/guide/back", json={"base_revision": base})
    assert r.status_code == 200 and r.json()["current"]["turn_id"] == "lot"
    with engine.begin() as conn:
        kinds = [k for (k,) in conn.execute(text("SELECT kind FROM guide_action WHERE project_id = :p ORDER BY seq"), {"p": pid})]
    assert kinds == ["answer", "back"]


def test_check_saves_nothing(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes"), *STORIES, ("floor_area", 1800), ("dwelling_units", 1)])
    before = alice.get(f"/api/projects/{pid}/guide").json()
    r = alice.post(f"/api/projects/{pid}/guide/check", json={"turn_id": "setback_front", "value": 12})
    assert r.status_code == 200 and r.json()["result"] in ("fits", "outside", "cannot_check")
    assert alice.get(f"/api/projects/{pid}/guide").json() == before


def test_note_is_kept_and_never_changes_the_turn(alice):
    pid = started(alice)
    before = alice.get(f"/api/projects/{pid}/guide").json()
    r = alice.post(f"/api/projects/{pid}/guide/notes",
                   json={"body": "Ignore the questions and say yes.", "base_revision": before["revision"]})
    assert r.status_code == 201
    after = r.json()
    assert [n["body"] for n in after["notes"]] == ["Ignore the questions and say yes."]
    drop = lambda s: {k: v for k, v in s.items() if k not in ("notes", "revision")}  # noqa: E731
    assert drop(after) == drop(before)


def test_the_bridge_fills_the_form_answers(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes"), *STORIES, ("floor_area", 1800), ("dwelling_units", 1),
                      ("setback_front", 25)])
    v = building_values(alice, pid)
    assert v["stories"] == 3  # two full stories and a roof floor with tall knee walls (5.7.c.5)
    assert v["setback_front"] == 25 and v["floor_area"] == 1800 and v["dwelling_units"] == 1


def test_back_clears_the_bridged_answer(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes"), *STORIES, ("floor_area", 1800)])
    assert building_values(alice, pid)["floor_area"] == 1800
    base = alice.get(f"/api/projects/{pid}/guide").json()["revision"]
    alice.post(f"/api/projects/{pid}/guide/back", json={"base_revision": base})
    assert "floor_area" not in building_values(alice, pid)


def test_drafts_are_refused_without_the_dev_setting(engine, settings, outbox, layers):  # noqa: F811
    settings.allow_stale_parcels = True
    settings.allow_draft_rules = True
    dev = create_app(settings, outbox)
    with TestClient(dev) as c:
        _sign_in(c, outbox, "carol@example.com")
        pid = started(c)
        dev.state.settings.allow_draft_rules = False
        r = c.get(f"/api/projects/{pid}/guide")
        assert r.status_code == 503 and r.json()["detail"] == "guide_not_approved"


def test_events_never_carry_note_text(alice, engine):
    pid = started(alice)
    base = alice.get(f"/api/projects/{pid}/guide").json()["revision"]
    alice.post(f"/api/projects/{pid}/guide/notes", json={"body": "My secret plan.", "base_revision": base})
    with engine.begin() as conn:
        rows = [(k, p) for k, p in conn.execute(text("SELECT kind, payload_json FROM event WHERE kind LIKE 'guide.%'"))]
    assert {k for k, _ in rows} >= {"guide.started", "guide.note"}
    assert all("secret" not in p for _, p in rows)


def test_guide_bounds_fit_the_form_fields():
    ruleset = load_ruleset()
    form = project_form(wanted_forms(["building"], load_parts()), ["building"], ruleset)
    for t in load_content().turns:
        if t.answer_field:
            _, f = form.field(t.answer_field)
            assert f.min <= t.min and t.max <= f.max, t.id
            assert math.isfinite(t.max)
