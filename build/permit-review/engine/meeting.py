"""engine/meeting.py -- THE bridge from a carried motion's recorded vote to
a Conclusion of Law.

Referenced by name in engine/findings.py's own docstring/comments
("engine/meeting.py:apply_motion() -- the function that first proves a
motion CARRIED ... before ever reaching this code") since before this file
existed. This module is that promised piece -- the ONLY caller of
engine.findings._write_conclusion(), the ONE raw UPDATE in this whole
application that can ever set findings_nodes.conclusion (see that
function's own section docstring in engine/findings.py for the full
"THE ONLY WRITER" contract this module fulfills).

DELIBERATELY SEPARATE FROM `app/meeting.py` -- the meeting MODEL (board
attendance, conflict-of-interest disclosures, motion drafting, vote
recording, the case's own decisions row) built by a concurrently-running W7
session in this same directory. This is this repo's own established
precedent for two sessions landing adjacent pieces of the same phase
without one clobbering the other: BUILD-STATE.md's W5 section documents it
happening once already ("four concurrent W5 builds -> one coherent state"),
and 0013_findings_tree.sql's header documents a second instance (a
migration-number collision between two parallel W4 sessions). The right
response, per BUILD-STATE.md's own resolution both times, is to adapt to
the other build's architecture rather than fight it or silently overwrite
it -- so this module reads `app/meeting.py`'s already-written
create_motion()/record_vote() column lists as GIVEN, and adds exactly the
one seam neither of those functions writes to: the four columns
0015_motion_conclusion.sql added to `motions`
(findings_node_id/proposed_conclusion/applied_node_id/applied_at) that
neither app/meeting.py's create_motion() INSERT nor its record_vote()
UPDATE statement lists (verified by reading both before writing this
module) -- and the matching `disposition`/`discussion` columns
0016_motion_disposition_discussion.sql added, same gap.

KIND VOCABULARY NOTE. app/meeting.py's own MOTION_KINDS comment describes
'other' as "every per-standard or per-contested-node motion" -- but
0015_motion_conclusion.sql's own DB CHECK (`findings_node_id IS NULL OR
kind = 'findings'`) is the enforced rule, and it says the opposite: ANY
motion carrying a findings_node_id must be kind='findings'. This module
follows the enforced CHECK, not the comment (a CHECK constraint cannot be
talked out of rejecting a row; a code comment can be stale) -- per-standard
motions are kind='findings' WITH findings_node_id set; the single verbatim
"accept and adopt ... as amended" motion is ALSO kind='findings', WITHOUT
one (findings_node_id NULL). The two are told apart mechanically by
`findings_node_id IS NULL`, never by string-matching motion text.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.audit import append_event
from engine.findings import (  # noqa: F401 -- NodeNotEligibleForConclusion re-exported for callers
    CONCLUSIONS,
    NodeNotEligibleForConclusion,
    ValidationError,
    _write_conclusion,
)

#: motions.disposition (0016_motion_disposition_discussion.sql). Only ever
#: meaningful on a kind='decision' motion -- see set_motion_findings_link().
DISPOSITIONS: frozenset[str] = frozenset(
    {"approve", "approve_with_conditions", "deny", "table", "withdraw"}
)

#: The mapping this module's caller (app/routes/meeting.py) uses to turn a
#: CARRIED decision motion's disposition into decisions.outcome
#: (app.meeting.CASE_OUTCOMES) -- kept here, next to DISPOSITIONS, so the
#: two vocabularies' correspondence lives in one place. 'table' -> the
#: decisions.outcome. See 0015_meeting_attendance.sql's own header for why
#: it's 'continued', not a bare 'tabled'.
DISPOSITION_TO_CASE_OUTCOME: dict[str, str] = {
    "approve": "approved",
    "approve_with_conditions": "approved_with_conditions",
    "deny": "denied",
    "table": "continued",
    "withdraw": "withdrawn",
}


class MotionNotFound(LookupError):
    def __init__(self, motion_id: str):
        self.motion_id = motion_id
        super().__init__(f"motions row {motion_id!r} not found")


class MotionAlreadyApplied(ValueError):
    def __init__(self, motion_id: str, applied_node_id: str):
        self.motion_id = motion_id
        self.applied_node_id = applied_node_id
        super().__init__(
            f"motion {motion_id!r} has already been applied to node {applied_node_id!r} -- "
            "a motion can conclude a node at most once (draft a fresh motion against the "
            "current revision for a reconsideration)"
        )


class MotionNotApplicable(ValueError):
    """Raised when apply_motion() is asked to apply a motion that cannot
    legally conclude anything as it stands -- did not carry, proposes no
    conclusion, or was never linked to a node. Distinct from
    MotionAlreadyApplied (that one CAN be applied, already was) and from
    NodeNotEligibleForConclusion (the motion is fine, the NODE is not --
    e.g. it was superseded by an amendment after this motion was drafted)."""


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _get_motion(conn: sqlite3.Connection, motion_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM motions WHERE id = ?;", (motion_id,)).fetchone()
    if row is None:
        raise MotionNotFound(motion_id)
    return row


# --------------------------------------------------------------------------- #
# set_motion_findings_link() -- the small additive UPDATE app/meeting.py's
# create_motion() does not perform. Called right after create_motion() by
# app/routes/meeting.py whenever a motion is about a specific findings_nodes
# standard (kind='findings', findings_node_id + proposed_conclusion) or is
# the decision motion (kind='decision', disposition) -- never both on the
# same motion (0015/0016's own CHECKs already forbid the cross-combination;
# this function re-checks in Python so a caller gets ValidationError's
# clean per-field shape instead of a bare sqlite3.IntegrityError).
# --------------------------------------------------------------------------- #


def set_motion_findings_link(
    conn: sqlite3.Connection,
    *,
    motion_id: str,
    findings_node_id: str | None = None,
    proposed_conclusion: str | None = None,
    disposition: str | None = None,
    discussion: str | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    row = _get_motion(conn, motion_id)

    details: list[dict[str, str]] = []
    if proposed_conclusion is not None and proposed_conclusion not in CONCLUSIONS:
        details.append({"field": "proposed_conclusion", "message": f"must be one of {sorted(CONCLUSIONS)}"})
    if proposed_conclusion is not None and findings_node_id is None and row["findings_node_id"] is None:
        details.append({"field": "proposed_conclusion", "message": "requires findings_node_id"})
    if findings_node_id is not None and row["kind"] != "findings":
        details.append({
            "field": "findings_node_id",
            "message": "a motion may only be linked to a findings_nodes row when kind='findings' "
                       "(0015_motion_conclusion.sql CHECK)",
        })
    if disposition is not None:
        if disposition not in DISPOSITIONS:
            details.append({"field": "disposition", "message": f"must be one of {sorted(DISPOSITIONS)}"})
        if row["kind"] != "decision":
            details.append({
                "field": "disposition",
                "message": "a disposition is only meaningful on a kind='decision' motion",
            })
    if details:
        raise ValidationError(details)

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            UPDATE motions
            SET findings_node_id   = COALESCE(?, findings_node_id),
                proposed_conclusion = COALESCE(?, proposed_conclusion),
                disposition        = COALESCE(?, disposition),
                discussion         = COALESCE(?, discussion)
            WHERE id = ?;
            """,
            (findings_node_id, proposed_conclusion, disposition, discussion, motion_id),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="motion.linked",
            payload={
                "motion_id": motion_id,
                "findings_node_id": findings_node_id,
                "proposed_conclusion": proposed_conclusion,
                "disposition": disposition,
            },
            case_id=row["case_id"],
            entity_table="motions",
            entity_id=motion_id,
        )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    return dict(conn.execute("SELECT * FROM motions WHERE id = ?;", (motion_id,)).fetchone())


