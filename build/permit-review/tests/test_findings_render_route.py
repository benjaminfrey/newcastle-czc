"""Tests POST /api/cases/{id}/findings/render and
GET /api/cases/{id}/findings/documents (app/routes/cases.py, CONTRACT.md
§10.3) -- the visible, in-app action that regenerates a findings draft,
as opposed to a shell script an operator has to find.

Same harness shape as tests/test_cases_routes.py: mounts
app.routes.cases:router on a bare FastAPI app, a throwaway temp-dir SQLite
DB. The render itself still lands in the REAL data/exports/ (render/
build-findings.sh hard-refuses anywhere else, CONTRACT.md §6.3/§8.6) --
cleaned up after each test, same convention tests/test_render.py and
tests/test_case_findings.py already use.
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

from app import db, security  # noqa: E402
from app.routes import cases as cases_routes  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
EXPORTS_DIR = APP_ROOT / "data" / "exports"

HAVE_PANDOC = subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0
HAVE_TYPST = subprocess.run(["which", "typst"], capture_output=True).returncode == 0
requires_toolchain = pytest.mark.skipif(
    not (HAVE_PANDOC and HAVE_TYPST), reason="pandoc and/or typst not on PATH"
)


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


def _create_case(client) -> str:
    resp = client.post("/api/cases", json=dict(
        application_type="subdivision", map_lot="M003, L059",
        situs_address="White Rd", applicant_name="Test Fixture Applicant",
    ))
    assert resp.status_code == 200
    return resp.json()["data"]["id"]


def _cleanup_rendered_pdfs(before: set[str]) -> None:
    if not EXPORTS_DIR.exists():
        return
    for p in EXPORTS_DIR.glob("*-findings-draft.pdf"):
        if p.name not in before:
            p.unlink()


@requires_toolchain
def test_render_unknown_case_404(client):
    resp = client.post("/api/cases/not-a-real-id/findings/render")
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


@requires_toolchain
def test_render_produces_a_pdf_and_records_generated_documents(client):
    case_id = _create_case(client)
    before = {p.name for p in EXPORTS_DIR.glob("*-findings-draft.pdf")} if EXPORTS_DIR.exists() else set()
    try:
        resp = client.post(f"/api/cases/{case_id}/findings/render", json={})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["bytes"] > 0
        assert len(data["sha256"]) == 64
        assert data["path"].startswith("data/exports/")
        assert isinstance(data["unresolved"], list)

        # A real generated_documents row + events row landed (CONTRACT.md §10.3).
        conn = db.connect(cases_routes.DB_PATH)
        try:
            row = conn.execute(
                "SELECT * FROM generated_documents WHERE id = ?;", (data["id"],)
            ).fetchone()
            assert row is not None
            assert row["kind"] == "findings_draft"
            assert row["case_id"] == case_id
            assert row["rel_path"] == data["path"]
            assert row["sha256"] == data["sha256"]

            event = conn.execute(
                "SELECT * FROM events WHERE kind = 'findings.rendered' ORDER BY seq DESC LIMIT 1;"
            ).fetchone()
            assert event is not None
        finally:
            conn.close()

        # Listed back via the documents endpoint, newest first.
        list_resp = client.get(f"/api/cases/{case_id}/findings/documents")
        assert list_resp.status_code == 200
        docs = list_resp.json()["data"]["documents"]
        assert docs and docs[0]["id"] == data["id"]
        assert docs[0]["unresolved_count"] == len(data["unresolved"])
    finally:
        _cleanup_rendered_pdfs(before)


@requires_toolchain
def test_documents_endpoint_unknown_case_404(client):
    resp = client.get("/api/cases/not-a-real-id/findings/documents")
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


@requires_toolchain
def test_render_twice_produces_two_distinct_documents(client):
    case_id = _create_case(client)
    before = {p.name for p in EXPORTS_DIR.glob("*-findings-draft.pdf")} if EXPORTS_DIR.exists() else set()
    try:
        r1 = client.post(f"/api/cases/{case_id}/findings/render", json={})
        r2 = client.post(f"/api/cases/{case_id}/findings/render", json={})
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["data"]["id"] != r2.json()["data"]["id"]

        list_resp = client.get(f"/api/cases/{case_id}/findings/documents")
        assert list_resp.json()["data"]["documents"].__len__() == 2
    finally:
        _cleanup_rendered_pdfs(before)
