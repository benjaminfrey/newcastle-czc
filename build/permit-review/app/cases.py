"""Implements the W3 "cases + the audit-backed case lifecycle" task brief on
top of CONTRACT.md §3.2 (the binding gate), §3.3 (the audit chain), §3.4
(deterministic dates) and the `cases` / `case_milestones` tables added by
app/migrations/0002_case_tracking.sql and app/migrations/0003_case_lifecycle.sql.

Pure business logic + DB access -- no FastAPI, no HTTP status codes, no JSON
envelope. app/routes/cases.py is the thin HTTP translation layer over this
module, exactly the split app/reviews.py already established for the
worksheet's Required-Review lookups.

THE STATE MACHINE
------------------
    intake -> extracting -> review -> draft_issued -> meeting -> decided -> closed
                  \\___________\\__________\\_____________\\________/
                   \\__________________________________________> withdrawn

`withdrawn` is reachable from any non-terminal status (an applicant can pull
an application at any point before a decision); `closed` and `withdrawn` are
terminal. See ALLOWED_TRANSITIONS below -- it is the single source of truth;
the `cases.status` CHECK constraint (0003_case_lifecycle.sql) is a DB-level
backstop against a bug here, not the other way around. Every transition
(including case creation, which enters at 'intake') writes exactly one
`events` row in the SAME transaction as its mutation, carrying `actor` and
`why` (CONTRACT.md §3.3) -- an invalid transition raises InvalidTransition
and writes nothing.

THE BINDING GATE, WITH ONE AUDITED ESCAPE HATCH
-------------------------------------------------
CONTRACT.md §1 S8 / §3.2: a real (non-scratch) case must not cite a
non-binding ruleset. That remains the default here. The W3 brief calls for
one explicit, audited exception: pass `binding_override=True` with a
non-empty `override_reason` and the case may pin a draft ruleset anyway --
this is for a human, on the record, choosing to pre-stage or dry-run a case
against a draft ahead of adoption. It does not change what "binding" means
and it is never available silently: create_case() raises
NonBindingRulesetRefused unless is_scratch, or binding_override +
override_reason, is given, and the choice (plus the reason and the acting
user) is written into the SAME `case.created` events row every case creation
already produces -- never a second, separate event (CONTRACT.md §3.3: one
mutation, one events row). The `cases` table CHECK/trigger pair
(0003_case_lifecycle.sql) enforces the identical rule as a backstop, matching
the dual enforcement CONTRACT.md §3.2 already requires ("enforced by a table
trigger AND re-checked in app/rulesets.py" -- app/cases.py is the second
enforcement point for this table, the way app/rulesets.py is for worksheet
rendering).

KEY DATES
---------
application_received, completeness, notice mailed/published, hearing
opened/closed, meeting, decision (+ decision filed, plat recorded, appeal,
reconsideration) are recorded as ROWS in `case_milestones`
(0002_case_tracking.sql / 0003_case_lifecycle.sql), never as single mutable
columns on `cases` -- that is what lets a case hold the real Shattuck
pattern: a hearing OPENED at one Board meeting and CLOSED at a later one
(two rows, two dates), and a hearing rescheduled and RE-NOTICED without
destroying the original notice record (a new row, optionally pointed back at
the row it reschedules via `supersedes_id`, which sets the OLD row's
write-once `superseded_by` forward -- the old row is never edited or
deleted). `cases.received_at` / `meeting_date` / `draft_due` stay as
convenience mirrors of the latest 'application_received' / 'meeting' rows
(never the source of truth); `draft_due` is always RECOMPUTED from
`meeting_date` via app.dates.draft_due() (CONTRACT.md §3.4 -- computed on
read, never typed by a user).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from typing import Any

from app import dates as dates_mod
from app.audit import append_event
# Finding 3 -- record_dates() validates an 'extension_agreed'/'clock_waived'/
# 'clock_not_applicable' entry's target_clock_key against the case's OWN
# ruleset's clocks (engine.deadlines.load_clocks/clock_is_extendable). No
# import cycle: engine.deadlines itself only imports app.citation/app.config/
# app.meetings, none of which import this module.
from engine import deadlines as deadlines_mod

# --------------------------------------------------------------------------- #
# Vocabulary -- single source of truth for this module; the CHECK constraints
# in app/migrations/0002_case_tracking.sql and 0003_case_lifecycle.sql are a
# DB-level mirror of the same lists, kept in sync by hand (small, stable,
# reviewed-together-with-a-migration lists -- not worth a runtime PRAGMA
# table_info() round trip to derive).
# --------------------------------------------------------------------------- #

APPLICATION_TYPES: frozenset[str] = frozenset({
    "use", "zoning", "subdivision", "shoreland", "site_plan", "special_permit",
    "expanded_use", "other", "small_project_plan", "large_project_plan", "variance",
})

STATUSES: tuple[str, ...] = (
    "intake", "extracting", "review", "draft_issued", "meeting", "decided", "closed", "withdrawn",
)

TERMINAL_STATUSES: frozenset[str] = frozenset({"closed", "withdrawn"})

#: The single source of truth for the case lifecycle. app/routes/cases.py and
#: every test import this rather than re-deriving it.
ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "intake":       frozenset({"extracting", "withdrawn"}),
    "extracting":   frozenset({"review", "withdrawn"}),
    "review":       frozenset({"draft_issued", "withdrawn"}),
    "draft_issued": frozenset({"meeting", "withdrawn"}),
    "meeting":      frozenset({"decided", "withdrawn"}),
    "decided":      frozenset({"closed"}),
    "closed":       frozenset(),
    "withdrawn":    frozenset(),
}

#: case_milestones.kind's full CHECK vocabulary (0003_case_lifecycle.sql,
#: widened by 0005_deadline_engine_fixes.sql -- F6 promotes 'findings_issued'
#: and 'certificate_recorded' from the retired 'other'+note-substring
#: bridging convention to first-class kinds -- and by
#: 0006_appeal_recordability.sql -- N2 adds the four §23 appeal-track events
#: (appeal_hearing_opened, appeal_hearing_closed, appeal_decision,
#: reconsideration_decided) that administrative_appeal_hearing/_decision/
#: reconsideration_decision (rulesets/adopted/clocks.json) named from F3
#: onward but that, before 0006, no case_milestones.kind could ever record --
#: two of those three clocks carry the §8.d.1 auto-approval consequence, so a
#: Board of Appeals that held its appeal hearing and decided it on time still
#: showed a permanent, un-clearable alarm), kept verbatim here so a bad kind
#: is rejected with a clean app-level error instead of a raw
#: sqlite3.IntegrityError. ruleset_build.verify_structure.
#: check_clock_event_recordability asserts, as a standing build gate, that
#: every clocks.json event resolves to a kind in this set -- see that
#: function's docstring. HARD-FINAL round, Finding 6 adds 'reconsideration_
#: voted' -- the §23.e.2/.e.3 VOTE TO RECONSIDER, now reconsideration_
#: decision's predicate_event in place of the mere §23.e.1 request (see
#: engine/deadlines.py's CaseFacts.reconsideration_voted_at and
#: app/migrations/0011_reconsideration_vote.sql). Finding 3 adds the three
#: clock-override kinds -- 'extension_agreed' (Article 7 §6.e.1/§6.e.2: a
#: written agreement extending a hearing-commencement or decision time
#: limit -- see engine.deadlines.clock_is_extendable() for which clocks
#: qualify, and DECISIONS-NEEDED D-0022/D-0024), 'clock_waived' and
#: 'clock_not_applicable' (the write path engine.deadlines.CaseFacts.
#: waived_clocks/na_clocks never had before this fix) -- all three shaped
#: by app/migrations/0010_clock_extensions.sql's target_clock_key/
#: extension_days/written_agreement_ref columns and validated below.
CASE_MILESTONE_KINDS: frozenset[str] = frozenset({
    "application_dated", "application_received", "pre_submittal_meeting", "circulated",
    "notice_mailed", "notice_published", "completeness_determined", "hearing_opened",
    "hearing_closed", "meeting", "forwarded_to_planning_board", "decision_issued",
    "decision_filed", "findings_issued", "certificate_recorded",
    "plat_recorded", "appeal_filed", "reconsideration_requested",
    "appeal_hearing_opened", "appeal_hearing_closed", "appeal_decision",
    "reconsideration_decided", "reconsideration_voted",
    "extension_agreed", "clock_waived", "clock_not_applicable", "other",
})

#: The W3 brief's own words ("application_received", "completeness",
#: "hearing opened/closed", "meeting", "decision") mapped onto
#: case_milestones' stored kind. Any name already in CASE_MILESTONE_KINDS
#: (e.g. "hearing_opened", "notice_mailed") passes through unchanged --
#: this dict only covers the handful of aliases that differ.
DATE_KIND_ALIASES: dict[str, str] = {
    "completeness": "completeness_determined",
    "decision": "decision_issued",
    "findings": "findings_issued",
    "certificate": "certificate_recorded",
    "extension": "extension_agreed",
    "waived": "clock_waived",
    "waive": "clock_waived",
    "not_applicable": "clock_not_applicable",
    "na": "clock_not_applicable",
}

#: Finding 3 -- kinds whose row carries a target_clock_key (and, for
#: 'extension_agreed' only, extension_days/written_agreement_ref) instead of
#: describing an ordinary dated procedural event. record_dates() branches on
#: membership in this set rather than repeating the three literal strings at
#: each call site below.
CLOCK_OVERRIDE_KINDS: frozenset[str] = frozenset({"extension_agreed", "clock_waived", "clock_not_applicable"})

#: N3 -- the only two legal `case_milestones.supersede_reason` values
#: (0007_supersede_reason.sql's CHECK, kept verbatim here for the same
#: clean-app-level-error-instead-of-raw-IntegrityError reason as
#: CASE_MILESTONE_KINDS above). See record_dates()'s docstring for what
#: each one means to engine/deadlines.py's satisfying-occurrence logic.
SUPERSEDE_REASONS: frozenset[str] = frozenset({"reschedule", "correction"})

DEFAULT_RULESET_KEY = "adopted"  # CONTRACT.md §1 S8 -- the binding ruleset, pinned by default.


def _occurred_on_error(raw: str) -> str | None:
    """Validates a `case_milestones.occurred_on` value AT THE BOUNDARY
    (CONTRACT.md §1 S1 -- validate-all-then-write), fixing the F5 defect: an
    unvalidated value like "December 18, 2025" used to write straight into
    the append-only `case_milestones` table, permanently, and 500 every
    later read of the case (engine.deadlines._parse_date only knows
    `datetime.fromisoformat(s[:10])`). Mirrors that exact parsing rule here
    so a value this function accepts is guaranteed to be one every read path
    can also parse: the first 10 characters must be a real ISO calendar
    date (`YYYY-MM-DD`); anything after that (e.g. a `THH:MM:SS` suffix) is
    tolerated but not itself validated, matching the docstring's own
    "ISO date/datetime string" claim.

    Returns None when `raw` is valid, else a human-readable message.
    """
    try:
        date.fromisoformat(raw[:10])
    except ValueError:
        return (
            f"{raw!r} is not a valid ISO date -- the first 10 characters must be a "
            f"real calendar date in YYYY-MM-DD form (a trailing time-of-day is fine)"
        )
    return None


# --------------------------------------------------------------------------- #
# Exceptions -- one type per failure mode app/routes/cases.py needs to tell
# apart, so it can pick the right HTTP status without string-matching.
# --------------------------------------------------------------------------- #


class CaseError(Exception):
    """Base for every error this module raises."""


class ValidationError(CaseError, ValueError):
    """The request itself is malformed. `.details` is a list of
    {"field": ..., "message": ...} dicts, matching CONTRACT.md §6's envelope."""

    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        super().__init__(f"validation failed: {details}")


