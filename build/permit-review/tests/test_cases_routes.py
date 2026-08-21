"""Tests app/routes/cases.py — the HTTP layer over app/cases.py — against
CONTRACT.md §6's envelope and the W3 task brief's five endpoints:

    POST   /api/cases
    GET    /api/cases
    GET    /api/cases/{id}
    PATCH  /api/cases/{id}/dates
    POST   /api/cases/{id}/status

Deliberately does NOT go through app.main:create_app() (that module's own
lifespan owns its own DB_PATH resolution and is out of this task's scope);
instead this mounts app.routes.cases:router on a bare FastAPI app and
monkeypatches the router module's DB_PATH to a throwaway temp-dir SQLite
file, migrated and seeded exactly like tests/test_cases.py's `conn` fixture.
Offline, no network, no LLM, no PII.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db, security  # noqa: E402
from app.routes import cases as cases_routes  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "permit-review.db"
    conn = db.connect(db_path)
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    conn.close()

    monkeypatch.setattr(cases_routes, "DB_PATH", db_path)

    app = FastAPI()
    app.include_router(cases_routes.router)
    with TestClient(app) as c:
        yield c


def _create(client, **overrides) -> dict:
    body = dict(application_type="subdivision", map_lot="M003, L059",
                situs_address="White Rd", applicant_name="Shattuck")
    body.update(overrides)
    resp = client.post("/api/cases", json=body)
    return resp


def test_create_case_envelope_and_defaults(client):
    resp = _create(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["status"] == "intake"
    assert body["data"]["label"] == "M003, L059 (White Rd, Shattuck)"


def test_create_case_validation_failure_envelope(client):
    resp = client.post("/api/cases", json={"application_type": "bogus"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert body["error"] == "validation_failed"
    assert body["details"][0]["field"] == "application_type"


def test_create_case_non_binding_ruleset_refused(client):
    resp = _create(client, ruleset_key="draft-x")
    assert resp.status_code == 403
    assert resp.json()["error"] == "non_binding_ruleset"


def test_create_case_non_binding_ruleset_accepted_with_override(client):
    resp = _create(client, ruleset_key="draft-x", binding_override=True,
                    override_reason="Board pre-authorized dry run")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["binding_override"] is True


def test_create_case_unknown_ruleset(client):
    resp = _create(client, ruleset_key="nope")
    assert resp.status_code == 404
    assert resp.json()["error"] == "unknown_ruleset"


def test_get_case_not_found(client):
    resp = client.get("/api/cases/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


def test_get_case_includes_dates_and_history(client):
    case_id = _create(client).json()["data"]["id"]
    client.patch(f"/api/cases/{case_id}/dates",
                 json={"dates": [{"kind": "application_received", "occurred_on": "2025-10-02"}],
                       "why": "intake"})
    resp = client.get(f"/api/cases/{case_id}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["case"]["id"] == case_id
    assert len(data["dates"]) == 1
    assert [e["kind"] for e in data["history"]] == ["case.created", "case.dates_recorded"]


def test_list_cases_filters(client):
    _create(client, map_lot="A")
    _create(client, map_lot="B", ruleset_key="draft-x", is_scratch=True)
    resp = client.get("/api/cases", params={"is_scratch": "true"})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["count"] == 1
    assert body["cases"][0]["map_lot"] == "B"


def test_status_transition_valid(client):
    case_id = _create(client).json()["data"]["id"]
    resp = client.post(f"/api/cases/{case_id}/status", json={"to_status": "extracting", "why": "starting review"})
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "extracting"


def test_status_transition_invalid_returns_409(client):
    case_id = _create(client).json()["data"]["id"]
    resp = client.post(f"/api/cases/{case_id}/status", json={"to_status": "closed", "why": "skip ahead"})
    assert resp.status_code == 409
    body = resp.json()
    assert body["error"] == "invalid_transition"
    assert body["details"][0]["allowed"] == ["extracting", "withdrawn"]


def test_status_transition_missing_why_is_validation_error(client):
    case_id = _create(client).json()["data"]["id"]
    resp = client.post(f"/api/cases/{case_id}/status", json={"to_status": "extracting"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_failed"


def test_status_transition_on_unknown_case_404(client):
    resp = client.post("/api/cases/nope/status", json={"to_status": "extracting", "why": "x"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


def test_record_dates_hearing_opened_then_closed(client):
    case_id = _create(client).json()["data"]["id"]
    r1 = client.patch(f"/api/cases/{case_id}/dates",
                       json={"dates": [{"kind": "hearing_opened", "occurred_on": "2025-11-20"}],
                             "why": "hearing opened"})
    assert r1.status_code == 200
    r2 = client.patch(f"/api/cases/{case_id}/dates",
                       json={"dates": [{"kind": "hearing_closed", "occurred_on": "2025-12-18"}],
                             "why": "hearing closed"})
    assert r2.status_code == 200

    resp = client.get(f"/api/cases/{case_id}")
    kinds = {d["kind"]: d["occurred_on"] for d in resp.json()["data"]["dates"]}
    assert kinds["hearing_opened"] == "2025-11-20"
    assert kinds["hearing_closed"] == "2025-12-18"


def test_record_dates_on_unknown_case_404(client):
    resp = client.patch("/api/cases/nope/dates",
                         json={"dates": [{"kind": "meeting", "occurred_on": "2026-01-01"}], "why": "x"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


def test_record_dates_validation_error(client):
    case_id = _create(client).json()["data"]["id"]
    resp = client.patch(f"/api/cases/{case_id}/dates", json={"dates": [], "why": "x"})
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_failed"


def test_record_dates_supersede_requires_an_explicit_reason(client):
    """N3, over HTTP: supersedes_id without supersede_reason is a
    validation_failed 400, not a silent guess (CONTRACT.md §1 S7)."""
    case_id = _create(client).json()["data"]["id"]
    seed = client.patch(f"/api/cases/{case_id}/dates",
                         json={"dates": [{"kind": "notice_mailed", "occurred_on": "2025-10-09"}],
                               "why": "seed"})
    original_id = seed.json()["data"]["recorded"][0]["id"]

    missing = client.patch(
        f"/api/cases/{case_id}/dates",
        json={"dates": [{"kind": "notice_mailed", "occurred_on": "2025-11-04",
                          "supersedes_id": original_id}],
              "why": "no reason given"},
    )
    assert missing.status_code == 400
    assert missing.json()["error"] == "validation_failed"
    assert any(d["field"] == "dates[0].supersede_reason" for d in missing.json()["details"])

    ok = client.patch(
        f"/api/cases/{case_id}/dates",
        json={"dates": [{"kind": "notice_mailed", "occurred_on": "2025-11-04",
                          "supersedes_id": original_id, "supersede_reason": "reschedule"}],
              "why": "reschedule"},
    )
    assert ok.status_code == 200
