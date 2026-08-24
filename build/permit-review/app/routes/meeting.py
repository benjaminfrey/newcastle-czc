"""app/routes/meeting.py -- the W7 live meeting UI.

Serves the keyboard-first meeting workflow for one case:

    GET   /case/{case_id}/meeting                      the meeting screen (HTML)
    GET   /api/cases/{case_id}/meeting/agenda           the whole agenda (JSON)
    POST  /api/cases/{case_id}/meeting/prepare          idempotently draft blank motions
    POST  /api/cases/{case_id}/meeting/disclosures      record one member's conflict disclosure
    POST  /api/cases/{case_id}/meeting/attendance       record one member's roll-call status
    POST  /api/cases/{case_id}/meeting/motions          draft the decision or adoption motion
    PATCH /api/cases/{case_id}/meeting/motions/{id}     record a motion's vote (and, for a
                                                         findings-node motion that carries,
                                                         apply its Conclusion of Law)
    POST  /api/cases/{case_id}/meeting/nodes/{id}/amend amend a finding's drafted text
                                                         (REQUIRES a non-empty `why`)

Pure HTTP translation layer, matching app/routes/cases.py's and
app/routes/extraction.py's own self-contained-router pattern: every rule
(vocabulary, the framing rule's "only a human sets an outcome") lives in
app/meeting.py (attendance/disclosures/motions/decisions -- a sibling W7
module built in this same directory) and engine/meeting.py (the
motions -> findings_nodes bridge, and the agenda assembler); this module
opens a DB connection per request and maps typed exceptions to the right
status code. `router` mounts defensively in app/main.py's create_app(),
same degrade-gracefully posture as every other router here.

THE FRAMING RULE, restated for this screen specifically: nothing this page
renders may state or imply a conclusion, a disposition, or an outcome the
Board has not actually voted on. Every value this module returns is either
(a) already-durable state written by a prior recorded vote, or (b) a
PREFILLED but unvoted DRAFT (motion text, a disposition a Chair is ABOUT to
move) that the page must render as a draft, never as a result. See
app/templates/meeting.html / app/static/meeting.js for how that is kept
visually unambiguous.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app import board as board_mod
from app import config, db, security
from app import meeting as app_meeting
from engine import findings as findings_mod
from engine import meeting as engine_meeting

router = APIRouter()

_templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


# --------------------------------------------------------------------------- #
# CONTRACT.md §6 envelope helpers -- deliberately duplicated, matching every
# sibling router's own stated reasoning (avoids an app.main import cycle;
# each router stays fully self-contained).
# --------------------------------------------------------------------------- #


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _err(code: str, message: str, status: int, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def _connect() -> sqlite3.Connection:
    db_path = config.DATA_DIR / "permit-review.db"
    conn = db.connect(db_path)
    db.migrate(conn, config.MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    board_mod.ensure_seed_board(conn)
    return conn


async def _json_body(request: Request) -> dict[str, Any] | JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("validation_failed", "request body is not valid JSON", 400)
    if not isinstance(body, dict):
        return _err("validation_failed", "request body must be a JSON object", 400)
    return body


def _map_validation(exc: Exception) -> JSONResponse:
    details = getattr(exc, "details", None)
    return _err("validation_failed", "the request body failed validation", 400, details=details)


# --------------------------------------------------------------------------- #
# GET /case/{case_id}/meeting -- the screen itself.
# --------------------------------------------------------------------------- #


@router.get("/case/{case_id}/meeting", response_class=HTMLResponse)
def meeting_screen(request: Request, case_id: str):
    conn = _connect()
    try:
        try:
            agenda = engine_meeting.build_agenda(conn, case_id)
        except LookupError:
            return _err("case_not_found", f"no case with id {case_id!r}", 404)
        return _templates.TemplateResponse(
            request, "meeting.html", {"case_id": case_id, "case": agenda["case"]},
        )
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# GET /api/cases/{case_id}/meeting/agenda
# --------------------------------------------------------------------------- #


@router.get("/api/cases/{case_id}/meeting/agenda")
def get_agenda_endpoint(case_id: str):
    conn = _connect()
    try:
        try:
            agenda = engine_meeting.build_agenda(conn, case_id)
        except LookupError:
            return _err("case_not_found", f"no case with id {case_id!r}", 404)
        return _ok(agenda)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/meeting/prepare -- idempotent agenda-motion prep.
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/meeting/prepare")
def prepare_agenda_endpoint(case_id: str):
    conn = _connect()
    try:
        user = security.current_user()
        try:
            created = engine_meeting.ensure_agenda_motions(conn, case_id=case_id, actor_user_id=user.id)
        except LookupError:
            return _err("case_not_found", f"no case with id {case_id!r}", 404)
        agenda = engine_meeting.build_agenda(conn, case_id)
        return _ok({"created": created, "agenda": agenda})
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/meeting/disclosures
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/meeting/disclosures")
async def record_disclosure_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        board_member_id = body.get("board_member_id")
        if not board_member_id:
            return _err("validation_failed", "board_member_id is required", 400,
                        details=[{"field": "board_member_id", "message": "required"}])
        try:
            row = app_meeting.record_conflict_disclosure(
                conn, case_id=case_id, board_member_id=board_member_id,
                disclosed=bool(body.get("disclosed", False)),
                recused=bool(body.get("recused", False)),
                nature=body.get("nature"),
                actor_user_id=user.id,
            )
        except app_meeting.ValidationError as exc:
            return _map_validation(exc)
        except sqlite3.IntegrityError as exc:
            return _err("validation_failed", f"could not record disclosure: {exc}", 400)
        return _ok(row)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/meeting/attendance
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/meeting/attendance")
async def record_attendance_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        board_member_id = body.get("board_member_id")
        if not board_member_id:
            return _err("validation_failed", "board_member_id is required", 400,
                        details=[{"field": "board_member_id", "message": "required"}])
        try:
            row = app_meeting.record_attendance(
                conn, case_id=case_id, board_member_id=board_member_id,
                present=bool(body.get("present", True)),
                role_note=body.get("role_note"),
                actor_user_id=user.id,
            )
        except sqlite3.IntegrityError as exc:
            return _err("validation_failed", f"could not record attendance: {exc}", 400)
        return _ok(row)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/meeting/motions -- drafts the ADOPTION motion
# (fixed, verbatim text) or a DECISION motion (one of the five real
# dispositions). Per-standard/completeness/conditions motions are drafted
# by /prepare above, never through this endpoint, so their text is always
# the mechanically-derived form -- this endpoint exists only for the two
# motions whose content depends on a Chair's explicit choice made AT THE
# MEETING (which disposition to move) or a fixed constant (the adoption
# wording) that must never be free-typed.
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/meeting/motions")
async def create_motion_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        motion_kind = body.get("kind")
        try:
            if motion_kind == "adoption":
                motion = engine_meeting.create_adoption_motion(conn, case_id=case_id, actor_user_id=user.id)
            elif motion_kind == "decision":
                disposition = body.get("disposition")
                if not disposition:
                    return _err("validation_failed", "disposition is required for a decision motion", 400,
                                details=[{"field": "disposition", "message": "required"}])
                motion = engine_meeting.create_decision_motion(
                    conn, case_id=case_id, disposition=disposition,
                    discussion=body.get("discussion"), actor_user_id=user.id,
                )
            else:
                return _err(
                    "validation_failed",
                    "kind must be 'adoption' or 'decision' -- every other motion is drafted "
                    "automatically by POST .../meeting/prepare",
                    400, details=[{"field": "kind", "message": "must be 'adoption' or 'decision'"}],
                )
        except engine_meeting.ValidationError as exc:
            return _map_validation(exc)
        except LookupError:
            return _err("case_not_found", f"no case with id {case_id!r}", 404)
        return _ok(motion)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# PATCH /api/cases/{case_id}/meeting/motions/{motion_id} -- record the vote,
# and, when it CARRIES a findings-node motion, apply its Conclusion of Law
# in the same request (two committed transactions -- the vote, then the
# application -- per engine.meeting.apply_motion()'s own documented posture).
# --------------------------------------------------------------------------- #


@router.patch("/api/cases/{case_id}/meeting/motions/{motion_id}")
async def record_vote_endpoint(case_id: str, motion_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        motion_row = conn.execute("SELECT * FROM motions WHERE id = ? AND case_id = ?;", (motion_id, case_id)).fetchone()
        if motion_row is None:
            return _err("motion_not_found", f"no motion {motion_id!r} on case {case_id!r}", 404)

        details: list[dict[str, str]] = []
        for f in ("moved_by", "seconded_by", "votes_yes", "votes_no", "votes_abstain", "outcome"):
            if body.get(f) is None:
                details.append({"field": f, "message": "required"})
        if details:
            return _err("validation_failed", "the request body failed validation", 400, details=details)

        discussion = body.get("discussion")
        if discussion is not None:
            try:
                engine_meeting.set_motion_findings_link(
                    conn, motion_id=motion_id, discussion=discussion, actor_user_id=user.id,
                )
            except engine_meeting.ValidationError as exc:
                return _map_validation(exc)

        try:
            voted = app_meeting.record_vote(
                conn, motion_id=motion_id,
                moved_by=body["moved_by"], seconded_by=body["seconded_by"],
                votes_yes=int(body["votes_yes"]), votes_no=int(body["votes_no"]),
                votes_abstain=int(body["votes_abstain"]), outcome=body["outcome"],
                recorded_by=user.id, actor_user_id=user.id,
            )
        except app_meeting.ValidationError as exc:
            return _map_validation(exc)
        except LookupError:
            return _err("motion_not_found", f"no motion {motion_id!r} on case {case_id!r}", 404)

        applied = None
        apply_error = None
        if voted["outcome"] == "carried" and voted["findings_node_id"] and voted["proposed_conclusion"]:
            try:
                applied = engine_meeting.apply_motion(conn, motion_id=motion_id, actor_user_id=user.id)
            except engine_meeting.MotionAlreadyApplied:
                pass  # already applied by an earlier request -- not an error to report twice
            except (engine_meeting.MotionNotApplicable, findings_mod.NodeNotEligibleForConclusion) as exc:
                apply_error = str(exc)

        decision_recorded = None
        if voted["outcome"] == "carried" and voted["kind"] == "decision" and voted.get("disposition"):
            case_row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
            existing = app_meeting.get_current_decision(conn, case_id)
            already_this_motion = existing is not None and existing["motion_id"] == motion_id
            if case_row is not None and not already_this_motion:
                outcome = engine_meeting.DISPOSITION_TO_CASE_OUTCOME[voted["disposition"]]
                decision_recorded = app_meeting.record_outcome(
                    conn, case_id=case_id, ruleset_id=case_row["ruleset_id"], outcome=outcome,
                    recorded_by=user.id, motion_id=motion_id,
                    meeting_date=case_row["meeting_date"], actor_user_id=user.id,
                )

        motion_final = conn.execute("SELECT * FROM motions WHERE id = ?;", (motion_id,)).fetchone()
        return _ok({
            "motion": dict(motion_final),
            "applied": applied,
            "apply_error": apply_error,
            "decision_recorded": decision_recorded,
        })
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/meeting/nodes/{node_id}/amend -- amend a
# finding's drafted text. `why` is REQUIRED -- engine.findings.amend_node()
# itself refuses a blank reason (ValidationError, writes nothing); this
# endpoint adds no separate check because that one already covers it, but
# returns the same validation_failed shape everything else here does.
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/meeting/nodes/{node_id}/amend")
async def amend_node_endpoint(case_id: str, node_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        node = findings_mod.get_node(conn, node_id)
        if node is None or node["case_id"] != case_id:
            return _err("node_not_found", f"no findings_nodes row {node_id!r} on case {case_id!r}", 404)
        if node["conclusion"] is not None:
            return _err(
                "already_concluded",
                "this standard's finding already carries a Board-recorded Conclusion of Law -- "
                "amending it now would silently change an adopted record. Bring a reconsideration "
                "motion instead.",
                409,
            )

        kwargs: dict[str, Any] = {}
        if "body" in body:
            kwargs["body"] = body["body"]
        if "quoted_standard_text" in body:
            kwargs["quoted_standard_text"] = body["quoted_standard_text"]
        if "board_question" in body:
            kwargs["board_question"] = body["board_question"]
        if kwargs.get("body") is not None and "finding_source" not in kwargs:
            kwargs["finding_source"] = "operator"
            kwargs["provenance"] = {"operator": {"user_id": user.id, "note": "amended at meeting"}}

        try:
            amended = findings_mod.amend_node(
                conn, node_id=node_id, actor_user_id=user.id, reason=body.get("why"), **kwargs,
            )
        except findings_mod.ValidationError as exc:
            return _map_validation(exc)
        except findings_mod.NotCurrentRevision as exc:
            return _err(
                "not_current_revision",
                f"a newer revision already exists ({exc.current_id}) -- reload the agenda",
                409,
            )

        # A motion drafted against the OLD revision is still valid (found via
        # root_id) -- nothing to relink here; see
        # engine.meeting.find_latest_motion_for_root()'s own doc comment.
        return _ok(amended)
    finally:
        conn.close()
