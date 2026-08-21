"""Tests app/cases.py (the case lifecycle business logic) and
app/routes/cases.py (its HTTP layer) against the W3 task brief and
CONTRACT.md §3.2/§3.3.

Offline, no network, no LLM, no PII — a throwaway temp-dir SQLite file per
test via the `conn` fixture (migrated, given the synthetic actor row, and
seeded with one binding ('adopted') and one non-binding ('draft-x') ruleset
row, matching the shape ruleset_build/build_ruleset.py's step 5 writes).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit, cases, db, security  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"

ADOPTED_ID = "r_adopted"
DRAFT_ID = "r_draft"


def _seed_rulesets(conn: sqlite3.Connection) -> None:
    now = "2026-08-20T00:00:00.000Z"
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, 'adopted', 'Newcastle Core Zoning Code (adopted)', 1, 'adopted', NULL,
                ?, 'ruleset_build/1.0.0', 'rulesets/adopted/manifest.json', '{}', 1, NULL, ?, NULL);
        """,
        (ADOPTED_ID, now, now),
    )
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, 'draft-x', 'CZC draft-x', 0, 'draft', NULL,
                ?, 'ruleset_build/1.0.0', 'rulesets/draft-x/manifest.json', '{}', 0, NULL, ?, NULL);
        """,
        (DRAFT_ID, now, now),
    )


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    _seed_rulesets(c)
    try:
        yield c
    finally:
        c.close()


ACTOR = security.SYNTHETIC_USER_ID


def _make_case(conn: sqlite3.Connection, **overrides):
    kwargs = dict(
        application_type="subdivision",
        map_lot="M003, L059",
        situs_address="White Rd",
        applicant_name="Shattuck",
        actor_user_id=ACTOR,
    )
    kwargs.update(overrides)
    return cases.create_case(conn, **kwargs)


# --------------------------------------------------------------------------- #
# create_case — defaulting, labeling, validation
# --------------------------------------------------------------------------- #


def test_create_case_defaults_to_adopted_binding_ruleset_and_intake_status(conn):
    case = _make_case(conn)
    assert case["ruleset_id"] == ADOPTED_ID
    assert case["status"] == "intake"
    assert case["is_scratch"] is False
    assert case["binding_override"] is False
    assert case["label"] == "M003, L059 (White Rd, Shattuck)"


def test_create_case_explicit_label_overrides_derived_one(conn):
    case = _make_case(conn, label="Custom Label")
    assert case["label"] == "Custom Label"


def test_create_case_rejects_bad_application_type(conn):
    with pytest.raises(cases.ValidationError) as ei:
        _make_case(conn, application_type="not_a_real_type")
    assert ei.value.details[0]["field"] == "application_type"


def test_create_case_rejects_unknown_ruleset_key(conn):
    with pytest.raises(cases.UnknownRuleset):
        _make_case(conn, ruleset_key="does-not-exist")


# --------------------------------------------------------------------------- #
# The binding gate (CONTRACT.md §1 S8 / §3.2) + the audited override
# --------------------------------------------------------------------------- #


def test_real_case_against_nonbinding_ruleset_refused_without_override(conn):
    with pytest.raises(cases.NonBindingRulesetRefused):
        _make_case(conn, ruleset_key="draft-x")

    # Nothing was written — refusal happens before any INSERT.
    assert conn.execute("SELECT COUNT(*) AS n FROM cases;").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM events;").fetchone()["n"] == 0


def test_real_case_against_nonbinding_ruleset_requires_a_reason(conn):
    with pytest.raises(cases.ValidationError) as ei:
        _make_case(conn, ruleset_key="draft-x", binding_override=True)
    assert ei.value.details[0]["field"] == "override_reason"


def test_real_case_against_nonbinding_ruleset_accepted_with_override(conn):
    case = _make_case(
        conn, ruleset_key="draft-x", binding_override=True,
        override_reason="Board pre-authorized a dry run against the pending draft.",
    )
    assert case["ruleset_id"] == DRAFT_ID
    assert case["binding_override"] is True
    assert case["override_reason"] == "Board pre-authorized a dry run against the pending draft."


def test_scratch_case_against_nonbinding_ruleset_needs_no_override(conn):
    case = _make_case(conn, ruleset_key="draft-x", is_scratch=True)
    assert case["is_scratch"] is True
    assert case["binding_override"] is False


# --------------------------------------------------------------------------- #
# Status transitions — the state machine
# --------------------------------------------------------------------------- #


def test_full_linear_chain_is_valid(conn):
    case = _make_case(conn)
    chain = ["extracting", "review", "draft_issued", "meeting", "decided", "closed"]
    for to_status in chain:
        case = cases.transition_status(conn, case["id"], to_status=to_status, why="advancing", actor_user_id=ACTOR)
        assert case["status"] == to_status


@pytest.mark.parametrize("from_status", ["intake", "extracting", "review", "draft_issued", "meeting"])
def test_withdrawn_reachable_from_any_nonterminal_status(conn, from_status):
    case = _make_case(conn)
    # Walk to from_status first.
    for step in ("extracting", "review", "draft_issued", "meeting"):
        if case["status"] == from_status:
            break
        case = cases.transition_status(conn, case["id"], to_status=step, why="advancing", actor_user_id=ACTOR)
    assert case["status"] == from_status
    case = cases.transition_status(conn, case["id"], to_status="withdrawn", why="applicant pulled it", actor_user_id=ACTOR)
    assert case["status"] == "withdrawn"


@pytest.mark.parametrize("bad_target", ["review", "draft_issued", "meeting", "decided", "closed"])
def test_intake_cannot_skip_ahead(conn, bad_target):
    case = _make_case(conn)
    with pytest.raises(cases.InvalidTransition) as ei:
        cases.transition_status(conn, case["id"], to_status=bad_target, why="skip", actor_user_id=ACTOR)
    assert ei.value.from_status == "intake"
    assert ei.value.to_status == bad_target
    # Nothing was mutated.
    assert cases.get_case(conn, case["id"])["status"] == "intake"


@pytest.mark.parametrize("terminal", ["closed", "withdrawn"])
def test_terminal_statuses_accept_no_further_transition(conn, terminal):
    case = _make_case(conn)
    case = cases.transition_status(conn, case["id"], to_status=terminal if terminal == "withdrawn" else "extracting",
                                    why="setup", actor_user_id=ACTOR)
    if terminal == "closed":
        for step in ("review", "draft_issued", "meeting", "decided", "closed"):
            case = cases.transition_status(conn, case["id"], to_status=step, why="advancing", actor_user_id=ACTOR)
    assert case["status"] == terminal
    with pytest.raises(cases.InvalidTransition):
        cases.transition_status(conn, case["id"], to_status="intake", why="nope", actor_user_id=ACTOR)


def test_transition_requires_a_reason(conn):
    case = _make_case(conn)
    with pytest.raises(cases.ValidationError) as ei:
        cases.transition_status(conn, case["id"], to_status="extracting", why="   ", actor_user_id=ACTOR)
    assert ei.value.details[0]["field"] == "why"


def test_transition_on_unknown_case_raises_not_found(conn):
    with pytest.raises(cases.CaseNotFound):
        cases.transition_status(conn, "nope", to_status="extracting", why="x", actor_user_id=ACTOR)


# --------------------------------------------------------------------------- #
# Key dates — hearing opened/closed at different meetings, re-notice history
# --------------------------------------------------------------------------- #


def test_hearing_opened_and_closed_at_different_meetings(conn):
    case = _make_case(conn)
    cases.record_dates(
        conn, case["id"],
        entries=[
            {"kind": "application_received", "occurred_on": "2025-10-02"},
            {"kind": "hearing_opened", "occurred_on": "2025-11-20"},
        ],
        why="initial intake + hearing opened", actor_user_id=ACTOR,
    )
    cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "hearing_closed", "occurred_on": "2025-12-18"},
                 {"kind": "decision", "occurred_on": "2025-12-18"}],
        why="hearing closed, decided same night", actor_user_id=ACTOR,
    )
    rows = cases.case_dates_for(conn, case["id"])
    kinds = {r["kind"]: r["occurred_on"] for r in rows}
    assert kinds["hearing_opened"] == "2025-11-20"
    assert kinds["hearing_closed"] == "2025-12-18"
    assert kinds["decision_issued"] == "2025-12-18"  # "decision" alias stored under decision_issued
    assert len(rows) == 4


def test_reschedule_and_renotice_does_not_destroy_the_original_record(conn):
    case = _make_case(conn)
    original = cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "notice_mailed", "occurred_on": "2025-09-25",
                  "note": "notice for the original Oct 16 hearing date"}],
        why="original notice", actor_user_id=ACTOR,
    )
    original_id = original["recorded"][0]["id"]

    cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "notice_mailed", "occurred_on": "2025-11-04",
                  "note": "re-notice for the rescheduled Nov 20 hearing",
                  "supersedes_id": original_id, "supersede_reason": "reschedule"}],
        why="hearing rescheduled and re-noticed", actor_user_id=ACTOR,
    )

    rows = {r["id"]: r for r in cases.case_dates_for(conn, case["id"])}
    assert len(rows) == 2  # both rows still present — nothing destroyed
    assert rows[original_id]["occurred_on"] == "2025-09-25"
    assert rows[original_id]["superseded_by"] is not None
    assert rows[original_id]["supersede_reason"] == "reschedule"  # N3
    new_id = rows[original_id]["superseded_by"]
    assert rows[new_id]["occurred_on"] == "2025-11-04"
    assert rows[new_id]["superseded_by"] is None


def test_record_dates_requires_supersede_reason_when_supersedes_id_is_given(conn):
    """N3: supersede_reason is REQUIRED, not inferred, whenever supersedes_id
    is given -- CONTRACT.md §1 S7 (no silent guessing)."""
    case = _make_case(conn)
    original = cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "notice_mailed", "occurred_on": "2025-09-25"}],
        why="original notice", actor_user_id=ACTOR,
    )
    original_id = original["recorded"][0]["id"]

    with pytest.raises(cases.ValidationError) as excinfo:
        cases.record_dates(
            conn, case["id"],
            entries=[{"kind": "notice_mailed", "occurred_on": "2025-11-04",
                      "supersedes_id": original_id}],  # no supersede_reason
            why="missing reason", actor_user_id=ACTOR,
        )
    assert any(d["field"] == "dates[0].supersede_reason" for d in excinfo.value.details)

    # Nothing was written -- validate-all-then-write (CONTRACT.md §1 S1).
    rows = cases.case_dates_for(conn, case["id"])
    assert len(rows) == 1
    assert rows[0]["superseded_by"] is None

    with pytest.raises(cases.ValidationError) as excinfo:
        cases.record_dates(
            conn, case["id"],
            entries=[{"kind": "notice_mailed", "occurred_on": "2025-11-04",
                      "supersedes_id": original_id, "supersede_reason": "bogus"}],
            why="bad reason", actor_user_id=ACTOR,
        )
    assert any(d["field"] == "dates[0].supersede_reason" for d in excinfo.value.details)


def test_record_dates_mirrors_meeting_date_and_recomputes_draft_due(conn):
    case = _make_case(conn)
    from app.dates import draft_due

    result = cases.record_dates(
        conn, case["id"], entries=[{"kind": "meeting", "occurred_on": "2026-09-17"}],
        why="on the Sept packet", actor_user_id=ACTOR,
    )
    updated = result["case"]
    assert updated["meeting_date"] == "2026-09-17"
    from datetime import date
    assert updated["draft_due"] == draft_due(date(2026, 9, 17)).isoformat()


def test_record_dates_rejects_unknown_kind(conn):
    case = _make_case(conn)
    with pytest.raises(cases.ValidationError) as ei:
        cases.record_dates(conn, case["id"], entries=[{"kind": "made_up", "occurred_on": "2025-01-01"}],
                            why="x", actor_user_id=ACTOR)
    assert "kind" in ei.value.details[0]["field"]


def test_record_dates_requires_at_least_one_entry(conn):
    case = _make_case(conn)
    with pytest.raises(cases.ValidationError):
        cases.record_dates(conn, case["id"], entries=[], why="x", actor_user_id=ACTOR)


def test_record_dates_on_unknown_case_raises_not_found(conn):
    with pytest.raises(cases.CaseNotFound):
        cases.record_dates(conn, "nope", entries=[{"kind": "meeting", "occurred_on": "2026-01-01"}],
                            why="x", actor_user_id=ACTOR)


# --------------------------------------------------------------------------- #
# F5 -- occurred_on must be a real ISO date, validated at the boundary
# (CONTRACT.md §1 S1). Before this fix, app/cases.py:541 accepted any
# non-empty string; one bad value (e.g. "December 18, 2025") wrote straight
# into the append-only case_milestones table and 500'd every later read of
# the case (engine.deadlines._parse_date only knows fromisoformat).
# --------------------------------------------------------------------------- #


def test_record_dates_rejects_a_non_iso_occurred_on_and_writes_nothing(conn):
    case = _make_case(conn)
    with pytest.raises(cases.ValidationError) as ei:
        cases.record_dates(
            conn, case["id"],
            entries=[{"kind": "application_received", "occurred_on": "December 18, 2025"}],
            why="x", actor_user_id=ACTOR,
        )
    assert "occurred_on" in ei.value.details[0]["field"]
    # CONTRACT.md §1 S1: validate-all-then-write -- nothing reaches disk.
    assert cases.case_dates_for(conn, case["id"]) == []


@pytest.mark.parametrize("bad", [
    "not-a-date", "2025-13-40", "2025/10/02", "", "   ", "10-02-2025",
])
def test_record_dates_rejects_various_malformed_occurred_on_values(conn, bad):
    case = _make_case(conn)
    with pytest.raises(cases.ValidationError):
        cases.record_dates(
            conn, case["id"],
            entries=[{"kind": "meeting", "occurred_on": bad}],
            why="x", actor_user_id=ACTOR,
        )


def test_record_dates_accepts_a_datetime_style_occurred_on(conn):
    # engine.deadlines._parse_date only inspects the first 10 characters --
    # a trailing time-of-day must still be accepted, matching that reader.
    case = _make_case(conn)
    result = cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "meeting", "occurred_on": "2026-09-17T18:30:00"}],
        why="x", actor_user_id=ACTOR,
    )
    assert result["recorded"][0]["occurred_on"] == "2026-09-17T18:30:00"


def test_record_dates_batch_rejects_the_whole_batch_if_any_entry_is_bad(conn):
    # S1 again, across a multi-entry batch: one bad occurred_on must not let
    # the OTHER, valid entries in the same call through.
    case = _make_case(conn)
    with pytest.raises(cases.ValidationError):
        cases.record_dates(
            conn, case["id"],
            entries=[
                {"kind": "application_received", "occurred_on": "2025-10-02"},
                {"kind": "completeness_determined", "occurred_on": "not-a-date"},
            ],
            why="x", actor_user_id=ACTOR,
        )
    assert cases.case_dates_for(conn, case["id"]) == []


def test_correcting_a_bad_occurred_on_via_supersedes_id_is_the_repair_path(conn):
    # The repair path for a row that predates this validation (or slipped in
    # some other way): record a NEW, valid entry with supersedes_id pointing
    # at the bad row. case_milestones stays append-only -- nothing is edited
    # or deleted -- but the bad row drops out of the LIVE
    # (superseded_by IS NULL) set every read path queries.
    case = _make_case(conn)
    now = "2026-08-20T00:00:00.000Z"
    bad_id = "m_bad"
    conn.execute(
        """
        INSERT INTO case_milestones
            (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id)
        VALUES (?, ?, 'application_received', 'December 18, 2025', NULL, NULL, ?, ?);
        """,
        (bad_id, case["id"], now, ACTOR),
    )

    cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "application_received", "occurred_on": "2025-12-18",
                  "note": "correcting a malformed row", "supersedes_id": bad_id,
                  "supersede_reason": "correction"}],
        why="fixing a bad historical value", actor_user_id=ACTOR,
    )

    rows = {r["id"]: r for r in cases.case_dates_for(conn, case["id"])}
    assert rows[bad_id]["superseded_by"] is not None  # kept, marked superseded
    new_id = rows[bad_id]["superseded_by"]
    assert rows[new_id]["occurred_on"] == "2025-12-18"

    from engine.deadlines import load_all_case_facts
    facts_by_id = {f.case_id: f for f in load_all_case_facts(conn)}
    # Now readable without raising -- the bad row is excluded (superseded).
    assert facts_by_id[case["id"]].submitted_at.isoformat() == "2025-12-18"


# --------------------------------------------------------------------------- #
# list_cases / get_case
# --------------------------------------------------------------------------- #


def test_list_cases_filters_by_status_and_scratch(conn):
    a = _make_case(conn, map_lot="A")
    b = _make_case(conn, map_lot="B", ruleset_key="draft-x", is_scratch=True)
    cases.transition_status(conn, a["id"], to_status="extracting", why="x", actor_user_id=ACTOR)

    intake_only = cases.list_cases(conn, status="intake")
    assert {c["id"] for c in intake_only} == {b["id"]}

    scratch_only = cases.list_cases(conn, is_scratch=True)
    assert {c["id"] for c in scratch_only} == {b["id"]}

    adopted_only = cases.list_cases(conn, ruleset_key="adopted")
    assert {c["id"] for c in adopted_only} == {a["id"]}


def test_get_case_returns_none_for_unknown_id(conn):
    assert cases.get_case(conn, "nope") is None


# --------------------------------------------------------------------------- #
# Every mutation appends exactly one event; the chain still verifies.
# --------------------------------------------------------------------------- #


def _event_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) AS n FROM events;").fetchone()["n"]


def test_every_mutation_appends_exactly_one_event_and_chain_verifies(conn):
    assert _event_count(conn) == 0

    case = _make_case(conn)
    assert _event_count(conn) == 1
    assert audit.verify_chain(conn) == (True, None)

    cases.transition_status(conn, case["id"], to_status="extracting", why="x", actor_user_id=ACTOR)
    assert _event_count(conn) == 2
    assert audit.verify_chain(conn) == (True, None)

    cases.record_dates(
        conn, case["id"],
        entries=[{"kind": "application_received", "occurred_on": "2025-10-02"},
                 {"kind": "completeness", "occurred_on": "2025-10-16"}],
        why="batch of two dates in one call", actor_user_id=ACTOR,
    )
    # A batch of several date entries is still ONE mutation -> ONE event.
    assert _event_count(conn) == 3
    assert audit.verify_chain(conn) == (True, None)

    # A rejected mutation (invalid transition) appends nothing.
    with pytest.raises(cases.InvalidTransition):
        cases.transition_status(conn, case["id"], to_status="closed", why="skip ahead", actor_user_id=ACTOR)
    assert _event_count(conn) == 3
    assert audit.verify_chain(conn) == (True, None)

    events = cases.case_history_for(conn, case["id"])
    assert [e["kind"] for e in events] == ["case.created", "case.status_changed", "case.dates_recorded"]
