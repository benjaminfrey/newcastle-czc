"""Tests for HARD-FINAL Finding 3 -- Article 7 §6.e.1/§6.e.2 clock extensions,
and the engine.deadlines.CaseFacts.waived_clocks/na_clocks write path.

Three layers, matching the task's own "Tests" requirement:
  1. engine/deadlines.py -- CaseFacts.clock_extension_days shifts due_date and
     clears presents_auto_approval_risk(); an unextended clock still reports
     risk (test_deadlines.py already covers this baseline extensively -- this
     file only re-confirms it alongside the extended case, as a direct
     before/after pair).
  2. app/cases.py:record_dates -- the write path (validation + the audit
     trail entry, including the written_agreement_ref).
  3. app/main.py -- the case-detail HTTP page: the auto-approval banner
     clears once a lawful extension is recorded, and the page renders the
     extension in the deadlines table and the Key Dates audit trail.

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
from engine import deadlines as dl  # noqa: E402

from tests.test_cases import _seed_rulesets  # noqa: E402

ACTOR = security.SYNTHETIC_USER_ID

# special_permit_decision: hearing_closed_at -> decision_at, 45 calendar days,
# municipal_duty, carries the §8.d.1 failure_consequence -- and (per
# engine.deadlines.clock_is_extendable()) an eligible §6.e.1(b) "decision"
# clock. notice_mailed is applicant_duty and NOT eligible -- used below as
# the negative case.
EXTENDABLE_CLOCK = "special_permit_decision"
INELIGIBLE_CLOCK = "notice_mailed"


# --------------------------------------------------------------------------- #
# Layer 1 -- engine/deadlines.py
# --------------------------------------------------------------------------- #


def test_unextended_clock_still_presents_auto_approval_risk():
    """Baseline: recording NO extension leaves the pre-existing MISSED/
    at-risk behavior completely unchanged."""
    case = dl.CaseFacts(
        case_id="c-ext-1", review_track="special_permit", hearing_closed_at=date(2026, 1, 1),
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 1), include_meeting_clocks=False)}
    d = rows[EXTENDABLE_CLOCK]
    assert d.status == dl.ClockStatus.MISSED.value
    assert d.due_date == date(2026, 2, 15)  # 45 calendar days from 2026-01-01
    assert d.extension_days_applied == 0
    assert d.auto_approval_alert is not None
    assert dl.presents_auto_approval_risk(d) is True


def test_extended_clock_moves_the_due_date_and_clears_auto_approval_risk():
    """The Finding 3 repro: the SAME facts as above, plus a recorded
    clock_extension_days entry -- due_date shifts by exactly the agreed day
    count (in the clock's own basis), and the false alarm clears."""
    case = dl.CaseFacts(
        case_id="c-ext-2", review_track="special_permit", hearing_closed_at=date(2026, 1, 1),
        clock_extension_days={EXTENDABLE_CLOCK: 30},
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 1), include_meeting_clocks=False)}
    d = rows[EXTENDABLE_CLOCK]
    assert d.due_date == date(2026, 3, 17)  # 2026-02-15 + 30 days
    assert d.extension_days_applied == 30
    assert d.status == dl.ClockStatus.OPEN.value
    assert d.auto_approval_alert is None
    assert dl.presents_auto_approval_risk(d) is False


def test_multiple_extensions_against_the_same_clock_accumulate():
    case = dl.CaseFacts(
        case_id="c-ext-3", review_track="special_permit", hearing_closed_at=date(2026, 1, 1),
        clock_extension_days={EXTENDABLE_CLOCK: 45},  # e.g. two agreements: +30, then +15
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 1), include_meeting_clocks=False)}
    assert rows[EXTENDABLE_CLOCK].due_date == date(2026, 4, 1)  # 2026-02-15 + 45


def test_extension_on_an_unrelated_clock_does_not_move_this_ones_due_date():
    case = dl.CaseFacts(
        case_id="c-ext-4", review_track="special_permit", hearing_closed_at=date(2026, 1, 1),
        clock_extension_days={"special_permit_review_hearing": 30},  # a DIFFERENT clock
    )
    rows = {d.clock_key: d for d in dl.compute_deadlines(case, as_of=date(2026, 3, 1), include_meeting_clocks=False)}
    assert rows[EXTENDABLE_CLOCK].due_date == date(2026, 2, 15)
    assert rows[EXTENDABLE_CLOCK].extension_days_applied == 0
    assert dl.presents_auto_approval_risk(rows[EXTENDABLE_CLOCK]) is True