# --------------------------------------------------------------------------- #
# apply_motion() -- THE bridge.
# --------------------------------------------------------------------------- #


def apply_motion(conn: sqlite3.Connection, *, motion_id: str, actor_user_id: str) -> dict[str, Any]:
    """Proves `motion_id` CARRIED (a real recorded human vote --
    motions.recorded_by/voted_at, enforced by motions' own CHECK), proposed
    a specific conclusion for a specific node, and has not already been
    applied -- then, in ONE transaction, writes that Conclusion of Law
    (via engine.findings._write_conclusion, this codebase's one and only
    writer of findings_nodes.conclusion) and stamps
    motions.applied_node_id/applied_at (write-once; 0015_motion_conclusion.
    sql's own CHECK already forbids stamping it on anything but a carried,
    conclusion-proposing motion, so this function's own checks below are a
    clean-error backstop in front of that CHECK, not the only thing
    enforcing it).

    Never called automatically by record_vote() (app/meeting.py) -- that
    module has no knowledge of findings_nodes at all, by design (see this
    module's own docstring). The caller (app/routes/meeting.py) invokes
    this explicitly, immediately after recording a carried vote on a
    findings-node motion, inside the SAME request -- but as two separate
    committed transactions (the vote and its application), matching
    0015_motion_conclusion.sql's own comment: "a motion can be 'carried' (a
    vote fact) without yet being 'applied' (its conclusion actually
    written) for at most the width of one transaction."

    Raises MotionNotFound / MotionAlreadyApplied / MotionNotApplicable (this
    motion, as it stands, cannot conclude anything) / NodeNotEligibleForConclusion
    (the motion is fine, but its target node is no longer a live,
    not-yet-concluded current revision -- e.g. it was amended out from under
    this motion after the motion was drafted; the caller's fix is to draft
    a fresh motion against the current revision).
    """
    row = _get_motion(conn, motion_id)

    if row["applied_node_id"] is not None:
        raise MotionAlreadyApplied(motion_id, row["applied_node_id"])
    if row["outcome"] != "carried":
        raise MotionNotApplicable(f"motion {motion_id!r} has not carried (outcome={row['outcome']!r})")
    if row["proposed_conclusion"] is None or row["findings_node_id"] is None:
        raise MotionNotApplicable(f"motion {motion_id!r} proposes no conclusion for any node")
    if row["recorded_by"] is None or row["voted_at"] is None:
        # Backstop only -- motions' own CHECK already forbids this shape.
        raise MotionNotApplicable(f"motion {motion_id!r} carried without a recorded human vote")

    now = _utc_now_iso()
    conn.execute("BEGIN;")
    try:
        _write_conclusion(
            conn,
            node_id=row["findings_node_id"],
            conclusion=row["proposed_conclusion"],
            conclusion_by=row["recorded_by"],
            conclusion_at=row["voted_at"],
        )
        cur = conn.execute(
            "UPDATE motions SET applied_node_id = ?, applied_at = ? "
            "WHERE id = ? AND applied_node_id IS NULL;",
            (row["findings_node_id"], now, motion_id),
        )
        if cur.rowcount != 1:  # pragma: no cover -- single-process SQLite/WAL; belt-and-suspenders
            raise MotionAlreadyApplied(motion_id, row["findings_node_id"])
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="motion.applied",
            payload={
                "motion_id": motion_id,
                "findings_node_id": row["findings_node_id"],
                "conclusion": row["proposed_conclusion"],
            },
            case_id=row["case_id"],
            entity_table="findings_nodes",
            entity_id=row["findings_node_id"],
        )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    return dict(conn.execute("SELECT * FROM motions WHERE id = ?;", (motion_id,)).fetchone())


