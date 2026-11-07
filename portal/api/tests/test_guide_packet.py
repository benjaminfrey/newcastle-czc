"""The applicant's packet (guided plan 6): one packet, built from what is stored, for both sides."""
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.guide.content import load_content
from portal_api.guide.packet import _marks, deciders_from
from portal_api.main import create_app
from portal_api.routes import guide as guide_routes
from tests.test_auth import _sign_in
from tests.test_guide_content import all_draft
from tests.test_guide_routes import STORIES, answer, front, started, walk
from tests.test_projects import alice, app, bob, create, fill_missing, finish_use_project, get  # noqa: F401  (fixtures)
from tests.test_property import layers  # noqa: F401  (fixture)

SETBACKS = [("setback_front", 30), ("setback_side_1", 30), ("setback_side_2", 30), ("setback_rear", 30)]
READY = [("lot", "yes"), ("confirm", "yes"), *STORIES, ("floor_area", 1800), ("dwelling_units", 1), *SETBACKS]


def packet(client, pid):
    return client.get(f"/api/projects/{pid}/packet")


def note(client, pid, body):
    base = client.get(f"/api/projects/{pid}/guide").json()["revision"]
    r = client.post(f"/api/projects/{pid}/guide/notes", json={"body": body, "base_revision": base})
    assert r.status_code == 201, r.text


def test_the_packet_carries_their_words_exactly(alice):
    pid = started(alice)
    body = 'Line one\n<b>Two</b> "quoted"'
    note(alice, pid, body)
    p = packet(alice, pid).json()
    assert [w["body"] for w in p["summary"]["own_words"]] == [body]


def test_the_reading_and_who_decides(alice):
    pid = started(alice)
    walk(alice, pid, READY)
    p = packet(alice, pid).json()
    assert p["finished"] is True
    assert p["summary"]["reading"].startswith("So you'd like to build a new house")
    assert "The Code Enforcement Officer decides within 10 days of accepting your project." in p["summary"]["deciders"]


def test_every_decision_sentence_in_review_order():
    clock = lambda key, plain: {"key": key, "plain": plain}  # noqa: E731
    needs = {"permits": [
        {"reviews": [{"certainty": "needed", "clocks": [clock("large_project_ceo_decision", "The CEO decides."),
                                                        clock("large_project_pb_decision", "The Board decides.")]}]},
        {"reviews": [{"certainty": "may_need", "clocks": [clock("use_permit_decision", "Maybe not.")]}]},
        {"reviews": [{"certainty": "needed", "clocks": [clock("use_permit_completeness", "Not a decision."),
                                                        clock("use_permit_decision", "The CEO decides.")]}]},
    ]}
    assert deciders_from(needs) == ["The CEO decides.", "The Board decides."]
    assert deciders_from({"refused": "not_approved"}) == []


def test_history_marks_the_moments_that_matter(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes")])
    # More stories than any district allows: whichever story question it is, it doesn't fit.
    for turn_id, value in [("full_stories", 4), ("roof_floors", 2), ("top_knee_over_3ft", "yes"),
                           ("basement_exposed_5ft", "yes")]:
        g = alice.get(f"/api/projects/{pid}/guide").json()
        if g["current"]["turn_id"].startswith("doesnt_fit:"):
            break
        assert answer(alice, pid, turn_id, value).status_code == 200
    g = alice.get(f"/api/projects/{pid}/guide").json()
    fit = g["current"]["turn_id"]
    assert fit.startswith("doesnt_fit:"), fit
    assert answer(alice, pid, fit, "keep_mine").status_code == 200
    g = alice.get(f"/api/projects/{pid}/guide").json()
    if g["current"] and g["current"]["turn_id"] != "floor_area":
        assert answer(alice, pid, g["current"]["turn_id"], "unsure").status_code == 200
    else:
        assert answer(alice, pid, "floor_area", "unsure").status_code == 200
    marks = {h["turn_id"]: h["marks"] for h in packet(alice, pid).json()["history"]}
    assert marks["confirm"] == ["confirmed"]
    assert marks[fit] == ["kept"]
    assert ["unsure"] in marks.values()
    assert marks["lot"] == []


def test_judgment_comes_first(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes"), *STORIES, ("floor_area", 1800), ("dwelling_units", "unsure"),
                      *SETBACKS])
    p = packet(alice, pid).json()
    town = {r["turn_id"] for r in p["checklist"]["town"]}
    fits = {r["turn_id"] for r in p["checklist"]["fits"]}
    assert "dwelling_units" in town and "setback_front" in fits
    assert not town & fits
    assert next(r for r in p["checklist"]["town"] if r["turn_id"] == "dwelling_units")["reason"] == "unsure"