def test_clock_is_extendable_eligibility():
    clocks = {c.clock_key: c for c in dl.load_clocks("adopted")}
    assert dl.clock_is_extendable(clocks[EXTENDABLE_CLOCK]) is True  # decision, municipal_duty
    assert dl.clock_is_extendable(clocks["special_permit_review_hearing"]) is True  # hearing commencement
    assert dl.clock_is_extendable(clocks[INELIGIBLE_CLOCK]) is False  # applicant_duty
    assert dl.clock_is_extendable(clocks["administrative_appeal"]) is False  # party_right
    assert dl.clock_is_extendable(clocks["subdivision_plat_recorded_90d"]) is False  # applicant_duty
    assert EXTENDABLE_CLOCK in dl.extendable_clock_keys("adopted")
    assert INELIGIBLE_CLOCK not in dl.extendable_clock_keys("adopted")


def test_case_facts_from_row_populates_clock_extension_days_from_live_rows_only():
    case_row = {
        "id": "c-ext-5", "application_type": "special_permit", "ruleset_key": "adopted",
        "is_scratch": 0, "label": "", "received_at": None, "meeting_date": None,
    }
    milestone_rows = [
        {
            "kind": "hearing_closed", "occurred_on": "2026-01-01", "note": None,
            "superseded_by": None, "supersede_reason": None,
            "target_clock_key": None, "extension_days": None, "written_agreement_ref": None,
        },
        {
            "kind": "extension_agreed", "occurred_on": "2026-01-15", "note": None,
            "superseded_by": None, "supersede_reason": None,
            "target_clock_key": EXTENDABLE_CLOCK, "extension_days": 30,
            "written_agreement_ref": "Letter dated 2026-01-14",
        },
        # A SUPERSEDED extension row must NOT count.
        {
            "kind": "extension_agreed", "occurred_on": "2026-01-10", "note": None,
            "superseded_by": "x", "supersede_reason": "correction",
            "target_clock_key": EXTENDABLE_CLOCK, "extension_days": 999,
            "written_agreement_ref": "typo'd entry",
        },
        {
            "kind": "clock_waived", "occurred_on": "2026-01-16", "note": "Board waived per vote",
            "superseded_by": None, "supersede_reason": None,
            "target_clock_key": INELIGIBLE_CLOCK, "extension_days": None, "written_agreement_ref": None,
        },
    ]
    case = dl.case_facts_from_row(case_row, milestone_rows)
    assert case.clock_extension_days == {EXTENDABLE_CLOCK: 30}
    assert case.waived_clocks == frozenset({INELIGIBLE_CLOCK})
    assert case.na_clocks == frozenset()
    # history carries the superseded row too (F7-style), with its full shape.
    superseded_entries = [h for h in case.history if h["superseded"]]
    assert len(superseded_entries) == 1
    assert superseded_entries[0]["extension_days"] == 999


# --------------------------------------------------------------------------- #
# Layer 2 -- app/cases.py:record_dates
# --------------------------------------------------------------------------- #