# --------------------------------------------------------------------------- #
# THE AGENDA. Everything below reads already-durable state (findings_nodes,
# motions, conditions, conflict_disclosures, board_members, decisions) and
# assembles the one view the meeting UI needs -- "which node am I on, how
# many remain, what is unresolved" (this session's own task brief) -- plus
# the handful of small write helpers (ensure_agenda_motions, the two
# fixed/templated motion drafters) that turn "the record" into "the blank
# slots ready for the Chair to fill," matching every real pre-meeting DRAFT
# sample's own shape: the motion language exists before the meeting, the
# vote does not (app.meeting.create_motion()'s own docstring).
#
# NEVER computes or implies an outcome. Every "resolved" flag below means
# only "a recorded human act (a vote, a disclosure, a roll call) already
# exists for this item" -- never "and it was favorable." A failed motion
# counts as resolved (the Board DID act); a tabled/withdrawn one does not
# (the Board explicitly deferred, and per this module's own docstring,
# apply_motion() never applies anything but a carried, conclusion-proposing
# motion, so a node behind a failed motion is intentionally left CARRYING a
# conclusion too -- see apply_motion() for how 'failed' maps to 'not_met'
# when a motion is drafted that way, e.g. an explicit negative motion).
# --------------------------------------------------------------------------- #

