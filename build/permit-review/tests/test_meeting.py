"""Tests app/meeting.py -- the W7 "meeting model" task: conflict
disclosures, completeness/contested-node motions and their votes,
attendance, and the case outcome (CONTRACT.md §3.5's `attendance`,
`conflict_disclosures`, `motions`, `decisions` tables).

Offline, throwaway temp-dir SQLite, mirrors tests/test_cases.py's `conn`
fixture + `_seed_rulesets`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit, cases, db, meeting, security  # noqa: E402

from tests.test_cases import ADOPTED_ID, _seed_rulesets  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"
ACTOR = security.SYNTHETIC_USER_ID


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


def _make_case(conn, **overrides) -> dict:
    kwargs = dict(
        application_type="subdivision",
        map_lot="M003, L059",
        situs_address="White Rd",
        applicant_name="Kathleen Shattuck (fictional test fixture)",
        actor_user_id=ACTOR,
    )
    kwargs.update(overrides)
    return cases.create_case(conn, **kwargs)


def _seed_board(conn) -> tuple[str, str]:
    """Two sitting members, mirroring the real Board's Chair-plus-others
    shape used throughout docs/Findings of Fact and Conclusions of Law/.
    Returns (chair_board_member_id, member_board_member_id)."""
    conn.execute(
        "INSERT INTO users (id, display_name, role, created_at) VALUES "
        "('u_chair', 'Ben Frey', 'chair', '2026-08-20T00:00:00.000Z'), "
        "('u_member', 'Lucas Kostenbader', 'board_member', '2026-08-20T00:00:00.000Z');"
    )
    conn.execute(
        "INSERT INTO board_members (id, user_id, is_chair, term_start, created_at) VALUES "
        "('bm_chair', 'u_chair', 1, '2026-01-01', '2026-08-20T00:00:00.000Z'), "
        "('bm_member', 'u_member', 0, '2026-01-01', '2026-08-20T00:00:00.000Z');"
    )
    return "bm_chair", "bm_member"


# --------------------------------------------------------------------------- #
# Attendance
# --------------------------------------------------------------------------- #


def test_record_attendance_inserts_and_appends_one_event(conn):
    case = _make_case(conn)
    bm_chair, _ = _seed_board(conn)

    row = meeting.record_attendance(
        conn, case_id=case["id"], board_member_id=bm_chair, present=True, actor_user_id=ACTOR,
    )
    assert row["present"] == 1
    assert row["case_id"] == case["id"]

    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'attendance' AND entity_id = ?;", (row["id"],)
    ).fetchall()
    assert [e["kind"] for e in events] == ["attendance.recorded"]
    ok, bad_seq = audit.verify_chain(conn)
    assert ok, f"hash chain broken at seq={bad_seq}"


def test_record_attendance_twice_corrects_in_place_not_a_second_row(conn):
    case = _make_case(conn)
    bm_chair, _ = _seed_board(conn)

    first = meeting.record_attendance(
        conn, case_id=case["id"], board_member_id=bm_chair, present=True, actor_user_id=ACTOR,
    )
    second = meeting.record_attendance(
        conn, case_id=case["id"], board_member_id=bm_chair, present=False,
        role_note="left before the vote", actor_user_id=ACTOR,
    )
    assert second["id"] == first["id"]
    assert second["present"] == 0
    assert second["role_note"] == "left before the vote"

    rows = conn.execute("SELECT * FROM attendance WHERE case_id = ?;", (case["id"],)).fetchall()
    assert len(rows) == 1

    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'attendance' ORDER BY seq;"
    ).fetchall()
    assert [e["kind"] for e in events] == ["attendance.recorded", "attendance.corrected"]


def test_get_attendance_empty_for_a_case_with_no_roll_call(conn):
    case = _make_case(conn)
    assert meeting.get_attendance(conn, case["id"]) == []


def test_get_attendance_orders_chair_first(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    meeting.record_attendance(conn, case_id=case["id"], board_member_id=bm_member, actor_user_id=ACTOR)
    meeting.record_attendance(conn, case_id=case["id"], board_member_id=bm_chair, actor_user_id=ACTOR)

    rows = meeting.get_attendance(conn, case["id"])
    assert [r["member_name"] for r in rows] == ["Ben Frey", "Lucas Kostenbader"]


# --------------------------------------------------------------------------- #
# Conflict-of-interest disclosures -- the zero-rows behavior is the
# decisive test for this whole module (task brief: "ZERO rows must render
# as the real drafts do -- a TBD/blank, never 'no conflicts declared'").
# --------------------------------------------------------------------------- #


def test_conflict_disclosures_summary_is_not_recorded_when_no_roll_call_happened(conn):
    case = _make_case(conn)
    _seed_board(conn)
    # No conflict_disclosures rows written at all -- this MUST NOT be
    # mistaken for "the Board considered it and found none."
    summary = meeting.conflict_disclosures_summary(conn, case["id"])
    assert summary["status"] == "not_recorded"
    assert summary["rows"] == ()
    assert meeting.get_conflict_disclosures(conn, case["id"]) == []


def test_conflict_disclosures_summary_none_disclosed_after_a_real_roll_call(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=bm_chair, disclosed=False, actor_user_id=ACTOR,
    )
    meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=bm_member, disclosed=False, actor_user_id=ACTOR,
    )
    summary = meeting.conflict_disclosures_summary(conn, case["id"])
    assert summary["status"] == "none_disclosed"
    assert summary["rows"] == ()


def test_conflict_disclosures_summary_disclosed_carries_only_disclosing_members(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=bm_chair, disclosed=False, actor_user_id=ACTOR,
    )
    meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=bm_member, disclosed=True, recused=True,
        nature="abutting property owner", actor_user_id=ACTOR,
    )
    summary = meeting.conflict_disclosures_summary(conn, case["id"])
    assert summary["status"] == "disclosed"
    assert len(summary["rows"]) == 1
    assert summary["rows"][0]["member_name"] == "Lucas Kostenbader"
    assert summary["rows"][0]["recused"] == 1


def test_recused_without_disclosed_is_rejected(conn):
    case = _make_case(conn)
    bm_chair, _ = _seed_board(conn)
    with pytest.raises(meeting.ValidationError):
        meeting.record_conflict_disclosure(
            conn, case_id=case["id"], board_member_id=bm_chair, disclosed=False, recused=True,
            actor_user_id=ACTOR,
        )
    # Nothing written -- the DB-level CHECK backs this up too, but the
    # app-level rejection must fire first (a clean ValidationError, not a
    # raw sqlite3.IntegrityError), and it must not have started a
    # transaction that left a half-written row behind.
    assert meeting.get_conflict_disclosures(conn, case["id"]) == []


def test_recused_without_disclosed_would_also_fail_the_db_check_directly(conn):
    # Confirms the DB-level backstop this module's app-level check mirrors
    # is real, not just documented in a comment.
    case = _make_case(conn)
    bm_chair, _ = _seed_board(conn)
    with pytest.raises(Exception):  # sqlite3.IntegrityError
        conn.execute(
            """
            INSERT INTO conflict_disclosures
                (id, case_id, board_member_id, disclosed, recused, created_at)
            VALUES ('cd_bad', ?, ?, 0, 1, '2026-08-20T00:00:00.000Z');
            """,
            (case["id"], bm_chair),
        )


def test_record_conflict_disclosure_corrects_in_place(conn):
    case = _make_case(conn)
    bm_chair, _ = _seed_board(conn)
    first = meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=bm_chair, disclosed=False, actor_user_id=ACTOR,
    )
    second = meeting.record_conflict_disclosure(
        conn, case_id=case["id"], board_member_id=bm_chair, disclosed=True, recused=True,
        nature="family member of applicant", actor_user_id=ACTOR,
    )
    assert second["id"] == first["id"]
    rows = conn.execute("SELECT * FROM conflict_disclosures WHERE case_id = ?;", (case["id"],)).fetchall()
    assert len(rows) == 1
    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'conflict_disclosures' ORDER BY seq;"
    ).fetchall()
    assert [e["kind"] for e in events] == [
        "conflict_disclosure.recorded", "conflict_disclosure.corrected",
    ]


# --------------------------------------------------------------------------- #
# Motions -- completeness determination is `kind='completeness'`.
# --------------------------------------------------------------------------- #


def test_create_motion_drafts_with_vote_fields_null(conn):
    case = _make_case(conn)
    motion = meeting.create_motion(
        conn, case_id=case["id"], kind="completeness",
        text="To find the application to be complete as of August 21, 2026.",
        actor_user_id=ACTOR,
    )
    assert motion["kind"] == "completeness"
    assert motion["moved_by"] is None
    assert motion["outcome"] is None
    assert motion["votes_yes"] is None


def test_create_motion_rejects_unknown_kind(conn):
    case = _make_case(conn)
    with pytest.raises(meeting.ValidationError):
        meeting.create_motion(conn, case_id=case["id"], kind="not-a-kind", text="x", actor_user_id=ACTOR)


def test_create_motion_rejects_empty_text(conn):
    case = _make_case(conn)
    with pytest.raises(meeting.ValidationError):
        meeting.create_motion(conn, case_id=case["id"], kind="completeness", text="   ", actor_user_id=ACTOR)


def test_record_vote_fills_in_the_drafted_motion(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    motion = meeting.create_motion(
        conn, case_id=case["id"], kind="completeness",
        text="To find the application to be complete as of August 21, 2026.",
        actor_user_id=ACTOR,
    )
    voted = meeting.record_vote(
        conn, motion_id=motion["id"], moved_by=bm_chair, seconded_by=bm_member,
        votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    assert voted["outcome"] == "carried"
    assert voted["votes_yes"] == 2
    assert voted["voted_at"] is not None
    assert voted["recorded_by"] == ACTOR

    events = [
        e["kind"] for e in conn.execute(
            "SELECT kind FROM events WHERE entity_table = 'motions' ORDER BY seq;"
        ).fetchall()
    ]
    assert events == ["motion.created", "motion.voted"]


def test_record_vote_requires_a_named_human_recorder(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    motion = meeting.create_motion(
        conn, case_id=case["id"], kind="completeness", text="x", actor_user_id=ACTOR,
    )
    with pytest.raises(meeting.ValidationError):
        meeting.record_vote(
            conn, motion_id=motion["id"], moved_by=bm_chair, seconded_by=bm_member,
            votes_yes=2, votes_no=0, votes_abstain=0, outcome="carried",
            recorded_by="", actor_user_id=ACTOR,
        )
    # the row must still show no outcome -- rejected before any write
    row = conn.execute("SELECT outcome FROM motions WHERE id = ?;", (motion["id"],)).fetchone()
    assert row["outcome"] is None


def test_record_vote_rejects_unknown_outcome(conn):
    case = _make_case(conn)
    bm_chair, bm_member = _seed_board(conn)
    motion = meeting.create_motion(conn, case_id=case["id"], kind="completeness", text="x", actor_user_id=ACTOR)
    with pytest.raises(meeting.ValidationError):
        meeting.record_vote(
            conn, motion_id=motion["id"], moved_by=bm_chair, seconded_by=bm_member,
            votes_yes=2, votes_no=0, votes_abstain=0, outcome="approved",
            recorded_by=ACTOR, actor_user_id=ACTOR,
        )


def test_get_motions_orders_by_sort_order(conn):
    case = _make_case(conn)
    meeting.create_motion(conn, case_id=case["id"], kind="completeness", text="first", sort_order=0, actor_user_id=ACTOR)
    meeting.create_motion(conn, case_id=case["id"], kind="decision", text="second", sort_order=1, actor_user_id=ACTOR)
    rows = meeting.get_motions(conn, case["id"])
    assert [r["text"] for r in rows] == ["first", "second"]


# --------------------------------------------------------------------------- #
# The case outcome.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("outcome", sorted(meeting.CASE_OUTCOMES))
def test_record_outcome_accepts_every_value_in_the_outcome_set(conn, outcome):
    # The task brief's outcome set -- approve / approve with conditions /
    # deny / table / withdraw -- maps onto decisions.outcome as: approved /
    # approved_with_conditions / denied / continued / withdrawn. See
    # 0017_meeting_attendance.sql's header for why 'continued' (not
    # 'tabled') is the schema's real word for "table" -- it is the one
    # Midcoast Solar's actual record uses.
    case = _make_case(conn)
    decision = meeting.record_outcome(
        conn, case_id=case["id"], ruleset_id=ADOPTED_ID, outcome=outcome,
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    assert decision["outcome"] == outcome
    assert decision["recorded_by"] == ACTOR
    assert decision["decided_at"] is not None


def test_record_outcome_rejects_unknown_outcome(conn):
    case = _make_case(conn)
    with pytest.raises(meeting.ValidationError):
        meeting.record_outcome(
            conn, case_id=case["id"], ruleset_id=ADOPTED_ID, outcome="rejected",
            recorded_by=ACTOR, actor_user_id=ACTOR,
        )


def test_record_outcome_requires_a_named_human_recorder(conn):
    case = _make_case(conn)
    with pytest.raises(meeting.ValidationError):
        meeting.record_outcome(
            conn, case_id=case["id"], ruleset_id=ADOPTED_ID, outcome="approved",
            recorded_by="", actor_user_id=ACTOR,
        )


def test_record_outcome_appends_exactly_one_event_in_the_same_transaction(conn):
    case = _make_case(conn)
    meeting.record_outcome(
        conn, case_id=case["id"], ruleset_id=ADOPTED_ID, outcome="approved_with_conditions",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    events = conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'decisions' AND case_id = ?;", (case["id"],)
    ).fetchall()
    assert [e["kind"] for e in events] == ["decision.recorded"]
    ok, bad_seq = audit.verify_chain(conn)
    assert ok, f"hash chain broken at seq={bad_seq}"


def test_reconsideration_is_a_new_decision_row_not_an_update(conn):
    case = _make_case(conn)
    first = meeting.record_outcome(
        conn, case_id=case["id"], ruleset_id=ADOPTED_ID, outcome="denied",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    second = meeting.record_outcome(
        conn, case_id=case["id"], ruleset_id=ADOPTED_ID, outcome="approved_with_conditions",
        recorded_by=ACTOR, actor_user_id=ACTOR,
    )
    assert first["id"] != second["id"]
    rows = meeting.get_decisions(conn, case["id"])
    assert len(rows) == 2
    assert meeting.get_current_decision(conn, case["id"])["id"] == second["id"]


def test_get_current_decision_none_when_never_decided(conn):
    case = _make_case(conn)
    assert meeting.get_current_decision(conn, case["id"]) is None