@pytest.fixture()
def conn(tmp_path: Path):
    c = db_mod.connect(tmp_path / "permit-review.db")
    db_mod.migrate(c, app_main.MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    _seed_rulesets(c)
    try:
        yield c
    finally:
        c.close()


def _make_case(conn, **overrides):
    kwargs = dict(application_type="special_permit", actor_user_id=ACTOR)
    kwargs.update(overrides)
    return cases_mod.create_case(conn, **kwargs)


def test_record_dates_rejects_extension_on_an_ineligible_clock(conn):
    case = _make_case(conn)
    with pytest.raises(cases_mod.ValidationError) as ei:
        cases_mod.record_dates(
            conn, case["id"],
            entries=[{
                "kind": "extension_agreed", "occurred_on": "2026-01-15",
                "target_clock_key": INELIGIBLE_CLOCK, "extension_days": 10,
                "written_agreement_ref": "a letter",
            }],
            why="test", actor_user_id=ACTOR,
        )
    assert ei.value.details[0]["field"] == "dates[0].target_clock_key"
    assert "§6.e.1" in ei.value.details[0]["message"]


@pytest.mark.parametrize("missing_field", ["target_clock_key", "extension_days", "written_agreement_ref"])
def test_record_dates_rejects_extension_missing_a_required_field(conn, missing_field):
    case = _make_case(conn)
    entry = {
        "kind": "extension_agreed", "occurred_on": "2026-01-15",
        "target_clock_key": EXTENDABLE_CLOCK, "extension_days": 10,
        "written_agreement_ref": "a letter",
    }
    del entry[missing_field]
    with pytest.raises(cases_mod.ValidationError) as ei:
        cases_mod.record_dates(conn, case["id"], entries=[entry], why="test", actor_user_id=ACTOR)
    assert ei.value.details[0]["field"] == f"dates[0].{missing_field}"


def test_record_dates_rejects_zero_or_negative_extension_days(conn):
    case = _make_case(conn)
    for bad in (0, -5):
        with pytest.raises(cases_mod.ValidationError):
            cases_mod.record_dates(
                conn, case["id"],
                entries=[{
                    "kind": "extension_agreed", "occurred_on": "2026-01-15",
                    "target_clock_key": EXTENDABLE_CLOCK, "extension_days": bad,
                    "written_agreement_ref": "a letter",
                }],
                why="test", actor_user_id=ACTOR,
            )


def test_record_dates_accepts_a_valid_extension_and_it_appears_in_the_audit_trail(conn):
    case = _make_case(conn)
    result = cases_mod.record_dates(
        conn, case["id"],
        entries=[{
            "kind": "extension_agreed", "occurred_on": "2026-01-15",
            "target_clock_key": EXTENDABLE_CLOCK, "extension_days": 30,
            "written_agreement_ref": "Letter dated 2026-01-14, signed by applicant and CEO",
        }],
        why="agreed extension per §6.e.1", actor_user_id=ACTOR,
    )
    recorded = result["recorded"][0]
    assert recorded["kind"] == "extension_agreed"
    assert recorded["target_clock_key"] == EXTENDABLE_CLOCK
    assert recorded["extension_days"] == 30
    assert recorded["written_agreement_ref"] == "Letter dated 2026-01-14, signed by applicant and CEO"

    # The events audit row (CONTRACT.md §3.3) carries the same written
    # agreement reference -- an inspector reading the audit trail alone can
    # see WHY the deadline moved.
    events = cases_mod.case_history_for(conn, case["id"])
    dates_events = [e for e in events if e["kind"] == "case.dates_recorded"]
    assert len(dates_events) == 1
    payload_entry = dates_events[0]["payload"]["entries"][0]
    assert payload_entry["written_agreement_ref"] == "Letter dated 2026-01-14, signed by applicant and CEO"
    assert payload_entry["extension_days"] == 30
    assert payload_entry["target_clock_key"] == EXTENDABLE_CLOCK

    # And it round-trips through the same read path the deadlines engine uses.
    row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case["id"],)).fetchone()
    milestones = conn.execute("SELECT * FROM case_milestones WHERE case_id = ?;", (case["id"],)).fetchall()
    facts = dl.case_facts_from_row(dict(row) | {"ruleset_key": "adopted"}, milestones)
    assert facts.clock_extension_days == {EXTENDABLE_CLOCK: 30}


def test_record_dates_extension_alias_accepted(conn):
    case = _make_case(conn)
    result = cases_mod.record_dates(
        conn, case["id"],
        entries=[{
            "kind": "extension", "occurred_on": "2026-01-15",
            "target_clock_key": EXTENDABLE_CLOCK, "extension_days": 10,
            "written_agreement_ref": "a letter",
        }],
        why="test", actor_user_id=ACTOR,
    )
    assert result["recorded"][0]["kind"] == "extension_agreed"


def test_record_dates_clock_waived_requires_note(conn):
    case = _make_case(conn)
    with pytest.raises(cases_mod.ValidationError) as ei:
        cases_mod.record_dates(
            conn, case["id"],
            entries=[{"kind": "clock_waived", "occurred_on": "2026-01-16", "target_clock_key": EXTENDABLE_CLOCK}],
            why="test", actor_user_id=ACTOR,
        )
    assert ei.value.details[0]["field"] == "dates[0].note"


def test_record_dates_clock_waived_valid_populates_waived_clocks(conn):
    case = _make_case(conn)
    cases_mod.record_dates(
        conn, case["id"],
        entries=[{
            "kind": "clock_waived", "occurred_on": "2026-01-16",
            "target_clock_key": EXTENDABLE_CLOCK, "note": "Board waived per vote 2026-01-16",
        }],
        why="test", actor_user_id=ACTOR,
    )
    row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case["id"],)).fetchone()
    milestones = conn.execute("SELECT * FROM case_milestones WHERE case_id = ?;", (case["id"],)).fetchall()
    facts = dl.case_facts_from_row(dict(row) | {"ruleset_key": "adopted"}, milestones)
    assert facts.waived_clocks == frozenset({EXTENDABLE_CLOCK})


