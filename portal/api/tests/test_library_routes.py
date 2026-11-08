"""Staff, the records and the review API (library plan 1, task 5)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from portal_api.library import load_library
from portal_api.library.__main__ import main as cli
from tests.test_auth import _sign_in
from tests.test_guide_routes import STORIES, front, started, walk
from tests.test_projects import alice, app, bob, create, get  # noqa: F401  (fixtures)
from tests.test_property import layers  # noqa: F401  (fixture)

ROUTES = [("get", "/api/library/batches", None), ("get", "/api/library/batches/guide", None),
          ("get", "/api/library/entries/setbacks/preview?district=d1", None),
          ("post", "/api/library/entries/setbacks/decision", {"version": 1, "action": "approve"}),
          ("post", "/api/library/entries/setbacks/pull", {"version": 1, "why": "test"})]


def _make_staff(engine, email):
    with engine.begin() as conn:
        conn.execute(text("UPDATE applicant SET role = 'staff' WHERE email = :e"), {"e": email})


@pytest.fixture
def staff(app, outbox, engine):
    with TestClient(app) as c:
        _sign_in(c, outbox, "ceo@example.com")
        _make_staff(engine, "ceo@example.com")
        yield c


def _count(engine, table):
    with engine.begin() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table}")).scalar()


def test_residents_cannot_reach_the_library(app, alice, engine):
    with TestClient(app) as anon:
        for method, url, body in ROUTES:
            assert getattr(alice, method)(url, **({"json": body} if body else {})).status_code == 403, url
            assert alice.get(url).json().get("detail") in ("staff_only", "Method Not Allowed"), url
            assert getattr(anon, method)(url, **({"json": body} if body else {})).status_code == 401, url
    assert _count(engine, "library_decision") == 0 and _count(engine, "library_pull") == 0


def test_role_cli_sets_and_reports(staff, engine, monkeypatch, capsys):
    monkeypatch.setenv("PORTAL_DATABASE_URL", str(engine.url.render_as_string(hide_password=False)))
    assert cli(["role", "CEO@example.com", "admin"]) == 0
    assert capsys.readouterr().out.strip() == "CEO@example.com: staff -> admin"
    assert cli(["role", "nobody@example.com", "staff"]) == 1


def test_batches_count_by_status(staff):
    rows = staff.get("/api/library/batches").json()
    guide = next(r for r in rows if r["batch"] == "guide")
    assert (guide["total"], guide["approved"], guide["draft"], guide["pending"]) == (4, 4, 0, 0)


def test_a_batch_shows_each_entry_with_its_code(staff):
    b = staff.get("/api/library/batches/guide").json()
    e = next(x for x in b["entries"] if x["entry"]["id"] == "setbacks")
    assert e["code"][0]["cite"] == "2.3.c.3" and e["code"][0]["text"]
    assert e["entry"]["approved_on"] == "2026-11-06" and e["pending"] is None and e["pulled"] is None
    assert staff.get("/api/library/batches/nope").status_code == 404


def test_a_decision_is_pending_until_exported(staff):
    r = staff.post("/api/library/entries/setbacks/decision", json={"version": 1, "action": "approve"})
    assert r.status_code == 201
    e = next(x for x in staff.get("/api/library/batches/guide").json()["entries"] if x["entry"]["id"] == "setbacks")
    assert e["pending"]["action"] == "approve" and e["pending"]["decided_by_email"] == "ceo@example.com"
    assert next(r for r in staff.get("/api/library/batches").json() if r["batch"] == "guide")["pending"] == 1


def test_a_stale_version_is_refused(staff):
    r = staff.post("/api/library/entries/setbacks/decision", json={"version": 2, "action": "approve"})
    assert (r.status_code, r.json()["detail"]) == (409, "stale")
    assert staff.post("/api/library/entries/setbacks/pull", json={"version": 9, "why": "x"}).status_code == 409


def test_send_back_needs_a_note_and_edit_needs_its_texts(staff):
    url = "/api/library/entries/setbacks/decision"
    assert staff.post(url, json={"version": 1, "action": "send_back", "note": "  "}).json()["detail"] == "needs_note"
    assert staff.post(url, json={"version": 1, "action": "edit", "body": {"answer": "x"}}).json()["detail"] == "needs_body"
    assert staff.post(url, json={"version": 1, "action": "shred"}).json()["detail"] == "bad_action"
    texts = {"overline": "o", "answer": "a", "detail": "d", "why": "w"}
    assert staff.post(url, json={"version": 1, "action": "edit", "body": texts}).status_code == 201


def test_a_pull_hides_the_entry_at_once(staff, alice):
    pid = started(alice)
    walk(alice, pid, [("lot", "yes"), ("confirm", "yes")])
    front(alice, pid)
    assert alice.get(f"/api/projects/{pid}/guide").json()["current"]["why"]["id"] == "how_stories_count"
    r = staff.post("/api/library/entries/how_stories_count/pull", json={"version": 1, "why": "Checking a word"})
    assert r.status_code == 201
    assert alice.get(f"/api/projects/{pid}/guide").json()["current"]["why"] is None
    assert load_library().entries["how_stories_count"].status == "approved"   # the files change only by commit


def test_preview_fills_the_district(staff):
    r = staff.get("/api/library/entries/setbacks/preview?district=d1").json()
    assert r["answer"] == load_library().entries["setbacks"].answer and r["governs"]
    assert staff.get("/api/library/entries/nope/preview?district=d1").status_code == 404


def test_the_record_round_trip(staff, engine, monkeypatch, capsys, lib, tmp_path):
    """decisions (VM) -> apply --emit (VM) -> unpack (Mac) -> mark-exported (VM)."""
    import json

    from portal_api.library import unpack
    monkeypatch.setenv("PORTAL_DATABASE_URL", str(engine.url.render_as_string(hide_password=False)))
    root = lib("guide", lambda d: None)
    staff.post("/api/library/entries/use_table/decision", json={"version": 1, "action": "send_back", "note": "Name it."})
    staff.post("/api/library/entries/setbacks/pull", json={"version": 1, "why": "Checking"})
    assert cli(["decisions"]) == 0
    decided = tmp_path / "decided.json"
    decided.write_text(capsys.readouterr().out)
    assert {d["entry_id"] for d in json.loads(decided.read_text())["decisions"]} == {"use_table"}

    assert cli(["apply", str(decided), "--root", str(root), "--chair", "chair@example.com",
                "--person", "ceo@example.com=the Code Enforcement Officer", "--emit"]) == 0
    result = tmp_path / "result.json"
    result.write_text(capsys.readouterr().out)
    out = tmp_path / "out"
    out.mkdir()
    assert unpack.main([str(result), str(out)]) == ["guide.yaml"]
    assert "status: pulled" in (out / "guide.yaml").read_text()

    assert cli(["mark-exported", str(result)]) == 0
    capsys.readouterr()
    assert cli(["decisions"]) == 0
    assert json.loads(capsys.readouterr().out) == {"decisions": [], "superseded": [], "pulls": []}


def test_a_batch_lists_the_districts_and_their_buildings(staff):
    ds = staff.get("/api/library/batches/guide").json()["districts"]
    d1 = next(d for d in ds if d["key"] == "d1")
    assert (d1["code"], d1["name"]) == ("D1", "D1 - Rural") and "Residential" in d1["buildings"]
    assert next(d for d in ds if d["key"] == "sd-conserve")["buildings"] == []


def test_approving_right_after_an_edit_approves_the_edited_text(staff):
    url = "/api/library/entries/setbacks/decision"
    texts = {"overline": "o", "answer": "The edited answer.", "detail": "d", "why": "w"}
    staff.post(url, json={"version": 1, "action": "edit", "body": texts})
    staff.post(url, json={"version": 1, "action": "approve"})
    e = next(x for x in staff.get("/api/library/batches/guide").json()["entries"] if x["entry"]["id"] == "setbacks")
    assert e["pending"]["action"] == "approve" and e["pending"]["body"] == texts
