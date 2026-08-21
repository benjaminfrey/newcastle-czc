"""Tests for N2 -- event recordability (the missing gate assertion).

Before this fix, three §23 appeal-track clocks (administrative_appeal_hearing
§23.d.2, administrative_appeal_decision §23.d.3, reconsideration_decision
§23.e.4 -- rulesets/adopted/clocks.json, added at F3) named four CaseFacts
events (appeal_hearing_opened_at, appeal_hearing_closed_at, appeal_decision_at,
reconsideration_decided_at) that NO case_milestones.kind could ever record.
Two of those three clocks carry the §8.d.1 auto-approval consequence, so a
Board of Appeals that held its hearing and decided an appeal exactly on time
still showed a PERMANENT, un-clearable alarm.

This file is deliberately a SEPARATE module from tests/test_deadlines.py,
tests/test_cases.py, and tests/test_verify_structure.py (which other,
concurrent fixes to this same deadline engine are actively editing) so this
N2-scoped test suite never collides with in-flight edits to those files.

    1. app.cases.CASE_MILESTONE_KINDS / engine.deadlines._MILESTONE_TO_FIELD /
       app.main.MILESTONE_KIND_LABELS all carry the four new kinds.
    2. engine.deadlines.event_recordable_kinds() -- the single source of
       truth the recordability assertion consults.
    3. ruleset_build.verify_structure.check_clock_event_recordability --
       passes cleanly on the committed rulesets, and (regression proof)
       fails, naming the exact clock/role/layer, when any one of the four
       layers is broken.
    4. run.py --verify-structure and --selftest both surface the check.
    5. app.cases.record_dates() can actually store all four new kinds.
    6. engine.deadlines.compute_deadlines() -- a full appeal + reconsideration
       timeline reaches MET on every §23 clock with no residual alarm.
    7. END TO END through the real HTTP routes (POST /api/cases, PATCH
       .../dates, GET /cases/{id}) -- the PROVE IT walkthrough.

Offline, no network, no LLM, no PII.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import cases as cases_mod  # noqa: E402
from app import db as db_mod  # noqa: E402
from app import main as app_main  # noqa: E402
from app import security  # noqa: E402
from app.routes import cases as cases_routes_mod  # noqa: E402
from engine import deadlines as dl  # noqa: E402
from ruleset_build import verify_structure as vs  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"

NEW_KINDS = (
    "appeal_hearing_opened",
    "appeal_hearing_closed",
    "appeal_decision",
    "reconsideration_decided",
)

# --------------------------------------------------------------------------- #
# 1. Static vocabulary -- the four new kinds are wired into every layer.
# --------------------------------------------------------------------------- #


def test_new_kinds_are_in_case_milestone_kinds():
    for k in NEW_KINDS:
        assert k in cases_mod.CASE_MILESTONE_KINDS


def test_new_kinds_are_mapped_in_milestone_to_field():
    expected = {
        "appeal_hearing_opened": "appeal_hearing_opened_at",
        "appeal_hearing_closed": "appeal_hearing_closed_at",
        "appeal_decision": "appeal_decision_at",
        "reconsideration_decided": "reconsideration_decided_at",
    }
    for kind, field in expected.items():
        assert dl._MILESTONE_TO_FIELD[kind] == field


def test_new_kinds_have_operator_ui_labels():
    for k in NEW_KINDS:
        assert k in app_main.MILESTONE_KIND_LABELS
        assert app_main.MILESTONE_KIND_LABELS[k]  # non-empty


def test_new_kinds_render_as_dropdown_options_on_the_case_detail_page(tmp_path, monkeypatch):
    """The template renders one <option> per sorted(CASE_MILESTONE_KINDS)
    with MILESTONE_KIND_LABELS.get(k, k) as its text -- confirm the four new
    kinds actually appear as *labeled* options, not just raw snake_case."""
    db_path = tmp_path / "permit-review.db"
    conn = db_mod.connect(db_path)
    db_mod.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    case = cases_mod.create_case(
        conn, application_type="variance", map_lot="M1, L1", situs_address="Test Rd",
        applicant_name="Tester", actor_user_id=security.SYNTHETIC_USER_ID,
    )
    conn.close()

    monkeypatch.setattr(app_main, "DB_PATH", db_path)
    app = app_main.create_app(port=8781)
    with TestClient(app, base_url="http://127.0.0.1:8781") as client:
        resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    html = resp.text
    for kind, label in (
        ("appeal_hearing_opened", app_main.MILESTONE_KIND_LABELS["appeal_hearing_opened"]),
        ("appeal_hearing_closed", app_main.MILESTONE_KIND_LABELS["appeal_hearing_closed"]),
        ("appeal_decision", app_main.MILESTONE_KIND_LABELS["appeal_decision"]),
        ("reconsideration_decided", app_main.MILESTONE_KIND_LABELS["reconsideration_decided"]),
    ):
        assert f'value="{kind}"' in html
        assert label in html


# --------------------------------------------------------------------------- #
# 2. event_recordable_kinds() -- the single source of truth.
# --------------------------------------------------------------------------- #


def test_event_recordable_kinds_for_the_four_new_events():
    assert dl.event_recordable_kinds("appeal_hearing_opened_at") == ("appeal_hearing_opened",)
    assert dl.event_recordable_kinds("appeal_hearing_closed_at") == ("appeal_hearing_closed",)
    assert dl.event_recordable_kinds("appeal_decision_at") == ("appeal_decision",)
    assert dl.event_recordable_kinds("reconsideration_decided_at") == ("reconsideration_decided",)


def test_event_recordable_kinds_special_case_submitted_at():
    # DECISIONS-NEEDED D-0008's multi-source ranking -- documented exception,
    # not a generic _MILESTONE_TO_FIELD entry (see that dict's own docstring).
    assert set(dl.event_recordable_kinds("submitted_at")) == {"application_received", "application_dated"}


def test_event_recordable_kinds_empty_for_a_field_no_kind_records():
    assert dl.event_recordable_kinds("this_field_does_not_exist") == ()
    # meeting_date / draft_document_generated are sourced outside
    # case_milestones entirely (the cases row / generated_documents) and are
    # never named as a clocks.json event -- honestly empty, not guessed.
    assert dl.event_recordable_kinds("meeting_date") == ()
    assert dl.event_recordable_kinds("draft_document_generated") == ()


# --------------------------------------------------------------------------- #
# 3. The gate assertion itself.
# --------------------------------------------------------------------------- #


def test_recordability_check_passes_on_the_committed_ruleset():
    result = vs.Result()
    vs.check_clock_event_recordability(result)
    fails = [line for line in result.lines if line.startswith("FAIL")]
    assert result.ok, f"unexpected FAIL lines: {fails}"
    assert any("clock event recordability" in line for line in result.lines)


def test_recordability_check_covers_every_clock_role_pair():
    """44 = 22 clocks x 2 roles (start_event, satisfying_event) -- confirms
    the check actually walked everything, not a vacuous pass."""
    result = vs.Result()
    vs.check_clock_event_recordability(result)
    note_line = next(line for line in result.lines if "pairs checked" in line)
    assert "44" in note_line
    assert "22 clocks" in note_line


def test_recordability_check_catches_a_missing_field_mapping(monkeypatch):
    """Reproduces the EXACT original N2 defect: an event named in clocks.json
    with no engine.deadlines._MILESTONE_TO_FIELD entry at all."""
    broken = dict(dl._MILESTONE_TO_FIELD)
    del broken["appeal_hearing_opened"]
    monkeypatch.setattr(dl, "_MILESTONE_TO_FIELD", broken)

    result = vs.Result()
    vs.check_clock_event_recordability(result)
    assert not result.ok
    fail_line = next(line for line in result.lines if line.startswith("FAIL"))
    assert "administrative_appeal_hearing" in fail_line
    assert "NOT MAPPED" in fail_line


def test_recordability_check_catches_a_kind_missing_from_case_milestone_kinds(monkeypatch):
    narrowed = frozenset(k for k in cases_mod.CASE_MILESTONE_KINDS if k != "appeal_decision")
    monkeypatch.setattr(cases_mod, "CASE_MILESTONE_KINDS", narrowed)

    result = vs.Result()
    vs.check_clock_event_recordability(result)
    assert not result.ok
    fail_line = next(line for line in result.lines if line.startswith("FAIL"))
    assert "appeal_decision" in fail_line
    assert "app.cases.CASE_MILESTONE_KINDS" in fail_line


def test_recordability_check_catches_a_kind_missing_from_ui_labels(monkeypatch):
    narrowed = {k: v for k, v in app_main.MILESTONE_KIND_LABELS.items() if k != "reconsideration_decided"}
    monkeypatch.setattr(app_main, "MILESTONE_KIND_LABELS", narrowed)

    result = vs.Result()
    vs.check_clock_event_recordability(result)
    assert not result.ok
    fail_line = next(line for line in result.lines if line.startswith("FAIL"))
    assert "reconsideration_decided" in fail_line
    assert "app.main.MILESTONE_KIND_LABELS" in fail_line


def test_recordability_check_catches_a_stale_check_constraint(monkeypatch):
    """Layer (a) -- a kind mapped everywhere in code but the DB's own CHECK
    constraint doesn't actually carry it (a migration that was never
    written/applied)."""
    monkeypatch.setattr(vs, "_case_milestones_kind_check_values",
                         lambda: set(cases_mod.CASE_MILESTONE_KINDS) - {"appeal_hearing_closed"})

    result = vs.Result()
    vs.check_clock_event_recordability(result)
    assert not result.ok
    fail_line = next(line for line in result.lines if line.startswith("FAIL"))
    assert "appeal_hearing_closed" in fail_line
    assert "CHECK constraint" in fail_line


# --------------------------------------------------------------------------- #
# 4. Wired into both run.py entry points -- a standing invariant.
# --------------------------------------------------------------------------- #


def test_selftest_check_9_includes_the_recordability_gate(capsys):
    rc = app_main.selftest()
    out = capsys.readouterr().out
    assert "clock event recordability" not in out  # only shown on FAIL by main.py's own filter
    assert "9. ruleset_build.verify_structure -- structural gate over both rulesets" in out
    assert "PASS  9." in out
    assert rc == 0


def test_verify_structure_run_includes_the_recordability_gate(capsys):
    rc = vs.run(quiet=False)
    out = capsys.readouterr().out
    assert "clock event recordability" in out
    assert "STRUCTURE: ALL OK" in out
    assert rc == 0


# --------------------------------------------------------------------------- #
# 5. app.cases.record_dates() can actually store the four new kinds.
# --------------------------------------------------------------------------- #


@pytest.fixture()
def conn(tmp_path):
    db_path = tmp_path / "permit-review.db"
    c = db_mod.connect(db_path)
    db_mod.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    _seed_rulesets(c)
    try:
        yield c
    finally:
        c.close()


def test_record_dates_accepts_all_four_new_appeal_kinds(conn):
    case = cases_mod.create_case(
        conn, application_type="variance", map_lot="M2, L2", situs_address="Appeal Rd",
        applicant_name="Appellant", actor_user_id=security.SYNTHETIC_USER_ID,
    )
    result = cases_mod.record_dates(
        conn, case["id"],
        entries=[
            {"kind": "appeal_hearing_opened", "occurred_on": "2025-03-05"},
            {"kind": "appeal_hearing_closed", "occurred_on": "2025-03-05"},
            {"kind": "appeal_decision", "occurred_on": "2025-03-20"},
            {"kind": "reconsideration_decided", "occurred_on": "2025-02-25"},
        ],
        why="appeal + reconsideration concluded", actor_user_id=security.SYNTHETIC_USER_ID,
    )
    stored = {r["kind"]: r["occurred_on"] for r in result["recorded"]}
    assert stored["appeal_hearing_opened"] == "2025-03-05"
    assert stored["appeal_hearing_closed"] == "2025-03-05"
    assert stored["appeal_decision"] == "2025-03-20"
    assert stored["reconsideration_decided"] == "2025-02-25"

    rows = cases_mod.case_dates_for(conn, case["id"])
    assert {r["kind"] for r in rows} == set(NEW_KINDS)


# --------------------------------------------------------------------------- #
# 6. compute_deadlines() -- a full appeal + reconsideration timeline reaches
#    MET on every §23 clock, no residual alarm.
# --------------------------------------------------------------------------- #


def test_full_appeal_and_reconsideration_timeline_reaches_met_with_no_residual_alarm():
    case = dl.CaseFacts(
        case_id="c-n2-full", review_track="variance",
        submitted_at=date(2025, 1, 6),
        notice_mailed_at=date(2025, 1, 9),
        hearing_opened_at=date(2025, 1, 20),
        hearing_closed_at=date(2025, 1, 20),
        decision_at=date(2025, 2, 1),
        decision_filed_at=date(2025, 2, 4),
        certificate_recorded_at=date(2025, 3, 1),
        reconsideration_requested_at=date(2025, 2, 8),
        # HARD-FINAL round, Finding 6: reconsideration_decision's predicate
        # is now the §23.e.2/.e.3 VOTE TO RECONSIDER, not the bare §23.e.1
        # request above -- reconsideration_voted_at must be recorded too for
        # this clock to trigger at all (see CaseFacts.reconsideration_voted_at).
        reconsideration_voted_at=date(2025, 2, 12),
        reconsideration_decided_at=date(2025, 2, 25),
        appeal_filed_at=date(2025, 2, 20),
        appeal_hearing_opened_at=date(2025, 3, 5),
        appeal_hearing_closed_at=date(2025, 3, 5),
        appeal_decision_at=date(2025, 3, 20),
    )
    rows = dl.compute_deadlines(case, as_of=date(2026, 8, 21), include_meeting_clocks=False)
    by_key = {d.clock_key: d for d in rows}

    for key in (
        "notice_mailed", "variance_review_hearing", "variance_decision",
        "variance_certificate_recorded", "decision_filed_with_clerk",
        "administrative_appeal", "administrative_appeal_hearing", "administrative_appeal_decision",
        "reconsideration", "reconsideration_decision",
    ):
        d = by_key[key]
        assert d.status == dl.ClockStatus.MET.value, f"{key}: expected MET, got {d.status}"
        assert d.auto_approval_alert is None, f"{key}: unexpected auto_approval_alert {d.auto_approval_alert!r}"
        assert d.start_not_recorded_alert is None, (
            f"{key}: unexpected start_not_recorded_alert {d.start_not_recorded_alert!r}"
        )
        assert dl.presents_auto_approval_risk(d) is False, f"{key}: unexpectedly presents auto-approval risk"

    # The case-wide gate the dashboard/case-detail banner keys off.
    assert any(dl.presents_auto_approval_risk(d) for d in rows) is False


# --------------------------------------------------------------------------- #
# 7. PROVE IT -- end to end through the real HTTP routes.
# --------------------------------------------------------------------------- #


@pytest.fixture()
def http_client(tmp_path, monkeypatch):
    """The FULL app (app.main.create_app()), so both app.main's own routes
    (GET /cases/{id}) and app.routes.cases's router (POST/PATCH /api/cases...,
    mounted separately with its OWN module-level DB_PATH binding) resolve to
    the SAME throwaway database -- see app/routes/cases.py's own docstring on
    why it duplicates app.main's envelope helpers instead of importing them
    (no import cycle), the same reason its DB_PATH is a separate name that
    needs its own monkeypatch here."""
    db_path = tmp_path / "permit-review.db"
    conn = db_mod.connect(db_path)
    db_mod.migrate(conn, app_main.MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    conn.close()

    monkeypatch.setattr(app_main, "DB_PATH", db_path)
    monkeypatch.setattr(app_main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(cases_routes_mod, "DB_PATH", db_path)

    app = app_main.create_app(port=8781)
    with TestClient(app, base_url="http://127.0.0.1:8781") as c:
        yield c, db_path


def _record(client, case_id, kind, occurred_on, why):
    resp = client.patch(
        f"/api/cases/{case_id}/dates",
        json={"dates": [{"kind": kind, "occurred_on": occurred_on}], "why": why},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    return body["data"]


def test_end_to_end_appealed_case_through_the_real_http_routes(http_client):
    """A real appealed case, driven entirely through POST /api/cases,
    PATCH /api/cases/{id}/dates, and GET /cases/{id} -- exactly the routes an
    operator's browser calls. Appeal filed; BOA hearing opened and closed on
    time; appeal decision recorded. Every §23 clock reaches a correct
    terminal status with NO residual alarm -- proving the N2 fix end to end,
    not just at the engine layer."""
    client, db_path = http_client

    create_resp = client.post(
        "/api/cases",
        json={
            "application_type": "variance",
            "map_lot": "M9, L12",
            "situs_address": "Appeal Test Lane",
            "applicant_name": "N2 Walkthrough",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    case_id = create_resp.json()["data"]["id"]

    # The case's own original review, decided and filed cleanly.
    _record(client, case_id, "application_received", "2025-01-06", "application received")
    _record(client, case_id, "notice_mailed", "2025-01-09", "notice mailed")
    _record(client, case_id, "hearing_opened", "2025-01-20", "variance hearing opened")
    _record(client, case_id, "hearing_closed", "2025-01-20", "variance hearing closed same night")
    _record(client, case_id, "decision", "2025-02-01", "Board decision")
    _record(client, case_id, "decision_filed", "2025-02-04", "decision filed with the Town Clerk")

    # The appeal: filed, BOA hearing opened + closed on time, decided -- the
    # exact "appeal filed, BOA hearing opened and closed on time, appeal
    # decision recorded" sequence the task brief asks for, through the four
    # newly-recordable N2 events (appeal_filed was already recordable before
    # N2; the three that follow were not).
    _record(client, case_id, "appeal_filed", "2025-02-20", "aggrieved party filed an appeal")
    _record(client, case_id, "appeal_hearing_opened", "2025-03-05", "BOA opened the appeal hearing")
    _record(client, case_id, "appeal_hearing_closed", "2025-03-05", "BOA closed the appeal hearing")
    _record(client, case_id, "appeal_decision", "2025-03-20", "BOA upheld the decision on appeal")

    # A reconsideration request concluded too -- reconsideration_decided is
    # the fourth newly-recordable N2 event. HARD-FINAL round, Finding 6:
    # reconsideration_decision's predicate is now the §23.e.2/.e.3 VOTE TO
    # RECONSIDER (kind "reconsideration_voted"), not the bare §23.e.1 request
    # -- both are recorded here, request then vote, matching the Code's own
    # sequence.
    _record(client, case_id, "reconsideration_requested", "2025-02-08", "applicant requested reconsideration")
    _record(client, case_id, "reconsideration_voted", "2025-02-12", "Board voted to reconsider its decision")
    _record(client, case_id, "reconsideration_decided", "2025-02-25", "Board concluded reconsideration, no change")

    detail_resp = client.get(f"/cases/{case_id}")
    assert detail_resp.status_code == 200
    html = detail_resp.text

    # No auto-approval alarm anywhere on the rendered page -- the exact
    # symptom N2's task brief opens with ("the auto-approval banner now
    # fires on every decided, unappealed case") does not, and must not,
    # survive a genuinely timely appeal.
    assert "AUTO-APPROVAL" not in html
    assert "START NOT RECORDED" not in html

    # Confirm the actual engine-level statuses too (authoritative, not just
    # a string-absence check on the rendered page) -- reads through the SAME
    # DB the HTTP routes just wrote to.
    conn = db_mod.connect(db_path)
    try:
        facts = [f for f in dl.load_all_case_facts(conn) if f.case_id == case_id]
        assert len(facts) == 1
        rows = dl.compute_deadlines(facts[0], as_of=date(2026, 8, 21))
    finally:
        conn.close()

    by_key = {d.clock_key: d for d in rows}
    for key in (
        "notice_mailed", "variance_review_hearing", "variance_decision",
        "decision_filed_with_clerk", "administrative_appeal",
        "administrative_appeal_hearing", "administrative_appeal_decision",
        "reconsideration", "reconsideration_decision",
    ):
        d = by_key[key]
        assert d.status == dl.ClockStatus.MET.value, f"{key}: expected MET, got {d.status} ({d!r})"
        assert dl.presents_auto_approval_risk(d) is False, f"{key}: unexpectedly presents auto-approval risk"

    assert any(dl.presents_auto_approval_risk(d) for d in rows) is False
    assert app_main._has_auto_approval_alert(rows) is False

    # And the milestone history round-trips exactly as recorded, through the
    # real HTTP GET too (case_detail's "Key dates" panel).
    for kind_label in (
        "Appeal hearing opened (Appellate Authority)",
        "Appeal hearing closed (Appellate Authority)",
        "Appeal decision issued (Appellate Authority)",
        "Board voted to reconsider (§23.e.2-.e.3)",
        "Reconsideration concluded (Board of Appeals)",
    ):
        assert kind_label in html
