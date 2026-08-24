"""W7 task: "the meeting model" -- conflict disclosures, completeness /
contested-node motions and their votes, attendance, and the case outcome.

Implements CONTRACT.md §3.5's `attendance` (0017_meeting_attendance.sql),
`conflict_disclosures`, `motions`, and `decisions` tables (the last three
already fully specified by 0001_init.sql -- "the full v1 schema" -- but,
before this module, had zero readers or writers anywhere in app/ or
engine/). Pure business logic + DB access, exactly the split app/cases.py
and engine/findings.py already establish: no FastAPI, no HTTP status
codes, no JSON envelope, every mutation wrapped in BEGIN/COMMIT with
exactly one `events` row in the same transaction (CONTRACT.md §3.3), a
raised exception writes nothing.

THE FRAMING RULE, restated for this module specifically: a `motions.outcome`
or `decisions.outcome` is a recorded human act, never an app-derived fact.
Both tables' own CHECK constraints already enforce this at the DB level
(`outcome IS NULL OR (recorded_by IS NOT NULL AND voted_at/decided_at IS NOT
NULL)`) -- this module's `record_vote()`/`record_outcome()` are the ONLY
place a caller can ever fill those columns, and both REQUIRE `recorded_by`
as a named human, matching engine/findings.py's `conclusion_by` requirement
for the identical reason.

ABSENCE OF A ROW IS NOT A FINDING. `conflict_disclosures_summary()` below is
the load-bearing function of this module: zero rows for a case means the
roll call has not happened yet, and must render as the real DRAFT samples
do -- a "TBD..." blank -- NEVER as "no conflicts declared". Only an actual
roll call (one row per attending board_member, `disclosed` explicitly 0 or
1) can produce the real adopted-final wording ("No Planning Board members
identified any potential conflicts of interest..."). See
render/case_findings.py's `_conflict_disclosures_render_node()` for where
this reaches the actual document.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.audit import append_event
from engine import findings as findings_engine
from engine import meeting as meeting_engine

# --------------------------------------------------------------------------- #
# Vocabulary -- single source of truth for this module; the CHECK constraints
# in app/migrations/0001_init.sql (motions, decisions, conflict_disclosures)
# and 0017_meeting_attendance.sql (attendance) are the DB-level mirror, kept
# in sync by hand -- same convention app/cases.py's own vocabulary block
# documents.
# --------------------------------------------------------------------------- #

#: motions.kind (0001_init.sql). 'completeness' is the Complete Application
#: motion the real Shattuck adopted final shows; 'findings' is the "accept
#: and adopt the draft findings of fact and conclusions of law, as amended"
#: motion (its text is lifted VERBATIM from that document by whichever W7
#: unit builds the adoption workflow -- this module does not compose it);
#: 'conditions' is the conditions-of-approval vote; 'decision' is the final
#: disposition vote; 'continuance' covers a vote to continue the case to a
#: future meeting (distinct from `decisions.outcome`'s 'continued' -- see
#: 0017_meeting_attendance.sql's note on why that word, not 'table', is
#: kept); 'other' is every per-standard or per-contested-node motion (the
#: Shattuck adopted final's one motion per Article/Standard).
MOTION_KINDS: frozenset[str] = frozenset({
    "completeness", "findings", "conditions", "decision", "continuance", "other",
})

#: motions.outcome (0001_init.sql) -- the PARLIAMENTARY result of one vote.
#: Distinct from decisions.outcome (the case's disposition, below):
#: a motion can be 'tabled' without the case itself being disposed of.
MOTION_OUTCOMES: frozenset[str] = frozenset({"carried", "failed", "tabled", "withdrawn"})

#: decisions.outcome (0001_init.sql) -- the Board's disposition of the whole
#: case. See 0017_meeting_attendance.sql's header for why 'continued' is
#: kept rather than renamed to the generic "table".
CASE_OUTCOMES: frozenset[str] = frozenset({
    "approved", "approved_with_conditions", "denied", "withdrawn", "continued",
})


class ValidationError(ValueError):
    """One or more fields failed validation. `.details` is a list of
    {"field": ..., "message": ...} dicts, matching app/cases.py's and
    engine/findings.py's ValidationError shape."""

    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        super().__init__(str(details))


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    """ISO-8601 UTC, 'Z' suffix, millisecond precision -- CONTRACT.md §3.3/§3.4."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _rollback_and_raise(conn: sqlite3.Connection, exc: BaseException) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK;")
    raise exc


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


# --------------------------------------------------------------------------- #
# Attendance
# --------------------------------------------------------------------------- #


def record_attendance(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    board_member_id: str,
    present: bool = True,
    role_note: str | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Record (or correct) one board_member's roll-call status for one
    case's meeting. First call for a (case_id, board_member_id) pair
    INSERTs (kind='attendance.recorded'); a later call for the SAME pair is
    a correction and UPDATEs the existing row in place (kind=
    'attendance.corrected') -- a roll call is a simple point-in-time fact
    with no adopted document ever quoting it back verbatim (unlike
    findings_nodes, which the Board amends on the record and which
    therefore keeps every prior revision), so an audited overwrite is
    enough: the `events` row is still the permanent, hash-chained record of
    what changed and when.
    """
    now = _utc_now_iso()
    existing = conn.execute(
        "SELECT id FROM attendance WHERE case_id = ? AND board_member_id = ?;",
        (case_id, board_member_id),
    ).fetchone()

    conn.execute("BEGIN;")
    try:
        if existing is None:
            row_id = _new_id()
            conn.execute(
                """
                INSERT INTO attendance
                    (id, case_id, board_member_id, present, role_note, recorded_at,
                     created_at, actor_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (row_id, case_id, board_member_id, int(present), role_note, now, now, actor_user_id),
            )
            kind = "attendance.recorded"
        else:
            row_id = existing["id"]
            conn.execute(
                """
                UPDATE attendance
                SET present = ?, role_note = ?, recorded_at = ?, actor_user_id = ?
                WHERE id = ?;
                """,
                (int(present), role_note, now, actor_user_id, row_id),
            )
            kind = "attendance.corrected"

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind=kind,
            payload={
                "attendance_id": row_id,
                "case_id": case_id,
                "board_member_id": board_member_id,
                "present": bool(present),
                "role_note": role_note,
            },
            case_id=case_id,
            entity_table="attendance",
            entity_id=row_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: roll back, then re-raise unchanged
        _rollback_and_raise(conn, exc)

    return _row_to_dict(conn.execute("SELECT * FROM attendance WHERE id = ?;", (row_id,)).fetchone())


def get_attendance(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every roll-call row for `case_id`, board_member's display name
    joined in, chair first then alphabetically -- empty list means no roll
    call has been recorded for this case yet (see this module's docstring:
    absence of a row is not a finding)."""
    rows = conn.execute(
        """
        SELECT a.*, u.display_name AS member_name, bm.is_chair AS is_chair
        FROM attendance a
        JOIN board_members bm ON bm.id = a.board_member_id
        JOIN users u ON u.id = bm.user_id
        WHERE a.case_id = ?
        ORDER BY bm.is_chair DESC, u.display_name;
        """,
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# Conflict-of-interest disclosures
# --------------------------------------------------------------------------- #


def record_conflict_disclosure(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    board_member_id: str,
    disclosed: bool,
    recused: bool = False,
    nature: str | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Record (or correct) one board_member's answer at the conflict-of-
    interest roll call. Mirrors record_attendance()'s INSERT-then-correct-
    by-UPDATE shape (same UNIQUE (case_id, board_member_id) pair on the
    underlying table).

    Raises ValidationError if `recused` is true while `disclosed` is false
    -- conflict_disclosures' own CHECK (0001_init.sql: "recused = 0 OR
    disclosed = 1") says the same thing at the DB level; this is the clean
    app-level error in front of it, matching every other vocabulary check
    in this module.
    """
    if recused and not disclosed:
        raise ValidationError([{
            "field": "recused",
            "message": "cannot be true when disclosed is false (conflict_disclosures CHECK)",
        }])

    now = _utc_now_iso()
    existing = conn.execute(
        "SELECT id FROM conflict_disclosures WHERE case_id = ? AND board_member_id = ?;",
        (case_id, board_member_id),
    ).fetchone()

    conn.execute("BEGIN;")
    try:
        if existing is None:
            row_id = _new_id()
            conn.execute(
                """
                INSERT INTO conflict_disclosures
                    (id, case_id, board_member_id, disclosed, recused, nature, disclosed_at,
                     created_at, actor_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (row_id, case_id, board_member_id, int(disclosed), int(recused), nature, now,
                 now, actor_user_id),
            )
            kind = "conflict_disclosure.recorded"
        else:
            row_id = existing["id"]
            conn.execute(
                """
                UPDATE conflict_disclosures
                SET disclosed = ?, recused = ?, nature = ?, disclosed_at = ?, actor_user_id = ?
                WHERE id = ?;
                """,
                (int(disclosed), int(recused), nature, now, actor_user_id, row_id),
            )
            kind = "conflict_disclosure.corrected"

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind=kind,
            payload={
                "conflict_disclosure_id": row_id,
                "case_id": case_id,
                "board_member_id": board_member_id,
                "disclosed": bool(disclosed),
                "recused": bool(recused),
                "nature": nature,
            },
            case_id=case_id,
            entity_table="conflict_disclosures",
            entity_id=row_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return _row_to_dict(
        conn.execute("SELECT * FROM conflict_disclosures WHERE id = ?;", (row_id,)).fetchone()
    )


def get_conflict_disclosures(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every disclosure roll-call row for `case_id`. Empty list means the
    roll call has not happened yet -- see conflict_disclosures_summary()."""
    rows = conn.execute(
        """
        SELECT cd.*, u.display_name AS member_name
        FROM conflict_disclosures cd
        JOIN board_members bm ON bm.id = cd.board_member_id
        JOIN users u ON u.id = bm.user_id
        WHERE cd.case_id = ?
        ORDER BY u.display_name;
        """,
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def conflict_disclosures_summary(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    """The three-way status render/case_findings.py's
    `_conflict_disclosures_render_node()` maps onto the document:

      - status == "not_recorded" -- ZERO rows. No roll call has happened
        yet. Renders as the honest "TBD..." blank, matching every
        pre-meeting DRAFT sample (Buehner, Verney, Blood and Sons, Z38) --
        NEVER as "no conflicts declared". `rows` is always `()` here.
      - status == "none_disclosed" -- one or more rows exist and NONE has
        disclosed=1. Renders as the real adopted-final wording verbatim
        ("No Planning Board members identified any potential conflicts of
        interest in taking up the submitted application for review.") --
        Shattuck and Uberoi's exact sentence.
      - status == "disclosed" -- at least one row has disclosed=1. `rows`
        carries only the disclosing members (name, disclosed, recused,
        nature) for the caller to narrate; this function does not compose
        that sentence (see render/case_findings.py, the one place DB text
        is escaped before reaching the document per CONTRACT.md §10.1's
        closing paragraph).
    """
    rows = get_conflict_disclosures(conn, case_id)
    if not rows:
        return {"status": "not_recorded", "rows": ()}
    disclosed_rows = tuple(r for r in rows if r["disclosed"])
    if not disclosed_rows:
        return {"status": "none_disclosed", "rows": ()}
    return {"status": "disclosed", "rows": disclosed_rows}


# --------------------------------------------------------------------------- #
# Motions (completeness, findings adoption, conditions, decision, ... )
# --------------------------------------------------------------------------- #


def create_motion(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    kind: str,
    text: str,
    sort_order: int = 0,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Draft a motion (the language, PREFILLED from whatever this motion
    concerns -- a contested findings_nodes standard, the completeness
    question, the adoption text) with its vote fields NULL, matching every
    real pre-meeting DRAFT sample: the motion's wording exists before the
    meeting, the vote does not. `record_vote()` fills the vote in later,
    once the meeting actually happens.
    """
    details: list[dict[str, str]] = []
    if kind not in MOTION_KINDS:
        details.append({"field": "kind", "message": f"must be one of {sorted(MOTION_KINDS)}"})
    if not text or not text.strip():
        details.append({"field": "text", "message": "required (non-empty) -- the motion language"})
    if details:
        raise ValidationError(details)

    motion_id = _new_id()
    now = _utc_now_iso()

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO motions (id, case_id, sort_order, kind, text, created_at, actor_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (motion_id, case_id, sort_order, kind, text, now, actor_user_id),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="motion.created",
            payload={"motion_id": motion_id, "case_id": case_id, "kind": kind, "text": text},
            case_id=case_id,
            entity_table="motions",
            entity_id=motion_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return _row_to_dict(conn.execute("SELECT * FROM motions WHERE id = ?;", (motion_id,)).fetchone())


def record_vote(
    conn: sqlite3.Connection,
    *,
    motion_id: str,
    moved_by: str,
    seconded_by: str,
    votes_yes: int,
    votes_no: int,
    votes_abstain: int,
    outcome: str,
    recorded_by: str,
    voted_at: str | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Fill in an already-drafted motion's vote -- moved_by/seconded_by
    (board_members.id), the tally, and the parliamentary outcome. UPDATEs
    the existing motions row (a motion is voted once; a re-vote is a
    reconsideration, out of this function's scope -- see decisions'
    "a reconsideration is a new row" comment for the pattern one level up).

    `recorded_by` (a users.id, matching motions.recorded_by/decisions.
    recorded_by's own naming) is REQUIRED and non-optional in this
    signature -- motions' own CHECK ("outcome IS NULL OR (recorded_by IS
    NOT NULL AND voted_at IS NOT NULL)") is exactly the framing rule's "only
    a human sets this" backstop, and this function is the one place that
    can ever satisfy it.
    """
    details: list[dict[str, str]] = []
    if outcome not in MOTION_OUTCOMES:
        details.append({"field": "outcome", "message": f"must be one of {sorted(MOTION_OUTCOMES)}"})
    for field_name, value in (("votes_yes", votes_yes), ("votes_no", votes_no), ("votes_abstain", votes_abstain)):
        if value is None or value < 0:
            details.append({"field": field_name, "message": "required, must be >= 0"})
    if not recorded_by:
        details.append({"field": "recorded_by", "message": "required -- a motion's vote is a recorded human act"})
    if details:
        raise ValidationError(details)

    now = _utc_now_iso()
    effective_voted_at = voted_at or now

    conn.execute("BEGIN;")
    try:
        cur = conn.execute(
            """
            UPDATE motions
            SET moved_by = ?, seconded_by = ?, votes_yes = ?, votes_no = ?, votes_abstain = ?,
                outcome = ?, voted_at = ?, recorded_by = ?
            WHERE id = ?;
            """,
            (moved_by, seconded_by, votes_yes, votes_no, votes_abstain, outcome,
             effective_voted_at, recorded_by, motion_id),
        )
        if cur.rowcount == 0:
            raise LookupError(f"no motions row with id={motion_id!r}")

        row = conn.execute("SELECT case_id FROM motions WHERE id = ?;", (motion_id,)).fetchone()
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="motion.voted",
            payload={
                "motion_id": motion_id,
                "moved_by": moved_by,
                "seconded_by": seconded_by,
                "votes_yes": votes_yes,
                "votes_no": votes_no,
                "votes_abstain": votes_abstain,
                "outcome": outcome,
                "recorded_by": recorded_by,
            },
            case_id=row["case_id"] if row is not None else None,
            entity_table="motions",
            entity_id=motion_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return _row_to_dict(conn.execute("SELECT * FROM motions WHERE id = ?;", (motion_id,)).fetchone())


def get_motions(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM motions WHERE case_id = ? ORDER BY sort_order;", (case_id,)
    ).fetchall()
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------- #
# The case outcome
# --------------------------------------------------------------------------- #


def record_outcome(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    ruleset_id: str,
    outcome: str,
    recorded_by: str,
    motion_id: str | None = None,
    decided_at: str | None = None,
    meeting_date: str | None = None,
    summary: str | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Record the Board's disposition of the case -- one of CASE_OUTCOMES.
    Always INSERTs a NEW row (decisions.id) rather than updating a prior
    one: 0001_init.sql's own comment on this table is explicit that "a
    reconsideration is a new row", so this function is never destructive.

    `recorded_by` is REQUIRED -- decisions' own CHECK ("outcome IS NULL OR
    (recorded_by IS NOT NULL AND decided_at IS NOT NULL)") is the same
    framing-rule backstop `record_vote()` enforces for motions, and this is
    the one function that can ever satisfy it. Downstream clock emission
    (Clerk filing -> §23 appeal window, via engine/deadlines.py) is
    deliberately NOT done here -- that belongs to the "produce adopted
    final" step of W7, which has the post-amendment tree and the actual
    adopted document to derive milestones from; this function's job ends at
    "the decision itself is durably recorded, with who and when."
    """
    details: list[dict[str, str]] = []
    if outcome not in CASE_OUTCOMES:
        details.append({"field": "outcome", "message": f"must be one of {sorted(CASE_OUTCOMES)}"})
    if not recorded_by:
        details.append({"field": "recorded_by", "message": "required -- a decision is a recorded human act"})
    if details:
        raise ValidationError(details)

    decision_id = _new_id()
    now = _utc_now_iso()
    effective_decided_at = decided_at or now

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO decisions
                (id, case_id, motion_id, outcome, decided_at, meeting_date, appeal_deadline,
                 ruleset_id, summary, recorded_by, created_at, actor_user_id)
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?);
            """,
            (decision_id, case_id, motion_id, outcome, effective_decided_at, meeting_date,
             ruleset_id, summary, recorded_by, now, actor_user_id),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="decision.recorded",
            payload={
                "decision_id": decision_id,
                "case_id": case_id,
                "motion_id": motion_id,
                "outcome": outcome,
                "decided_at": effective_decided_at,
                "recorded_by": recorded_by,
            },
            case_id=case_id,
            entity_table="decisions",
            entity_id=decision_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return _row_to_dict(conn.execute("SELECT * FROM decisions WHERE id = ?;", (decision_id,)).fetchone())


def get_decisions(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every decision row for `case_id`, oldest first -- ordinarily one row,
    more than one only if the case was reconsidered."""
    rows = conn.execute(
        "SELECT * FROM decisions WHERE case_id = ? ORDER BY created_at;", (case_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def get_current_decision(conn: sqlite3.Connection, case_id: str) -> dict[str, Any] | None:
    """The most recently recorded decision for `case_id`, or None if the
    case has never been decided. On a reconsidered case this is the LATEST
    disposition, not necessarily the first."""
    rows = get_decisions(conn, case_id)
    return rows[-1] if rows else None


# --------------------------------------------------------------------------- #
# W7: per-node Conclusion-of-Law motions -- the DRAFTING half of THE ONLY
# PATH TO findings_nodes.conclusion.
#
# RECONCILIATION NOTE (found mid-build, same shape as BUILD-STATE.md's W5
# section and 0013_findings_tree.sql's own header): a concurrently-running
# W7 session independently built `engine/meeting.py`, whose `apply_motion()`
# is THE ONLY caller of engine.findings._write_conclusion() -- the one raw
# UPDATE in this application that can ever set findings_nodes.conclusion
# (see that function's own "THE ONLY WRITER" section). This module does NOT
# duplicate that function; it supplies the piece engine/meeting.py's own
# docstring says it deliberately does not own -- drafting a motion's TEXT
# and PROPOSED conclusion FROM a specific findings_nodes row in the first
# place (0015_motion_conclusion.sql added `motions.findings_node_id` and
# `motions.proposed_conclusion` for exactly this). draft_node_motion() below
# composes create_motion() (this module, above) with
# engine.meeting.set_motion_findings_link() (the other session's own
# additive-UPDATE seam for those two columns) rather than reaching into
# `motions` directly a second way.
# --------------------------------------------------------------------------- #


def eligible_nodes_for_motion(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every CURRENT (superseded_by IS NULL), not-yet-concluded
    (conclusion IS NULL) finding/conclusion node in `case_id` that carries
    enough content to be worth a motion (a quoted standard, a stated fact,
    or a board question -- never a bare placeholder row) and does not
    already have ANY motion drafted against it (this makes
    draft_node_motions() below idempotent: calling it again after a partial
    meeting only drafts motions for what is still outstanding, never a
    duplicate for a node already on the agenda).

    Every one of these nodes is "contested or judgement" in the sense the
    W7 brief uses the phrase: per findings_nodes' own CHECK and
    engine/subdivision_review.py's own comment on it, EVERY finding node --
    including a NOT_APPLICABLE or PROCEDURAL_REFERENCE one -- "remains a
    Board-adoptable item until a vote closes it". This module drafts one
    motion per such node (v1 scope: the real Shattuck adopted final
    sometimes bulk-groups several not-applicable standards under a single
    motion -- e.g. "Article 3, 4, 5 and 6 ... are not applicable" -- but
    building that grouping heuristic is out of scope here; one motion per
    node is simpler, strictly more auditable, and never wrong, only more
    verbose than the Board's own real practice).
    """
    rows = conn.execute(
        """
        SELECT fn.* FROM findings_nodes fn
        WHERE fn.case_id = ?
          AND fn.superseded_by IS NULL
          AND fn.conclusion IS NULL
          AND fn.node_type IN ('finding', 'conclusion')
          AND (fn.body IS NOT NULL OR fn.board_question IS NOT NULL OR fn.quoted_standard_text IS NOT NULL)
          AND NOT EXISTS (SELECT 1 FROM motions m WHERE m.findings_node_id = fn.id)
        ORDER BY fn.sort_order;
        """,
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _node_label(node: dict[str, Any]) -> str:
    return (
        (node.get("citation_display") or "").strip()
        or (node.get("heading") or "").strip()
        or (node.get("number_label") or "").strip()
        or "this standard"
    )


def draft_text_for_node(node: dict[str, Any]) -> tuple[str, str]:
    """Returns (text, proposed_conclusion) for one findings_nodes row,
    PREFILLED to match the real Shattuck adopted final's own house
    phrasing (docs/Findings of Fact and Conclusions of Law/M003, L059 ...
    2025.12.18.pdf, pp.11-14) -- every per-standard motion is worded as the
    AFFIRMATIVE action:

        applicability_verdict == 'false' (the gate found this standard's
        subject matter absent -- NOT_APPLICABLE):
            "To conclude that {label} is not applicable to this application."
            proposed_conclusion = 'n_a'
            (real example: "To conclude that Article 3, Article 4, Article 5,
            and Article 6 of the Core Zoning Code are not applicable...")

        every other case (a stated fact, a judgement question, a
        procedural cross-reference, a mandated condition, or an unresolved
        applicability question) -- the real document's own uniform
        template, whether the standard is a., b., g., j., n., o., r., or
        u.:
            "To conclude that the application is consistent with {label}."
            proposed_conclusion = 'met'

    This is a DRAFT, never a guess at what the Board will decide: the text
    only ever reaches a live vote through record_vote() above, and a
    conclusion only ever reaches findings_nodes through
    engine.meeting.apply_motion(), and only on outcome='carried'. If the
    Board disagrees, the motion fails (or is amended before the vote) and
    the node stays unresolved for a substitute motion -- this function
    never drafts a pre-written negative ("...is NOT consistent...") because
    no real sample in docs/ ever phrases one that way; the Board's own
    convention is to vote down the affirmative, not to pre-draft its
    opposite.
    """
    label = _node_label(node)
    if node.get("applicability_verdict") == "false":
        return (f"To conclude that {label} is not applicable to this application.", "n_a")
    return (f"To conclude that the application is consistent with {label}.", "met")


def draft_node_motion(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    node_id: str,
    sort_order: int = 0,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Draft ONE motion (kind='findings', findings_node_id=node_id,
    proposed_conclusion from draft_text_for_node()) against a single
    findings_nodes row. Vote fields ship NULL, matching create_motion()'s
    own convention -- the wording exists before the meeting, the vote does
    not.

    Composes create_motion() (above, in this module) with
    engine.meeting.set_motion_findings_link() (the other W7 session's own
    additive seam for `findings_node_id`/`proposed_conclusion`) rather than
    inserting those two columns directly -- see this section's own
    reconciliation note.

    Raises engine.findings.NodeNotFound if the node does not exist, and
    ValueError if the node is not the case's own, not the current revision,
    not a finding/conclusion node, or already carries a conclusion --
    drafting a motion against a stale or already-decided node is never a
    silent no-op.
    """
    node = findings_engine.get_node(conn, node_id)
    if node is None:
        raise findings_engine.NodeNotFound(node_id)
    if node["case_id"] != case_id:
        raise ValueError(f"node {node_id!r} belongs to case {node['case_id']!r}, not {case_id!r}")
    if node["superseded_by"] is not None:
        raise ValueError(f"node {node_id!r} is not the current revision; amend or re-fetch first")
    if node["node_type"] not in ("finding", "conclusion"):
        raise ValueError(f"node {node_id!r} is a {node['node_type']!r} node; only finding/conclusion nodes take a motion")
    if node["conclusion"] is not None:
        raise ValueError(f"node {node_id!r} already carries a conclusion; nothing to move")

    text, proposed_conclusion = draft_text_for_node(node)
    motion = create_motion(conn, case_id=case_id, kind="findings", text=text, sort_order=sort_order, actor_user_id=actor_user_id)

    return meeting_engine.set_motion_findings_link(
        conn, motion_id=motion["id"], findings_node_id=node_id, proposed_conclusion=proposed_conclusion,
        actor_user_id=actor_user_id,
    )


def draft_node_motions(
    conn: sqlite3.Connection, *, case_id: str, actor_user_id: str | None, sort_start: int = 100,
) -> list[dict[str, Any]]:
    """draft_node_motion() for every row eligible_nodes_for_motion() returns,
    in sort_order, numbered starting at `sort_start` (default 100, so a
    caller that also drafts a completeness motion at sort_order=0 gets the
    real meeting's own ordering: completeness first, then one motion per
    contested/judgement node, in Code order). Idempotent: a node that
    already has a motion (from a prior call, or drafted individually via
    draft_node_motion()) is skipped, never double-drafted.
    """
    out: list[dict[str, Any]] = []
    for i, node in enumerate(eligible_nodes_for_motion(conn, case_id)):
        out.append(
            draft_node_motion(
                conn, case_id=case_id, node_id=node["id"], sort_order=sort_start + i,
                actor_user_id=actor_user_id,
            )
        )
    return out

    return findings_engine.get_node(conn, node_id)  # type: ignore[return-value]