class CaseNotFound(CaseError, LookupError):
    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"no case with id {case_id!r}")


class UnknownRuleset(CaseError, LookupError):
    def __init__(self, ruleset_key: str):
        self.ruleset_key = ruleset_key
        super().__init__(f"no ruleset registered with ruleset_key={ruleset_key!r}")


class NonBindingRulesetRefused(CaseError, PermissionError):
    """CONTRACT.md §1 S8 / §3.2: a real (non-scratch) case tried to cite a
    non-binding ruleset without is_scratch or an explicit binding_override."""


class InvalidTransition(CaseError, ValueError):
    def __init__(self, case_id: str, from_status: str, to_status: str, allowed: frozenset[str]):
        self.case_id = case_id
        self.from_status = from_status
        self.to_status = to_status
        self.allowed = allowed
        super().__init__(
            f"cannot transition case {case_id} from {from_status!r} to {to_status!r}; "
            f"allowed next status(es): {sorted(allowed) if allowed else '(none -- terminal status)'}"
        )


# --------------------------------------------------------------------------- #
# Small internal helpers
# --------------------------------------------------------------------------- #


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    """ISO-8601 UTC, 'Z' suffix, millisecond precision -- CONTRACT.md §3.3/§3.4."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _default_label(
    map_lot: str | None, situs_address: str | None, applicant_name: str | None, case_number: str | None,
) -> str:
    head = map_lot or case_number or "Case"
    paren_bits = [b for b in (situs_address, applicant_name) if b]
    return f"{head} ({', '.join(paren_bits)})" if paren_bits else head


def _case_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["is_scratch"] = bool(d["is_scratch"])
    d["binding_override"] = bool(d["binding_override"])
    return d


def _resolve_ruleset(conn: sqlite3.Connection, ruleset_key: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, ruleset_key, binding FROM rulesets WHERE ruleset_key = ?;", (ruleset_key,)
    ).fetchone()
    if row is None:
        raise UnknownRuleset(ruleset_key)
    return row


def _rollback_and_raise(conn: sqlite3.Connection, exc: BaseException) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK;")
    raise exc


# --------------------------------------------------------------------------- #
# create_case
# --------------------------------------------------------------------------- #


def create_case(
    conn: sqlite3.Connection,
    *,
    application_type: str | None,
    map_lot: str | None = None,
    situs_address: str | None = None,
    applicant_name: str | None = None,
    case_number: str | None = None,
    label: str | None = None,
    district_key: str | None = None,
    ruleset_key: str | None = None,
    is_scratch: bool = False,
    binding_override: bool = False,
    override_reason: str | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Create a case, pinned to `ruleset_key` (default DEFAULT_RULESET_KEY,
    the adopted/binding Code), entering the state machine at 'intake'.

    Raises ValidationError (bad application_type / missing override_reason),
    UnknownRuleset (ruleset_key not registered in the DB -- see
    ruleset_build/build_ruleset.py's step 5), or NonBindingRulesetRefused
    (CONTRACT.md §1 S8 -- a real case against a draft ruleset with neither
    is_scratch nor an explicit, reasoned binding_override). Writes exactly
    one `events` row (kind='case.created') in the same transaction as the
    INSERT; a raised exception writes nothing.
    """
    details: list[dict[str, str]] = []
    if application_type not in APPLICATION_TYPES:
        details.append({
            "field": "application_type",
            "message": f"required; must be one of {sorted(APPLICATION_TYPES)}",
        })
    if binding_override and not (override_reason and override_reason.strip()):
        details.append({
            "field": "override_reason",
            "message": "required (non-empty) when binding_override is true",
        })
    if details:
        raise ValidationError(details)

    ruleset_key_effective = ruleset_key or DEFAULT_RULESET_KEY
    ruleset_row = _resolve_ruleset(conn, ruleset_key_effective)

    effective_reason = override_reason.strip() if binding_override else None

    if not is_scratch and not ruleset_row["binding"] and not binding_override:
        raise NonBindingRulesetRefused(
            f"ruleset {ruleset_key_effective!r} is not binding (CONTRACT.md §1 S8); a real case "
            f"must cite the adopted Code. Pass is_scratch=true to dry-run it, or "
            f"binding_override=true with a non-empty override_reason to record an explicit, "
            f"audited exception."
        )

    case_id = _new_id()
    now = _utc_now_iso()
    computed_label = label.strip() if label and label.strip() else _default_label(
        map_lot, situs_address, applicant_name, case_number
    )

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO cases (
                id, case_number, label, map_lot, situs_address, applicant_name,
                application_type, district_key, ruleset_id, is_scratch,
                binding_override, override_reason, status,
                received_at, meeting_date, draft_due, created_at, updated_at, actor_user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'intake', NULL, NULL, NULL, ?, ?, ?);
            """,
            (
                case_id, case_number, computed_label, map_lot, situs_address, applicant_name,
                application_type, district_key, ruleset_row["id"], int(is_scratch),
                int(binding_override), effective_reason,
                now, now, actor_user_id,
            ),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="case.created",
            payload={
                "case_id": case_id,
                "label": computed_label,
                "application_type": application_type,
                "ruleset_key": ruleset_row["ruleset_key"],
                "ruleset_id": ruleset_row["id"],
                "is_scratch": bool(is_scratch),
                "binding_override": bool(binding_override),
                "override_reason": effective_reason,
                "status": "intake",
            },
            case_id=case_id,
            entity_table="cases",
            entity_id=case_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: roll back, then re-raise unchanged
        _rollback_and_raise(conn, exc)

    return get_case(conn, case_id)  # type: ignore[return-value]  -- just inserted, always found


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


def get_case(conn: sqlite3.Connection, case_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
    return _case_row_to_dict(row) if row is not None else None


def list_cases(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    ruleset_key: str | None = None,
    is_scratch: bool | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT c.* FROM cases c"
    clauses: list[str] = []
    params: list[Any] = []
    if ruleset_key is not None:
        sql += " JOIN rulesets r ON r.id = c.ruleset_id"
        clauses.append("r.ruleset_key = ?")
        params.append(ruleset_key)
    if status is not None:
        clauses.append("c.status = ?")
        params.append(status)
    if is_scratch is not None:
        clauses.append("c.is_scratch = ?")
        params.append(int(is_scratch))
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY c.created_at DESC, c.id ASC;"
    rows = conn.execute(sql, params).fetchall()
    return [_case_row_to_dict(r) for r in rows]


def case_dates_for(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every case_milestones row for this case, oldest first -- the full,
    never-destroyed history (superseded rows included, so a re-notice or a
    rescheduled hearing is visible, not smoothed away)."""
    rows = conn.execute(
        "SELECT * FROM case_milestones WHERE case_id = ? ORDER BY occurred_on ASC, created_at ASC;",
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def case_history_for(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every `events` row about this case (CONTRACT.md §3.3's case_id
    column), oldest first, with payload_json decoded for display."""
    rows = conn.execute(
        """
        SELECT seq, id, at, actor_user_id, kind, payload_json
        FROM events WHERE case_id = ? ORDER BY seq ASC;
        """,
        (case_id,),
    ).fetchall()
    return [
        {
            "seq": r["seq"], "id": r["id"], "at": r["at"],
            "actor_user_id": r["actor_user_id"], "kind": r["kind"],
            "payload": json.loads(r["payload_json"]),
        }
        for r in rows
    ]


# --------------------------------------------------------------------------- #
# transition_status
# --------------------------------------------------------------------------- #


def transition_status(
    conn: sqlite3.Connection,
    case_id: str,
    *,
    to_status: str | None,
    why: str | None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Move a case to `to_status` per ALLOWED_TRANSITIONS. Raises
    ValidationError (bad/missing to_status or why), CaseNotFound, or
    InvalidTransition (the current status cannot reach to_status). Writes
    exactly one `events` row (kind='case.status_changed', carrying `why`) in
    the same transaction as the UPDATE; a raised exception writes nothing.
    """
    details: list[dict[str, str]] = []
    if to_status not in STATUSES:
        details.append({"field": "to_status", "message": f"required; must be one of {list(STATUSES)}"})
    if not why or not why.strip():
        details.append({"field": "why", "message": "required (non-empty) -- every transition records why"})
    if details:
        raise ValidationError(details)

    row = conn.execute("SELECT status FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if row is None:
        raise CaseNotFound(case_id)

    from_status = row["status"]
    allowed = ALLOWED_TRANSITIONS.get(from_status, frozenset())
    if to_status not in allowed:
        raise InvalidTransition(case_id, from_status, to_status, allowed)

    now = _utc_now_iso()
    conn.execute("BEGIN;")
    try:
        conn.execute("UPDATE cases SET status = ?, updated_at = ? WHERE id = ?;", (to_status, now, case_id))
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="case.status_changed",
            payload={"case_id": case_id, "from_status": from_status, "to_status": to_status, "why": why.strip()},
            case_id=case_id,
            entity_table="cases",
            entity_id=case_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return get_case(conn, case_id)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# record_dates
# --------------------------------------------------------------------------- #


def _mirror_column_updates(
    prepared: list[tuple[str, str, str, str | None, str | None, str | None, str | None, int | None, str | None]],
) -> dict[str, str]:
    """Recompute the `cases` convenience-mirror columns from this batch's
    'application_received' / 'meeting' entries (last one in the batch wins,
    matching "the most recent row for a kind is the current value").
    draft_due is always DERIVED from meeting_date via app.dates.draft_due()
    (CONTRACT.md §3.4) -- never accepted directly from a caller.
    """
    updates: dict[str, str] = {}
    for _kind_in, stored_kind, occurred_on, _note, _supersedes, _reason, _target, _ext_days, _ref in prepared:
        if stored_kind == "application_received":
            updates["received_at"] = occurred_on
        elif stored_kind == "meeting":
            updates["meeting_date"] = occurred_on

    if "meeting_date" in updates:
        try:
            y, m, d = (int(x) for x in updates["meeting_date"][:10].split("-"))
            updates["draft_due"] = dates_mod.draft_due(date(y, m, d)).isoformat()
        except (ValueError, TypeError):
            # Not a plain ISO date (e.g. a bare datetime string in an
            # unexpected shape) -- leave draft_due untouched rather than
            # guess at it (CONTRACT.md §1 S7).
            pass

    return updates


def record_dates(
    conn: sqlite3.Connection,
    case_id: str,
    *,
    entries: list[dict[str, Any]] | None,
    why: str | None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Append one or more key-date facts to `case_milestones`. Each entry is
    `{"kind": ..., "occurred_on": "YYYY-MM-DD"[, "note": ..., "supersedes_id": ...,
    "supersede_reason": ...]}`.
    `kind` accepts either the W3 brief's own words (DATE_KIND_ALIASES --
    "completeness", "decision") or any case_milestones.kind value directly
    ("hearing_opened", "hearing_closed", "meeting", "application_received",
    "notice_mailed", ...).

    Never UPDATEs or DELETEs an existing row -- a rescheduled/re-noticed
    hearing is a NEW row; pass `supersedes_id` (the id of the row being
    rescheduled/corrected) to point that EARLIER row's write-once
    `superseded_by` forward at this new one, so the original stays in the
    table, visibly superseded, never destroyed.

    N3 FIX -- whenever `supersedes_id` is given, `supersede_reason` is now
    REQUIRED and must be exactly one of:
      - "reschedule"  -- the superseded row is a GENUINE occurrence that
        really happened and really did satisfy whatever duty was live at
        the time (a hearing moved, so a fresh notice went out for the new
        date; the original notice still satisfied the original notice
        duty). engine/deadlines.py's `_first_satisfying_occurrence()` keeps
        crediting it as a candidate "first genuine occurrence".
      - "correction"  -- the superseded row was factually WRONG (a typo, a
        misread date) and never really happened as recorded; it must not be
        allowed to satisfy anything. Only the correcting (superseding) row
        counts.
    This is a deliberate, explicit choice at write time -- CONTRACT.md §1 S7
    ("no silent guessing"): the engine cannot tell the two apart from the
    dates alone, so it is never inferred, only recorded. A `supersedes_id`
    with no `supersede_reason` (or an unrecognized one) is a ValidationError,
    not a guess. See DECISIONS-NEEDED.md D-0016 for the conservative default
    this module's read side (engine/deadlines.py) applies to legacy rows
    that predate this requirement (NULL in the database).

    FINDING 3 -- three more kinds, each carrying a `target_clock_key`
    (the rulesets/<ruleset_key>/clocks.json clock_key this entry names,
    engine.deadlines.Clock.clock_key) instead of describing an ordinary
    procedural event:
      - "extension_agreed" (alias "extension") -- Article 7 §6.e.1/§6.e.2: a
        written agreement extending a hearing-commencement or decision time
        limit. Also requires `extension_days` (a positive integer, in the
        target clock's own basis) and `written_agreement_ref` (§6.e.2's
        "recorded in writing" -- a pointer to the writing itself: a letter
        date/description, a document id, whatever the case file holds).
        `target_clock_key` must name a clock engine.deadlines.
        clock_is_extendable() accepts for THIS case's own ruleset (a
        municipal_duty/conditional_duty clock whose satisfying_event is a
        hearing opening or a decision -- see DECISIONS-NEEDED D-0024);
        anything else is rejected, not silently accepted as a no-op.
        Multiple entries against the same target_clock_key ACCUMULATE (see
        engine.deadlines.CaseFacts.clock_extension_days) -- recording a
        second extension does not need to repeat or supersede the first.
      - "clock_waived" (alias "waived"/"waive") / "clock_not_applicable"
        (alias "not_applicable"/"na") -- the write path
        engine.deadlines.CaseFacts.waived_clocks / na_clocks never had
        before this fix (populated only in tests). Also requires a
        non-empty `note` (why this clock is waived/not applicable) and
        forbids `extension_days`/`written_agreement_ref`. `target_clock_key`
        must name ANY clock applicable to this case's ruleset (not narrowed
        to the §6.e.1 extendable subset -- a waiver/n/a determination is not
        itself a §6.e.1 extension).
    Every other kind forbids all three fields -- a caller cannot attach a
    target_clock_key to an ordinary dated event.

    Raises ValidationError (no entries / missing why / bad kind, occurred_on,
    supersede_reason, or clock-override fields) or CaseNotFound. Writes
    exactly one `events` row (kind='case.dates_recorded', listing every
    entry) in the same transaction as the INSERTs; a raised exception writes
    nothing.
    """
    case_row = conn.execute("SELECT ruleset_id FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if case_row is None:
        raise CaseNotFound(case_id)

    details: list[dict[str, str]] = []
    if not entries:
        details.append({"field": "dates", "message": "required: a non-empty list of date entries"})
    if not why or not why.strip():
        details.append({"field": "why", "message": "required (non-empty)"})
    if details:
        raise ValidationError(details)

    # FINDING 3 -- loaded lazily (only if the batch actually contains a
    # clock-override entry) and cached for the rest of this call, so an
    # ordinary date-recording batch on a case whose ruleset has no
    # clocks.json yet (e.g. a scratch case pinned to a draft ruleset before
    # ruleset_build.build_clocks has run for it) never fails just because
    # this validation exists.
    _clocks_cache: list[Any] | None = None

    def _clocks_for_case() -> list[Any]:
        nonlocal _clocks_cache
        if _clocks_cache is None:
            ruleset_row = conn.execute(
                "SELECT ruleset_key FROM rulesets WHERE id = ?;", (case_row["ruleset_id"],)
            ).fetchone()
            ruleset_key = ruleset_row["ruleset_key"] if ruleset_row is not None else DEFAULT_RULESET_KEY
            try:
                _clocks_cache = list(deadlines_mod.load_clocks(ruleset_key))
            except deadlines_mod.ClocksNotFound:
                # Honest empty list, not a crash -- see the CONTRACT.md §1 S7
                # graceful-degradation note above. Every target_clock_key
                # validation below simply fails closed (nothing is "known" or
                # "extendable"), which is the conservative outcome: an
                # operator cannot record a clock-override entry this app has
                # no clock definitions to check it against.
                _clocks_cache = []
        return _clocks_cache

    prepared: list[
        tuple[str, str, str, str | None, str | None, str | None, str | None, int | None, str | None]
    ] = []
    for i, entry in enumerate(entries):  # type: ignore[arg-type] -- entries checked non-empty above
        if not isinstance(entry, dict):
            details.append({"field": f"dates[{i}]", "message": "must be an object"})
            continue
        kind_in = entry.get("kind")
        stored_kind = DATE_KIND_ALIASES.get(kind_in, kind_in) if isinstance(kind_in, str) else None
        if stored_kind not in CASE_MILESTONE_KINDS:
            details.append({
                "field": f"dates[{i}].kind",
                "message": f"unknown kind {kind_in!r}; must be one of {sorted(CASE_MILESTONE_KINDS)} "
                           f"or an alias in {sorted(DATE_KIND_ALIASES)}",
            })
            continue
        occurred_on = entry.get("occurred_on")
        if not isinstance(occurred_on, str) or not occurred_on.strip():
            details.append({"field": f"dates[{i}].occurred_on", "message": "required ISO date/datetime string"})
            continue
        occurred_on = occurred_on.strip()
        date_error = _occurred_on_error(occurred_on)
        if date_error is not None:
            details.append({"field": f"dates[{i}].occurred_on", "message": date_error})
            continue
        note = entry.get("note")
        if note is not None and not isinstance(note, str):
            details.append({"field": f"dates[{i}].note", "message": "must be a string if given"})
            continue
        supersedes_id = entry.get("supersedes_id")
        if supersedes_id is not None and not isinstance(supersedes_id, str):
            details.append({"field": f"dates[{i}].supersedes_id", "message": "must be a string id if given"})
            continue
        # N3 -- supersede_reason is REQUIRED whenever supersedes_id is given
        # (CONTRACT.md §1 S7: never infer "reschedule" vs "correction" from
        # the dates alone -- see record_dates()'s docstring). Not accepted
        # at all when supersedes_id is absent, so a caller can't attach a
        # reason to nothing.
        supersede_reason = entry.get("supersede_reason")
        if supersedes_id:
            if supersede_reason not in SUPERSEDE_REASONS:
                details.append({
                    "field": f"dates[{i}].supersede_reason",
                    "message": f"required when supersedes_id is given; must be one of "
                               f"{sorted(SUPERSEDE_REASONS)} -- got {supersede_reason!r}. "
                               f"'reschedule' means the superseded row genuinely happened and "
                               f"satisfied the duty live at the time (e.g. a re-notice after a "
                               f"hearing moved); 'correction' means the superseded row was "
                               f"factually wrong (e.g. a typo) and never counts as an occurrence.",
                })
                continue
        elif supersede_reason is not None:
            details.append({
                "field": f"dates[{i}].supersede_reason",
                "message": "only meaningful together with supersedes_id",
            })
            continue

        # FINDING 3 -- target_clock_key / extension_days / written_agreement_ref.
        target_clock_key = entry.get("target_clock_key")
        extension_days = entry.get("extension_days")
        written_agreement_ref = entry.get("written_agreement_ref")
        if stored_kind == "extension_agreed":
            extendable_keys = {
                c.clock_key for c in _clocks_for_case() if deadlines_mod.clock_is_extendable(c)
            }
            if not isinstance(target_clock_key, str) or not target_clock_key.strip():
                details.append({
                    "field": f"dates[{i}].target_clock_key",
                    "message": "required for kind='extension_agreed' -- which clock is this "
                               "written agreement extending?",
                })
                continue
            target_clock_key = target_clock_key.strip()
            if target_clock_key not in extendable_keys:
                allowed_desc = (
                    str(sorted(extendable_keys)) if extendable_keys
                    else "(no clocks available for this case's ruleset)"
                )
                details.append({
                    "field": f"dates[{i}].target_clock_key",
                    "message": f"{target_clock_key!r} is not a clock Article 7 §6.e.1 lets the "
                               f"applicant and Permitting Authority extend by written agreement "
                               f"(a public-hearing-commencement or decision time limit) -- must be "
                               f"one of {allowed_desc}",
                })
                continue
            if isinstance(extension_days, bool) or not isinstance(extension_days, int) or extension_days <= 0:
                details.append({
                    "field": f"dates[{i}].extension_days",
                    "message": "required for kind='extension_agreed'; must be a positive integer "
                               "(the number of days, in the clock's own basis, this agreement adds)",
                })
                continue
            if not isinstance(written_agreement_ref, str) or not written_agreement_ref.strip():
                details.append({
                    "field": f"dates[{i}].written_agreement_ref",
                    "message": "required for kind='extension_agreed' (Article 7 §6.e.2: the "
                               "extension must be recorded in writing) -- identify the writing "
                               "(e.g. a letter date/description or a document id)",
                })
                continue
            written_agreement_ref = written_agreement_ref.strip()
        elif stored_kind in CLOCK_OVERRIDE_KINDS:  # 'clock_waived' / 'clock_not_applicable'
            known_keys = {c.clock_key for c in _clocks_for_case()}
            if not isinstance(target_clock_key, str) or not target_clock_key.strip():
                details.append({
                    "field": f"dates[{i}].target_clock_key",
                    "message": f"required for kind={stored_kind!r} -- which clock is this?",
                })
                continue
            target_clock_key = target_clock_key.strip()
            if known_keys and target_clock_key not in known_keys:
                details.append({
                    "field": f"dates[{i}].target_clock_key",
                    "message": f"{target_clock_key!r} does not name a clock in this case's ruleset "
                               f"-- must be one of {sorted(known_keys)}",
                })
                continue
            if not note or not note.strip():
                details.append({
                    "field": f"dates[{i}].note",
                    "message": f"required for kind={stored_kind!r} -- record why this clock is "
                               f"{'waived' if stored_kind == 'clock_waived' else 'not applicable'}",
                })
                continue
            if extension_days is not None or written_agreement_ref is not None:
                details.append({
                    "field": f"dates[{i}]",
                    "message": f"extension_days/written_agreement_ref are only meaningful for "
                               f"kind='extension_agreed', not {stored_kind!r}",
                })
                continue
        else:
            if target_clock_key is not None or extension_days is not None or written_agreement_ref is not None:
                details.append({
                    "field": f"dates[{i}]",
                    "message": "target_clock_key/extension_days/written_agreement_ref are only "
                               "meaningful for kind in "
                               f"{sorted(CLOCK_OVERRIDE_KINDS)}, not {stored_kind!r}",
                })
                continue
            target_clock_key = None

        prepared.append((
            kind_in, stored_kind, occurred_on.strip(), note, supersedes_id, supersede_reason,
            target_clock_key, extension_days, written_agreement_ref,
        ))
    if details:
        raise ValidationError(details)

    now = _utc_now_iso()
    inserted: list[dict[str, Any]] = []
    conn.execute("BEGIN;")
    try:
        for (
            kind_in, stored_kind, occurred_on, note, supersedes_id, supersede_reason,
            target_clock_key, extension_days, written_agreement_ref,
        ) in prepared:
            row_id = _new_id()
            conn.execute(
                """
                INSERT INTO case_milestones
                    (id, case_id, kind, occurred_on, note, superseded_by, created_at, actor_user_id,
                     target_clock_key, extension_days, written_agreement_ref)
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?);
                """,
                (row_id, case_id, stored_kind, occurred_on, note, now, actor_user_id,
                 target_clock_key, extension_days, written_agreement_ref),
            )
            if supersedes_id:
                cur = conn.execute(
                    """
                    UPDATE case_milestones SET superseded_by = ?, supersede_reason = ?
                    WHERE id = ? AND case_id = ? AND superseded_by IS NULL;
                    """,
                    (row_id, supersede_reason, supersedes_id, case_id),
                )
                if cur.rowcount == 0:
                    raise ValidationError([{
                        "field": "dates[].supersedes_id",
                        "message": f"{supersedes_id!r} does not name a live case_milestones row "
                                   f"on case {case_id} (already superseded, wrong case, or unknown id)",
                    }])
            inserted.append({
                "id": row_id, "kind_requested": kind_in, "kind": stored_kind,
                "occurred_on": occurred_on, "note": note, "supersedes_id": supersedes_id,
                "supersede_reason": supersede_reason,
                "target_clock_key": target_clock_key, "extension_days": extension_days,
                "written_agreement_ref": written_agreement_ref,
            })

        mirror_updates = _mirror_column_updates(prepared)
        if mirror_updates:
            set_sql = ", ".join(f"{col} = ?" for col in mirror_updates)
            conn.execute(
                f"UPDATE cases SET {set_sql}, updated_at = ? WHERE id = ?;",
                (*mirror_updates.values(), now, case_id),
            )

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="case.dates_recorded",
            payload={"case_id": case_id, "why": why.strip(), "entries": inserted, "mirrored": mirror_updates},
            case_id=case_id,
            entity_table="case_milestones",
            entity_id=case_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return {"case": get_case(conn, case_id), "recorded": inserted}