def test_a_packet_mid_conversation_lists_the_checks_so_far(alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes"), *STORIES, ("floor_area", 1800), ("dwelling_units", 1),
                      ("setback_front", 30)])
    p = packet(alice, pid).json()
    assert p["finished"] is False
    assert "setback_front" in {r["turn_id"] for r in p["checklist"]["fits"]}
    assert p["drawing"]["outline"] is not None


def test_a_disputed_lot_is_flagged(alice):
    pid = started(alice)
    r = answer(alice, pid, "lot", "not_right")
    assert r.status_code == 200, r.text
    assert packet(alice, pid).json()["summary"]["corrections"]["lot_disputed"] is True


def test_no_conversation_is_not_started(alice):
    pid = create(alice, parts=("building",))
    r = packet(alice, pid)
    assert r.status_code == 404 and r.json()["detail"] == "not_started"


def test_someone_elses_packet_is_404(alice, bob):
    pid = started(alice)
    assert packet(bob, pid).status_code == 404


def test_the_packet_is_refused_while_its_words_are_drafts(engine, settings, outbox, layers, monkeypatch):  # noqa: F811
    settings.allow_stale_parcels = True
    settings.allow_draft_rules = True
    dev = create_app(settings, outbox)
    with TestClient(dev) as c:
        _sign_in(c, outbox, "erin@example.com")
        pid = started(c)
        dev.state.settings.allow_draft_rules = False
        monkeypatch.setattr(guide_routes, "load_content", lambda: all_draft(load_content()))
        r = packet(c, pid)
        assert r.status_code == 503 and r.json()["detail"] == "guide_not_approved"


def test_a_suggestion_taken_is_marked():
    shown = SimpleNamespace(turn_id="doesnt_fit:setback_side_1", answers=(), input=None)
    assert _marks(shown, "nearest") == ["took_suggestion"]
    assert _marks(shown, "keep_mine") == ["kept"]
    assert _marks(shown, "talk_to_town") == []



# --- Task 2: as sent ---

def send(client, pid):
    r = client.post(f"/api/projects/{pid}/submit", json={"base_revision": get(client, pid)["revision"]})
    assert r.status_code == 200, r.text


def sendable(client):
    pid = started(client, opening="change_of_use", parts=("use",))
    note(client, pid, "A yoga studio in the barn.")
    return fill_missing(client, pid)


def test_sending_keeps_the_packet_as_sent(alice):
    pid = sendable(alice)
    assert packet(alice, pid).json()["state"] == "now"
    send(alice, pid)
    p = packet(alice, pid).json()
    assert p["state"] == "sent" and p["sent_at"]


def test_the_sent_packet_does_not_follow_later_changes(alice):
    pid = sendable(alice)
    send(alice, pid)
    note(alice, pid, "One more thing.")
    words = [w["body"] for w in packet(alice, pid).json()["summary"]["own_words"]]
    assert words == ["A yoga studio in the barn."]


def test_sending_again_replaces_it(alice):
    pid = sendable(alice)
    send(alice, pid)
    note(alice, pid, "One more thing.")
    send(alice, pid)
    words = [w["body"] for w in packet(alice, pid).json()["summary"]["own_words"]]
    assert words == ["A yoga studio in the barn.", "One more thing."]


def test_a_project_sent_without_a_conversation_saves_nothing(alice, engine):
    pid = finish_use_project(alice)
    send(alice, pid)
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM guide_packet WHERE project_id = :p"), {"p": pid}).scalar() == 0
