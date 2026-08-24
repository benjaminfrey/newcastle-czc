"""Tests POST /api/cases/{id}/findings/adopt (app/routes/cases.py, W7:
"the adopted final + downstream clocks") -- the visible, in-app action that
produces the adopted final, as opposed to a shell script an operator has to
find. Same harness shape as tests/test_findings_render_route.py.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import db, meeting, security  # noqa: E402
from app.routes import cases as cases_routes  # noqa: E402
from render import case_findings as cf  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
EXPORTS_DIR = APP_ROOT / "data" / "exports"
ACTOR = security.SYNTHETIC_USER_ID

HAVE_PANDOC = subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0
HAVE_TYPST = subprocess.run(["which", "typst"], capture_output=True).returncode == 0
requires_toolchain = pytest.mark.skipif(
    not (HAVE_PANDOC and HAVE_TYPST), reason="pandoc and/or typst not on PATH"
)


@pytest.fixture()
def db_path(tmp_path: Path):
    p = tmp_path / "permit-review.db"
    conn = db.connect(p)
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    conn.close()
    return p


@pytest.fixture()
def client(db_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cases_routes, "DB_PATH", db_path)
    app = FastAPI()
    app.include_router(cases_routes.router)
    with TestClient(app) as c:
        yield c


def _create_case(client) -> str:
    resp = client.post("/api/cases", json=dict(
        application_type="subdivision", map_lot="M003, L059",
        situs_address="White Rd", applicant_name="Test Fixture Applicant",
    ))
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _seed_board_and_adopt(db_path: Path, case_id: str) -> None:
    """Drives app.meeting directly against the SAME on-disk db the route
    reads (a second sqlite3 connection to the same WAL file -- the normal
    way an operator's HTTP request and a background/CLI write path share a
    database), producing a genuinely adopted case."""
    conn = db.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users (id, display_name, role, created_at) VALUES "
            "('u_chair2', 'Board Chair (fictional test fixture)', 'chair', '2026-08-20T00:00:00.000Z'), "
            "('u_member2', 'Board Member (fictional test fixture)', 'board_member', '2026-08-20T00:00:00.000Z');"
        )
        conn.execute(
            "INSERT INTO board_members (id, user_id, is_chair, term_start, created_at) VALUES "
            "('bm_chair2', 'u_chair2', 1, '2026-01-01', '2026-08-20T00:00:00.000Z'), "
            "('bm_member2', 'u_member2', 0, '2026-01-01', '2026-08-20T00:00:00.000Z');"
        )
        ruleset_id = conn.execute("SELECT ruleset_id FROM cases WHERE id = ?;", (case_id,)).fetchone()["ruleset_id"]

        m = meeting.create_motion(
            conn, case_id=case_id, kind="findings", text=cf.ADOPTION_MOTION_TEXT, actor_user_id=ACTOR,
        )
        meeting.record_vote(
            conn, motion_id=m["id"], moved_by="bm_member2", seconded_by="bm_chair2",
            votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
            recorded_by=ACTOR, voted_at="2025-12-18T18:30:00.000Z", actor_user_id=ACTOR,
        )
        decision_motion = meeting.create_motion(
            conn, case_id=case_id, kind="decision",
            text="To approve, with conditions, the subdivision application as discussed and amended.",
            actor_user_id=ACTOR,
        )
        meeting.record_vote(
            conn, motion_id=decision_motion["id"], moved_by="bm_chair2", seconded_by="bm_member2",
            votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
            recorded_by=ACTOR, voted_at="2025-12-18T18:35:00.000Z", actor_user_id=ACTOR,
        )
        meeting.record_outcome(
            conn, case_id=case_id, ruleset_id=ruleset_id, outcome="approved_with_conditions",
            recorded_by=ACTOR, motion_id=decision_motion["id"], decided_at="2025-12-18",
            meeting_date="2025-12-18", summary="Approved with conditions (fictional test fixture).",
            actor_user_id=ACTOR,
        )
    finally:
        conn.close()


def _cleanup_rendered_files(before: set[str]) -> None:
    if not EXPORTS_DIR.exists():
        return
    for pattern in ("*-findings-final.pdf", "*-findings-final.md", "*-findings-final.snapshot.json"):
        for p in EXPORTS_DIR.glob(pattern):
            if p.name not in before:
                p.unlink()


def _existing_final_files() -> set[str]:
    if not EXPORTS_DIR.exists():
        return set()
    names: set[str] = set()
    for pattern in ("*-findings-final.pdf", "*-findings-final.md", "*-findings-final.snapshot.json"):
        names |= {p.name for p in EXPORTS_DIR.glob(pattern)}
    return names


@requires_toolchain
def test_adopt_unknown_case_404(client):
    resp = client.post("/api/cases/not-a-real-id/findings/adopt")
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


@requires_toolchain
def test_adopt_refuses_409_before_any_adoption_vote(client):
    case_id = _create_case(client)
    resp = client.post(f"/api/cases/{case_id}/findings/adopt")
    assert resp.status_code == 409
    assert resp.json()["error"] == "not_adopted"


@requires_toolchain
def test_adopt_produces_adopted_final_and_emits_downstream_clocks(client, db_path):
    case_id = _create_case(client)
    _seed_board_and_adopt(db_path, case_id)

    before = _existing_final_files()
    try:
        resp = client.post(f"/api/cases/{case_id}/findings/adopt")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["path"].startswith("data/exports/")
        assert data["bytes"] > 0
        assert data["pdf_sha256"]
        assert data["content_sha256"]
        assert data["snapshot_path"].endswith(".snapshot.json")
        assert data["milestones_recorded"] == ["decision_issued"]

        clocks = {c["clock_key"]: c for c in data["downstream_clocks"]}
        assert data["downstream_clocks_error"] is None
        assert clocks["decision_filed_with_clerk"]["start_date"] == "2025-12-18"
        # 5 BUSINESS days after 2025-12-18 (Thu), skipping Christmas Day
        # (2025-12-25, a Maine legal holiday) -> 2025-12-26.
        assert clocks["decision_filed_with_clerk"]["due_date"] == "2025-12-26"
        # The appeal window has not started -- no decision_filed milestone
        # recorded yet (only decision_issued).
        assert clocks["administrative_appeal"]["due_date"] is None

        # Verify the generated_documents row itself carries both hashes.
        conn = db.connect(db_path)
        try:
            row = conn.execute(
                "SELECT * FROM generated_documents WHERE id = ?;", (data["id"],)
            ).fetchone()
            assert row["kind"] == "findings_final"
            assert row["content_sha256"] == data["content_sha256"]
            assert row["snapshot_rel_path"] == data["snapshot_path"]
        finally:
            conn.close()

        # A second call is idempotent about the milestone (no duplicate
        # decision_issued row) and still succeeds.
        resp2 = client.post(f"/api/cases/{case_id}/findings/adopt")
        assert resp2.status_code == 200
        assert resp2.json()["data"]["milestones_recorded"] == []
    finally:
        after = _existing_final_files()
        _cleanup_rendered_files(before)
        # belt-and-suspenders: also remove anything left from the 2nd call
        for name in after - before:
            p = EXPORTS_DIR / name
            p.unlink(missing_ok=True)