import json
import sqlite3
import uuid

_CITATION_FIELDS = (
    "ruleset_key", "scheme", "article", "section", "subsection",
    "district_key", "district_code", "district_name", "panel_title", "label",
    "use_label", "exhibit", "table", "section_title", "standard_letter",
    "standard_title", "table_title",
)


def _new_id() -> str:
    return uuid.uuid4().hex


def _standard_citation_text(conn: sqlite3.Connection, node: sqlite3.Row | dict, *, ruleset_key: str) -> str | None:
    """The full "Article N, Section M, Standard x. (Title)" text for a
    finding node -- the same long-style, standard-letter-aware render
    render/case_findings.py's own `_citation_display()` produces for the
    printed document (its own comment explains why: `citation.render()`
    drops standard_letter/standard_title by design, so a lettered Article 7
    standard needs `render_citation()` instead). Duplicated here in miniature
    rather than imported, matching engine/subdivision_review.py's own
    `_citation_display_for()` -- this module's citation need is one line of
    motion-prefill text, not the full render pipeline.
    """
    from app import citation as citation_mod

    raw = node["citation_json"] if isinstance(node, sqlite3.Row) else node.get("citation_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            raw = None
    if not raw:
        return None
    filtered = {k: v for k, v in raw.items() if k in _CITATION_FIELDS}
    filtered.setdefault("ruleset_key", ruleset_key)
    filtered.setdefault("scheme", ruleset_key if ruleset_key in ("adopted", "draft") else "adopted")
    if "article" not in filtered:
        return None
    try:
        c = citation_mod.Citation(**filtered)
    except TypeError:
        return None
    if c.standard_letter:
        return citation_mod.render_citation(c, scheme=ruleset_key, style="long")
    return citation_mod.render(c, style="long")


def _ruleset_key_for_case(conn: sqlite3.Connection, case_row: sqlite3.Row) -> str:
    row = conn.execute(
        "SELECT ruleset_key FROM rulesets WHERE id = ?;", (case_row["ruleset_id"],)
    ).fetchone()
    return row["ruleset_key"] if row is not None else "adopted"


def list_standards_for_motions(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every live ('finding', superseded_by IS NULL) node carrying enough
    content to be worth a motion -- a stated fact, a first-person question,
    or a quoted standard (never a bare placeholder row).

    RECONCILIATION FIX (2026-08-23, W7 integration pass): originally this
    query required `board_question IS NOT NULL`, which is exactly the set
    the review engine could not resolve on its own -- FACT_RECORDED,
    BOARD_QUESTION, EXCEPTION_FLAGGED-with-a-question, and
    APPLICABILITY_UNKNOWN. But NOT_APPLICABLE, PROCEDURAL_REFERENCE, and
    CONDITION_ATTACHED dispositions (engine/review.py's own evaluate_*
    helpers) set board_question=None -- so under the old query those nodes
    could NEVER get a motion through this (the only HTTP-wired) path, and
    would sit `unresolved=1, conclusion=NULL` in the tree forever, with no
    way for the Board to close them out. That contradicts the real record:
    the adopted Shattuck decision explicitly moves on its not-applicable
    standards too ("To conclude that Article 3, Article 4, Article 5, and
    Article 6 ... are not applicable ..."). This was a genuine split
    between two concurrently-built W7 modules -- app.meeting's own
    (unwired) eligible_nodes_for_motion() already used this WIDER
    condition (body OR board_question OR quoted_standard_text) and drafted
    the correct 'not applicable' wording via draft_text_for_node(); this
    function is now reconciled to match that broader, already-correct
    definition, with ensure_agenda_motions() below carrying the matching
    met/n_a wording fix.
    """
    rows = conn.execute(
        """
        SELECT * FROM findings_nodes
        WHERE case_id = ? AND superseded_by IS NULL AND node_type = 'finding'
          AND (board_question IS NOT NULL OR body IS NOT NULL OR quoted_standard_text IS NOT NULL)
        ORDER BY sort_order;
        """,
        (case_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def find_latest_motion_for_root(conn: sqlite3.Connection, root_id: str) -> dict[str, Any] | None:
    """The most recently drafted motion whose `findings_node_id` points at
    ANY revision under `root_id` -- so a motion drafted against a node,
    then amended (a NEW revision, new node id, SAME root_id), is still
    found. See 0015_motion_conclusion.sql's own header note on this exact
    join shape."""
    row = conn.execute(
        """
        SELECT m.* FROM motions m
        JOIN findings_nodes fn ON fn.id = m.findings_node_id
        WHERE fn.root_id = ?
        ORDER BY m.created_at DESC
        LIMIT 1;
        """,
        (root_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def _latest_motion_of_kind(conn: sqlite3.Connection, case_id: str, kind: str, *, only_unlinked: bool = False) -> dict[str, Any] | None:
    q = "SELECT * FROM motions WHERE case_id = ? AND kind = ?"
    params: list[Any] = [case_id, kind]
    if only_unlinked:
        q += " AND findings_node_id IS NULL"
    q += " ORDER BY created_at DESC LIMIT 1;"
    row = conn.execute(q, params).fetchone()
    return dict(row) if row is not None else None


# --------------------------------------------------------------------------- #
# ensure_agenda_motions() -- idempotent prep. Drafts the blank motions this
# case's agenda needs, so the meeting page can move through it at keyboard
# speed (this session's own instruction) instead of the Chair having to
# type every motion's language live. Safe to call on every page load: never
# creates a second motion for something that already has one.
# --------------------------------------------------------------------------- #


def ensure_agenda_motions(conn: sqlite3.Connection, *, case_id: str, actor_user_id: str) -> dict[str, int]:
    case_row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if case_row is None:
        raise LookupError(f"no case with id {case_id!r}")
    ruleset_key = _ruleset_key_for_case(conn, case_row)

    import app.meeting as app_meeting  # local import: avoids a hard import-time
    #                                     dependency cycle risk between two
    #                                     concurrently-built sibling W7 modules
    #                                     (see this module's own docstring).

    created = {"completeness": 0, "findings": 0, "conditions": 0}

    if _latest_motion_of_kind(conn, case_id, "completeness") is None:
        app_meeting.create_motion(
            conn, case_id=case_id, kind="completeness",
            text=f"To find the application for {case_row['label']} complete and ready for review.",
            sort_order=0, actor_user_id=actor_user_id,
        )
        created["completeness"] = 1

    existing_links = {
        m["findings_node_id"]
        for m in conn.execute(
            "SELECT findings_node_id FROM motions WHERE case_id = ? AND findings_node_id IS NOT NULL;",
            (case_id,),
        ).fetchall()
    }
    for i, node in enumerate(list_standards_for_motions(conn, case_id)):
        # A motion may already exist against an EARLIER revision under the
        # same root_id -- don't draft a duplicate for the current one too.
        if find_latest_motion_for_root(conn, node["root_id"]) is not None:
            continue
        citation_text = _standard_citation_text(conn, node, ruleset_key=ruleset_key)
        label = (node["heading"] or node["number_label"] or "this standard").strip()
        subject = citation_text or label
        # RECONCILIATION FIX (2026-08-23): a NOT_APPLICABLE node (the
        # applicability gate found this standard's subject matter absent)
        # gets the real document's own "is not applicable" wording and
        # proposed_conclusion='n_a' -- matching app.meeting.draft_text_for_node()'s
        # already-correct template -- instead of the affirmative "is
        # consistent with" / 'met' wording every other node gets. Voting
        # 'carried' on "is consistent with" for a standard the engine
        # already determined does not apply would write the wrong
        # conclusion value.
        if node["applicability_verdict"] == "false":
            text = f"To conclude that {subject} is not applicable to this application."
            proposed_conclusion = "n_a"
        else:
            text = f"To conclude that the application is consistent with {subject}."
            proposed_conclusion = "met"
        motion = app_meeting.create_motion(
            conn, case_id=case_id, kind="findings",
            text=text,
            sort_order=10 + i, actor_user_id=actor_user_id,
        )
        set_motion_findings_link(
            conn, motion_id=motion["id"], findings_node_id=node["id"],
            proposed_conclusion=proposed_conclusion, actor_user_id=actor_user_id,
        )
        created["findings"] += 1

    condition_count = conn.execute(
        "SELECT COUNT(*) c FROM conditions WHERE case_id = ? AND superseded_by IS NULL AND status = 'proposed';",
        (case_id,),
    ).fetchone()["c"]
    if condition_count > 0 and _latest_motion_of_kind(conn, case_id, "conditions") is None:
        plural = "condition" if condition_count == 1 else "conditions"
        app_meeting.create_motion(
            conn, case_id=case_id, kind="conditions",
            text=f"To impose the {condition_count} proposed {plural} on the Board's approval of this application.",
            sort_order=900, actor_user_id=actor_user_id,
        )
        created["conditions"] = 1

    return created


#: The one adoption motion's wording, lifted verbatim (this session's own
#: instruction: "lift it from the document; do not compose it") from the
#: ONE adopted (not draft) sample, docs/Findings of Fact and Conclusions of
#: Law/M003, L059 (White Road, Shattuck), Subdivision FoF & CoL 2025.12.18.pdf,
#: p.14 of 16, the "Findings Of Fact" motion block. Never edited, never
#: parameterized -- a fixed constant, matched byte-for-byte by
#: find/verify-adopted logic elsewhere in this app.
ADOPTION_MOTION_TEXT = "To accept and adopt the draft findings of fact and conclusions of law, as amended."

#: Decision-motion text templates, by disposition -- worded after the same
#: real Shattuck "Board Decision" motion ("To approve, with conditions, the
#: subdivision application as discussed and amended."). `{kind}` is the
#: case's application_type, humanized (e.g. "subdivision").
_DECISION_MOTION_TEXT = {
    "approve": "To approve the {kind} application as discussed and amended.",
    "approve_with_conditions": "To approve, with conditions, the {kind} application as discussed and amended.",
    "deny": "To deny the {kind} application.",
    "table": "To table the {kind} application.",
    "withdraw": "To accept the withdrawal of the {kind} application.",
}


def create_adoption_motion(conn: sqlite3.Connection, *, case_id: str, actor_user_id: str) -> dict[str, Any]:
    """Drafts the single, verbatim "accept and adopt ... as amended" motion.
    Idempotent in spirit (a second call when one already exists just
    returns the existing row) -- draft language is not re-created once a
    Chair may already be looking at it.
    """
    import app.meeting as app_meeting

    existing = _latest_motion_of_kind(conn, case_id, "findings", only_unlinked=True)
    if existing is not None and (existing["text"] or "").strip() == ADOPTION_MOTION_TEXT:
        return existing
    return app_meeting.create_motion(
        conn, case_id=case_id, kind="findings", text=ADOPTION_MOTION_TEXT,
        sort_order=950, actor_user_id=actor_user_id,
    )


def create_decision_motion(
    conn: sqlite3.Connection, *, case_id: str, disposition: str, actor_user_id: str, discussion: str | None = None,
) -> dict[str, Any]:
    """Drafts the final disposition motion for one of the five real-world
    outcomes (this session's own task brief; `DISPOSITIONS` above). The
    Chair states which disposition is being moved AT DRAFTING TIME -- never
    inferred later from a vote outcome or free text (this module's own
    "no silent guessing" posture, matching 0016's header).
    """
    import app.meeting as app_meeting

    if disposition not in DISPOSITIONS:
        raise ValidationError([{"field": "disposition", "message": f"must be one of {sorted(DISPOSITIONS)}"}])
    case_row = conn.execute("SELECT application_type FROM cases WHERE id = ?;", (case_id,)).fetchone()
    kind_label = ((case_row["application_type"] if case_row else None) or "application").replace("_", " ")
    text = _DECISION_MOTION_TEXT[disposition].format(kind=kind_label)
    motion = app_meeting.create_motion(
        conn, case_id=case_id, kind="decision", text=text, sort_order=990, actor_user_id=actor_user_id,
    )
    return set_motion_findings_link(
        conn, motion_id=motion["id"], disposition=disposition, discussion=discussion,
        actor_user_id=actor_user_id,
    )


# --------------------------------------------------------------------------- #
# build_agenda() -- the master read. One JSON-shapeable dict; the HTTP layer
# (app/routes/meeting.py) does no further assembly of its own, only
# serializes this.
# --------------------------------------------------------------------------- #


def build_agenda(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    import app.board as board_mod
    import app.meeting as app_meeting

    case_row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if case_row is None:
        raise LookupError(f"no case with id {case_id!r}")
    case = dict(case_row)
    ruleset_key = _ruleset_key_for_case(conn, case_row)

    sitting = board_mod.list_sitting_members(conn)

    # ---- 1. Conflict disclosures --------------------------------------- #
    disclosure_rows = {r["board_member_id"]: r for r in app_meeting.get_conflict_disclosures(conn, case_id)}
    disclosures = []
    for m in sitting:
        row = disclosure_rows.get(m["board_member_id"])
        disclosures.append({
            **m,
            "recorded": row is not None,
            "disclosed": bool(row["disclosed"]) if row is not None else None,
            "recused": bool(row["recused"]) if row is not None else None,
            "nature": row["nature"] if row is not None else None,
        })
    disclosures_resolved = bool(sitting) and all(d["recorded"] for d in disclosures)

    # ---- 2. Completeness -------------------------------------------- #
    completeness_motion = _latest_motion_of_kind(conn, case_id, "completeness")

    # ---- 3. Standards (one motion per contested/judgement node) ------ #
    standards = []
    for node in list_standards_for_motions(conn, case_id):
        motion = find_latest_motion_for_root(conn, node["root_id"])
        standards.append({
            "node_id": node["id"],
            "root_id": node["root_id"],
            "number_label": node["number_label"],
            "heading": node["heading"],
            "board_question": node["board_question"],
            "applicability_verdict": node["applicability_verdict"],
            "conclusion": node["conclusion"],
            "citation_text": _standard_citation_text(conn, node, ruleset_key=ruleset_key),
            "motion": motion,
            "resolved": node["conclusion"] is not None,
        })

    # ---- 4. Conditions vote ------------------------------------------- #
    condition_rows = conn.execute(
        "SELECT * FROM conditions WHERE case_id = ? AND superseded_by IS NULL ORDER BY created_at;",
        (case_id,),
    ).fetchall()
    conditions = [dict(r) for r in condition_rows]
    conditions_motion = _latest_motion_of_kind(conn, case_id, "conditions")
    conditions_applicable = len(conditions) > 0

    # ---- 5. Adoption motion (verbatim) -------------------------------- #
    adoption_motion = None
    for m in app_meeting.get_motions(conn, case_id):
        if m["kind"] == "findings" and m["findings_node_id"] is None and (m["text"] or "").strip() == ADOPTION_MOTION_TEXT:
            adoption_motion = m
            break

    # ---- 6. Decision motion + recorded decision ----------------------- #
    decision_motion = _latest_motion_of_kind(conn, case_id, "decision")
    decision = app_meeting.get_current_decision(conn, case_id)

    # ---- counts --------------------------------------------------------- #
    total = 1 + 1 + len(standards) + (1 if conditions_applicable else 0) + 1 + 1
    resolved = (
        (1 if disclosures_resolved else 0)
        + (1 if completeness_motion and completeness_motion["outcome"] else 0)
        + sum(1 for s in standards if s["resolved"])
        + (1 if conditions_applicable and conditions_motion and conditions_motion["outcome"] else 0)
        + (1 if adoption_motion and adoption_motion["outcome"] else 0)
        + (1 if decision is not None else 0)
    )

    return {
        "case": case,
        "board_members": sitting,
        "disclosures": disclosures,
        "disclosures_resolved": disclosures_resolved,
        "completeness_motion": completeness_motion,
        "standards": standards,
        "conditions": conditions,
        "conditions_motion": conditions_motion,
        "conditions_applicable": conditions_applicable,
        "adoption_motion": adoption_motion,
        "decision_motion": decision_motion,
        "decision": decision,
        "counts": {"total": total, "resolved": resolved, "unresolved": total - resolved},
    }


__all__ = [
    "DISPOSITIONS",
    "DISPOSITION_TO_CASE_OUTCOME",
    "ADOPTION_MOTION_TEXT",
    "MotionNotFound",
    "MotionAlreadyApplied",
    "MotionNotApplicable",
    "NodeNotEligibleForConclusion",
    "ValidationError",
    "set_motion_findings_link",
    "apply_motion",
    "list_standards_for_motions",
    "find_latest_motion_for_root",
    "ensure_agenda_motions",
    "create_adoption_motion",
    "create_decision_motion",
    "build_agenda",
]
