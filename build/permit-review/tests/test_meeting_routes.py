"""Tests app/routes/meeting.py -- the W7 live meeting UI's HTTP layer.

Same harness shape as tests/test_findings_render_route.py: mounts
app.routes.meeting:router on a bare FastAPI app, a throwaway temp-dir
SQLite DB reached by monkeypatching app.config.DATA_DIR (app/routes/
meeting.py's own _connect() re-reads config.DATA_DIR on every call, the
same pattern app/routes/extraction.py already established -- there is no
module-level DB_PATH constant here to monkeypatch instead).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import cases as cases_mod  # noqa: E402
from app import config, db, security  # noqa: E402
from app.routes import meeting as meeting_routes  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "permit-review.db"
    conn = db.connect(db_path)
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    case = cases_mod.create_case(
        conn, application_type="subdivision", map_lot="M003, L059",
        situs_address="White Rd", applicant_name="Shattuck (fixture)",
        actor_user_id=security.SYNTHETIC_USER_ID,
    )
    conn.close()

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    app = FastAPI()
    app.include_router(meeting_routes.router)
    with TestClient(app) as c:
        c.case_id = case["id"]  # type: ignore[attr-defined]
        yield c


def test_meeting_screen_renders(client):
    resp = client.get(f"/case/{client.case_id}/meeting")
    assert resp.status_code == 200
    assert "meeting" in resp.text.lower()


def test_meeting_screen_404s_for_an_unknown_case(client):
    resp = client.get("/case/does-not-exist/meeting")
    assert resp.status_code == 404


def test_agenda_seeds_a_sitting_board_via_the_startup_seed(client):
    resp = client.get(f"/api/cases/{client.case_id}/meeting/agenda")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert len(body["data"]["board_members"]) == 7  # app/board.py's real seeded roster
    assert body["data"]["disclosures_resolved"] is False
    for d in body["data"]["disclosures"]:
        assert d["recorded"] is False
        assert d["disclosed"] is None


def test_prepare_drafts_the_completeness_motion(client):
    resp = client.post(f"/api/cases/{client.case_id}/meeting/prepare")
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["created"]["completeness"] == 1
    assert body["agenda"]["completeness_motion"] is not None
    assert body["agenda"]["completeness_motion"]["outcome"] is None


def test_full_sequence_disclosure_completeness_adoption_decision(client):
    client.post(f"/api/cases/{client.case_id}/meeting/prepare")
    agenda = client.get(f"/api/cases/{client.case_id}/meeting/agenda").json()["data"]
    board = agenda["board_members"]
    assert len(board) >= 2

    # 1. Disclosures — every sitting member.
    for m in board:
        r = client.post(
            f"/api/cases/{client.case_id}/meeting/disclosures",
            json={"board_member_id": m["board_member_id"], "disclosed": False},
        )
        assert r.status_code == 200

    agenda = client.get(f"/api/cases/{client.case_id}/meeting/agenda").json()["data"]
    assert agenda["disclosures_resolved"] is True

    # 2. Completeness — vote it carried.
    completeness = agenda["completeness_motion"]
    r = client.patch(
        f"/api/cases/{client.case_id}/meeting/motions/{completeness['id']}",
        json={
            "moved_by": board[0]["board_member_id"], "seconded_by": board[1]["board_member_id"],
            "votes_yes": 7, "votes_no": 0, "votes_abstain": 0, "outcome": "carried",
        },
    )
    assert r.status_code == 200
    assert r.json()["data"]["motion"]["outcome"] == "carried"

    # 5. Adoption — draft, then carry.
    r = client.post(f"/api/cases/{client.case_id}/meeting/motions", json={"kind": "adoption"})
    assert r.status_code == 200
    adoption = r.json()["data"]
    assert adoption["text"] == "To accept and adopt the draft findings of fact and conclusions of law, as amended."

    r = client.patch(
        f"/api/cases/{client.case_id}/meeting/motions/{adoption['id']}",
        json={
            "moved_by": board[0]["board_member_id"], "seconded_by": board[1]["board_member_id"],
            "votes_yes": 7, "votes_no": 0, "votes_abstain": 0, "outcome": "carried",
        },
    )
    assert r.status_code == 200

    # 6/7. Decision — draft "approve", then carry it; a decisions row must appear.
    r = client.post(
        f"/api/cases/{client.case_id}/meeting/motions",
        json={"kind": "decision", "disposition": "approve"},
    )
    assert r.status_code == 200
    decision_motion = r.json()["data"]
    assert decision_motion["disposition"] == "approve"

    r = client.patch(
        f"/api/cases/{client.case_id}/meeting/motions/{decision_motion['id']}",
        json={
            "moved_by": board[0]["board_member_id"], "seconded_by": board[1]["board_member_id"],
            "votes_yes": 7, "votes_no": 0, "votes_abstain": 0, "outcome": "carried",
        },
    )
    assert r.status_code == 200
    assert r.json()["data"]["decision_recorded"] is not None
    assert r.json()["data"]["decision_recorded"]["outcome"] == "approved"

    agenda = client.get(f"/api/cases/{client.case_id}/meeting/agenda").json()["data"]
    assert agenda["decision"] is not None
    assert agenda["decision"]["outcome"] == "approved"
    assert agenda["counts"]["unresolved"] == 0


def test_amend_requires_a_non_empty_why(client):
    # Seed one contested standard node directly via engine.findings, mirroring
    # what a real review-engine walk would have already produced.
    from engine import findings as findings_mod

    conn = db.connect(config.DATA_DIR / "permit-review.db")
    node = findings_mod.create_node(
        conn, case_id=client.case_id, node_type="finding", number_label="g.",
        heading="g. Traffic", board_question="Is the application consistent with Standard g?",
        actor_user_id=security.SYNTHETIC_USER_ID,
    )
    conn.close()

    r = client.post(
        f"/api/cases/{client.case_id}/meeting/nodes/{node['id']}/amend",
        json={"body": "Corrected finding text.", "why": ""},
    )
    assert r.status_code == 400
    assert r.json()["ok"] is False

    r = client.post(
        f"/api/cases/{client.case_id}/meeting/nodes/{node['id']}/amend",
        json={"body": "Corrected finding text.", "why": "Typo caught during Board discussion."},
    )
    assert r.status_code == 200
    assert r.json()["data"]["body"] == "Corrected finding text."
    assert r.json()["data"]["revision"] == 2