def test_record_dates_rejects_target_clock_key_on_an_ordinary_kind(conn):
    case = _make_case(conn)
    with pytest.raises(cases_mod.ValidationError):
        cases_mod.record_dates(
            conn, case["id"],
            entries=[{
                "kind": "hearing_closed", "occurred_on": "2026-01-01",
                "target_clock_key": EXTENDABLE_CLOCK,
            }],
            why="test", actor_user_id=ACTOR,
        )


# --------------------------------------------------------------------------- #
# Layer 3 -- app/main.py HTTP/template: the auto-approval banner
# --------------------------------------------------------------------------- #


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "permit-review.db"
    conn = db_mod.connect(db_path)
    db_mod.migrate(conn, app_main.MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    _seed_rulesets(conn)
    conn.close()

    monkeypatch.setattr(app_main, "DB_PATH", db_path)
    monkeypatch.setattr(app_main, "DATA_DIR", tmp_path)
    from app import config as config_mod
    monkeypatch.setattr(config_mod, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config_mod, "BLOBS_DIR", tmp_path / "blobs")

    app = app_main.create_app(port=8781)
    with TestClient(app, base_url="http://127.0.0.1:8781") as c:
        c._db_path = db_path  # type: ignore[attr-defined]
        yield c


def _create_case(db_path: Path, **overrides) -> dict:
    conn = db_mod.connect(db_path)
    try:
        kwargs = dict(application_type="special_permit", actor_user_id=ACTOR)
        kwargs.update(overrides)
        return cases_mod.create_case(conn, **kwargs)
    finally:
        conn.close()


def _record_dates(db_path: Path, case_id: str, entries: list, why: str = "seed") -> None:
    conn = db_mod.connect(db_path)
    try:
        cases_mod.record_dates(conn, case_id, entries=entries, why=why, actor_user_id=ACTOR)
    finally:
        conn.close()


def test_case_detail_page_before_and_after_a_lawful_extension(client):
    # app/main.py's case-detail route computes deadlines as of REAL
    # date.today() (it does not accept an as_of override), so this repro
    # uses a hearing-closed date recent enough that the ORIGINAL 45-day
    # decision clock has already passed today but a +30-day extension pushes
    # its due date safely into the future relative to today, whatever today
    # happens to be when this test runs (today - 50 days is always already
    # 45+ days in the past; +30 days on top of that always lands after
    # today). This keeps the test correct regardless of the current date.
    hearing_closed = date.today().fromordinal(date.today().toordinal() - 50)
    case = _create_case(client._db_path)
    _record_dates(client._db_path, case["id"], [{"kind": "hearing_closed", "occurred_on": hearing_closed.isoformat()}])

    resp_before = client.get(f"/cases/{case['id']}")
    assert resp_before.status_code == 200
    # BEFORE: the case-level auto-approval banner is showing (matches
    # test_unextended_clock_still_presents_auto_approval_risk's engine-level
    # assertion, exercised end to end through the real HTTP page render).
    assert "automatic approval" in resp_before.text

    _record_dates(client._db_path, case["id"], [{
        "kind": "extension_agreed", "occurred_on": "2026-01-15",
        "target_clock_key": EXTENDABLE_CLOCK, "extension_days": 30,
        "written_agreement_ref": "Letter dated 2026-01-14, signed by applicant and CEO",
    }], why="agreed extension")

    resp_after = client.get(f"/cases/{case['id']}")
    assert resp_after.status_code == 200
    # AFTER: the false banner is gone, and the extension is visible both in
    # the deadlines table ("see which clocks it moved") and the Key Dates
    # audit trail (the written-agreement reference).
    assert "automatic approval" not in resp_after.text
    assert "extended +30" in resp_after.text
    assert "Letter dated 2026-01-14, signed by applicant and CEO" in resp_after.text


def test_case_detail_page_offers_the_extension_form_with_only_eligible_clocks(client):
    case = _create_case(client._db_path)
    _record_dates(client._db_path, case["id"], [{"kind": "hearing_closed", "occurred_on": "2026-01-01"}])
    resp = client.get(f"/cases/{case['id']}")
    assert resp.status_code == 200
    assert "add-extension-form" in resp.text
    extension_form_html = resp.text.split('id="add-extension-form"')[1].split("</form>")[0]
    assert f'value="{EXTENDABLE_CLOCK}"' in extension_form_html
    assert f'value="{INELIGIBLE_CLOCK}"' not in extension_form_html
    # The override form (waive / n-a), by contrast, DOES offer the
    # ineligible-for-extension clock -- §6.e.1 narrows extension eligibility,
    # not waiver/n-a eligibility.
    assert "add-override-form" in resp.text
    override_form_html = resp.text.split('id="add-override-form"')[1].split("</form>")[0]
    assert f'value="{INELIGIBLE_CLOCK}"' in override_form_html
