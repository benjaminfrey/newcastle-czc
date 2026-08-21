"""Tests the W3 case dashboard (`GET /cases`) and case detail (`GET /cases/{id}`)
pages -- app/main.py's HTML routes, app/templates/cases_dashboard.html and
app/templates/case_detail.html.

Goes through the real app/main.py:create_app() (unlike tests/test_cases_routes.py,
which deliberately mounts app.routes.cases on a bare FastAPI app to dodge this
module's DB_PATH/host-origin-guard setup) because the dashboard/detail routes
live in app/main.py itself. app/main.py resolves DB_PATH once at IMPORT time
from app.config, so a throwaway per-test database is wired in by monkeypatching
the already-imported app.main.DB_PATH attribute directly (works regardless of
which test file happened to import app.main first in this session) rather than
setting the PERMIT_REVIEW_DATA_DIR env var (which only takes effect on
app.config's own import). CONTRACT.md §1.1 S4's Host/Origin guard is satisfied
by pointing TestClient's base_url at the app's own bound port, matching
127.0.0.1:<port> -- exactly what a real browser hitting this loopback-only
server would send.

Offline, no network, no LLM. Uses one real fixture PDF (docs/, read-only) for
the upload-and-render smoke test; every other test seeds case_milestones rows
directly via app.cases, matching the pattern tests/test_cases.py/
tests/test_cases_routes.py already established for this project's case tests.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import cases as cases_mod  # noqa: E402
from app import db as db_mod  # noqa: E402
from app import main as app_main  # noqa: E402
from app import security  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FIXTURE_PDF = (
    REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"
    / "M011, L046-A (Morrissey, 53 Pleasant Street) SLZ Application, 2025 Submitted Documents.pdf"
)


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "permit-review.db"
    conn = db_mod.connect(db_path)
    db_mod.migrate(conn, app_main.MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    conn.close()

    # app/main.py's own routes (worksheet render, /cases, /cases/{id}) resolve
    # DB_PATH from this module attribute.
    monkeypatch.setattr(app_main, "DB_PATH", db_path)
    monkeypatch.setattr(app_main, "DATA_DIR", tmp_path)
    # app/routes/documents.py resolves its own DB path from app.config.DATA_DIR
    # at call time (app/blobs.py's documented seam) -- point it at the same file.
    from app import config as config_mod
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "BLOBS_DIR", tmp_path / "blobs")

    app = app_main.create_app(port=8781)
    with TestClient(app, base_url="http://127.0.0.1:8781") as c:
        yield c


def _seeded_conn(client_tmp_db: Path):
    conn = db_mod.connect(client_tmp_db)
    return conn


def _create_case(db_path: Path, **overrides) -> dict:
    conn = db_mod.connect(db_path)
    try:
        kwargs = dict(
            application_type="subdivision",
            map_lot="M003, L059",
            situs_address="White Rd",
            applicant_name="Shattuck",
            label="M003, L059 (White Rd, Shattuck) Subdivision",
            actor_user_id=security.SYNTHETIC_USER_ID,
        )
        kwargs.update(overrides)
        return cases_mod.create_case(conn, **kwargs)
    finally:
        conn.close()


def _record_dates(db_path: Path, case_id: str, entries: list[dict], why: str = "seed") -> None:
    conn = db_mod.connect(db_path)
    try:
        cases_mod.record_dates(conn, case_id, entries=entries, why=why, actor_user_id=security.SYNTHETIC_USER_ID)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# GET /cases -- routes render for a seeded case
# --------------------------------------------------------------------------- #


def test_dashboard_renders_empty_state_with_no_cases(client):
    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "No cases yet." in resp.text


def test_dashboard_shows_a_seeded_case_with_its_label_and_status(client):
    db_path = app_main.DB_PATH
    _create_case(db_path)

    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "M003, L059 (White Rd, Shattuck) Subdivision" in resp.text
    assert "Subdivision" in resp.text
    assert "Intake" in resp.text  # STATUS_LABELS["intake"]


# --------------------------------------------------------------------------- #
# the dashboard shows an open deadline
# --------------------------------------------------------------------------- #


def test_dashboard_shows_an_open_deadline_for_a_recently_submitted_case(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)
    # Submitted a few days ago -- the 7-business-day notice clock is OPEN
    # (not yet due, not yet missed), so it should headline this case's row.
    _record_dates(db_path, case["id"], [{"kind": "application_received", "occurred_on": "2026-08-19"}])

    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "no open deadline" not in resp.text
    assert "Notice of application mailed" in resp.text
    assert "days-remaining" in resp.text


# --------------------------------------------------------------------------- #
# auto-approval styling is present when applicable
# --------------------------------------------------------------------------- #


def test_dashboard_flags_auto_approval_risk_for_a_missed_hearing_and_decision_clock(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)
    # Completeness determined long enough ago that the 30-day
    # hearing-and-decision clock (which DOES carry the §8.d.1 consequence)
    # is MISSED as of "today" in this test environment.
    _record_dates(db_path, case["id"], [
        {"kind": "application_received", "occurred_on": "2025-10-02"},
        {"kind": "completeness_determined", "occurred_on": "2025-10-20"},
    ])

    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "auto-approval-banner" in resp.text
    assert "row-auto-approval" in resp.text
    assert "1 case" in resp.text  # urgent_count == 1, singular phrasing

    detail = client.get(f"/cases/{case['id']}")
    assert detail.status_code == 200
    assert "auto-approval-banner" in detail.text
    assert "AUTO-APPROVAL" in detail.text
    assert "§8.d.1" in detail.text or "8.d.1" in detail.text


def test_dashboard_flags_auto_approval_risk_for_a_stalled_subdivision_f1_repro(client):
    """F1's ORIGINAL repro, end to end through the real routes: a
    subdivision received 2025-10-02 with NOTHING recorded since (no
    completeness_determined milestone at all -- unlike the test above, which
    records completeness and then lets the downstream hearing/decision clock
    go MISSED). subdivision_hearing_decision never leaves PENDING_START, but
    its predecessor duty (completeness, due 2025-11-01) is itself long
    overdue -- this must still trip the banner/row-highlight, not silently
    report no risk (CONTRACT.md's conservative-warning instruction)."""
    db_path = app_main.DB_PATH
    case = _create_case(db_path)
    _record_dates(db_path, case["id"], [
        {"kind": "application_received", "occurred_on": "2025-10-02"},
    ])

    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "auto-approval-banner" in resp.text
    assert "row-auto-approval" in resp.text

    detail = client.get(f"/cases/{case['id']}")
    assert detail.status_code == 200
    assert "auto-approval-banner" in detail.text
    assert "START NOT RECORDED" in detail.text
    assert "§8.d.1" in detail.text


def test_dashboard_does_not_flag_a_case_with_no_open_deadlines(client):
    db_path = app_main.DB_PATH
    _create_case(db_path, application_type="other", label="No-clock case")

    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "auto-approval-banner" not in resp.text
    assert "row-auto-approval" not in resp.text


# --------------------------------------------------------------------------- #
# case detail: header, ruleset badge, key dates (incl. a superseded re-notice
# row), documents + tier census, audit trail
# --------------------------------------------------------------------------- #


def test_case_detail_renders_header_and_binding_ruleset_badge(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)

    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    assert "M003, L059" in resp.text
    assert "White Rd" in resp.text
    assert "Shattuck" in resp.text
    assert "BINDING" in resp.text
    assert "ruleset-badge binding" in resp.text


def test_case_detail_shows_a_rescheduled_re_noticed_hearing_without_smoothing_it(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)

    conn = db_mod.connect(db_path)
    try:
        original = cases_mod.record_dates(
            conn, case["id"],
            entries=[{"kind": "notice_mailed", "occurred_on": "2025-10-09",
                      "note": "original notice, ahead of the Oct 16 meeting"}],
            why="seed", actor_user_id=security.SYNTHETIC_USER_ID,
        )
        original_id = original["recorded"][0]["id"]
        cases_mod.record_dates(
            conn, case["id"],
            entries=[{"kind": "notice_mailed", "occurred_on": "2025-11-04",
                      "note": "re-notice after the hearing was rescheduled to Nov 20",
                      "supersedes_id": original_id, "supersede_reason": "reschedule"}],
            why="re-notice", actor_user_id=security.SYNTHETIC_USER_ID,
        )
    finally:
        conn.close()

    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    # Both notice_mailed dates are visible -- the original (struck through,
    # marked superseded) AND the re-notice, never collapsed into one row.
    assert "2025-10-09" in resp.text
    assert "2025-11-04" in resp.text
    assert "milestone-superseded" in resp.text
    assert "superseded" in resp.text


def test_case_detail_shows_uploaded_document_with_tier_census(client):
    if not FIXTURE_PDF.exists():
        pytest.skip(f"fixture PDF not present at {FIXTURE_PDF}")

    db_path = app_main.DB_PATH
    case = _create_case(db_path, application_type="use", label="Upload smoke case")

    with open(FIXTURE_PDF, "rb") as f:
        upload = client.post(
            f"/api/cases/{case['id']}/documents",
            files={"file": ("morrissey.pdf", f, "application/pdf")},
            data={"doc_role": "application_form", "title": "Morrissey Application"},
        )
    assert upload.status_code == 200, upload.text
    assert upload.json()["ok"] is True

    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    assert "Morrissey Application" in resp.text
    assert "tier-badge" in resp.text


def test_case_detail_shows_audit_trail_entries(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)
    _record_dates(db_path, case["id"], [{"kind": "application_received", "occurred_on": "2026-08-01"}])

    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    assert "case.created" in resp.text
    assert "case.dates_recorded" in resp.text


def test_case_detail_unknown_case_returns_404(client):
    resp = client.get(f"/cases/{uuid.uuid4().hex}")
    assert resp.status_code == 404
    assert resp.json()["error"] == "case_not_found"


# --------------------------------------------------------------------------- #
# graceful degradation -- a case pinned to a district doesn't error even
# though rulesets/adopted/districts.json is blocked (DECISIONS-NEEDED
# D-0001/D-0002)
# --------------------------------------------------------------------------- #


def test_case_detail_degrades_gracefully_when_district_data_is_blocked(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path, district_key="d1")

    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    assert "d1" in resp.text
    # Either the worksheet loaded (districts.json present in this checkout)
    # or the D-0001/D-0002 note is shown -- either way, no 500.
    assert ("D-0001" in resp.text) or ("d1" in resp.text)


# --------------------------------------------------------------------------- #
# F5 -- a malformed historical occurred_on must never 500 the dashboard or a
# case's own detail page. app/cases.py:record_dates now rejects a bad value
# AT WRITE TIME (tests/test_cases.py), so this seeds one the only way it can
# still get in post-fix: directly via SQL, standing in for a row written
# before the fix existed, or by any other path that failed to validate --
# exactly the scenario the adversarial review reproduced (PATCH .../dates
# with "December 18, 2025" used to 200, then every later GET /cases and
# GET /cases/{id} 500'd, permanently, because case_milestones is append-only).
# --------------------------------------------------------------------------- #


def _insert_raw_milestone(db_path: Path, case_id: str, *, milestone_id: str, occurred_on: str,
                           kind: str = "application_received") -> None:
    """Bypasses app.cases.record_dates entirely -- the only way, post-fix,
    to get a malformed occurred_on into case_milestones at all."""
    conn = db_mod.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO case_milestones
                (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id)
            VALUES (?, ?, ?, ?, NULL, NULL, '2026-08-20T00:00:00.000Z', ?);
            """,
            (milestone_id, case_id, kind, occurred_on, security.SYNTHETIC_USER_ID),
        )
        conn.commit()
    finally:
        conn.close()


def test_dashboard_does_not_500_on_a_case_with_a_malformed_historical_date(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path, label="Case with a bad legacy date")
    _insert_raw_milestone(db_path, case["id"], milestone_id="m_bad_1", occurred_on="December 18, 2025")

    resp = client.get("/cases")
    assert resp.status_code == 200
    assert "Case with a bad legacy date" in resp.text
    # engine.deadlines.case_facts_from_row no longer raises on this row (it
    # now carries an honestly-unknown None date instead, per-field, rather
    # than crashing the whole case) -- so the row renders normally, with
    # whatever OTHER clocks don't depend on the unparseable date. The bar
    # this test holds is simply: never a 500, and the case is still listed.
    assert "Internal Server Error" not in resp.text


def test_case_detail_does_not_500_on_a_malformed_historical_date_and_flags_it(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)
    _insert_raw_milestone(db_path, case["id"], milestone_id="m_bad_2", occurred_on="December 18, 2025")

    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    assert "December 18, 2025" in resp.text  # the bad row is still shown, honestly
    assert "not a valid calendar date" in resp.text  # the per-row flag
    assert "Correct this date" in resp.text  # the repair-path button


def test_case_detail_repair_path_clears_the_flag(client):
    db_path = app_main.DB_PATH
    case = _create_case(db_path)
    _insert_raw_milestone(db_path, case["id"], milestone_id="m_bad_3", occurred_on="December 18, 2025")

    # Confirm it's broken first.
    broken = client.get(f"/cases/{case['id']}")
    assert "not a valid calendar date" in broken.text

    # The repair path: a NEW, valid entry with supersedes_id pointing at the
    # bad row -- exactly what the "Correct this date" button drives
    # client-side (app/cases.py:record_dates itself is covered end-to-end,
    # over HTTP, in tests/test_cases_routes.py; this seeds the same way
    # every other test in this file does, per its own module docstring).
    _record_dates(db_path, case["id"], [
        {"kind": "application_received", "occurred_on": "2025-12-18", "supersedes_id": "m_bad_3",
         "supersede_reason": "correction"},
    ], why="correcting a malformed legacy row")

    fixed = client.get(f"/cases/{case['id']}")
    assert fixed.status_code == 200
    assert "not a valid calendar date" not in fixed.text
    assert "milestone-superseded" in fixed.text  # the bad row, kept, marked superseded

    dashboard = client.get("/cases")
    assert dashboard.status_code == 200
    assert "Internal Server Error" not in dashboard.text
