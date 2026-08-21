"""app/routes/extraction.py — the W4 "operator confirm UI" HTTP layer.

Implements CONTRACT.md §6's envelope for the field-decision actions and
serves the server-rendered Jinja2 extraction-review screen for one case:

    GET   /cases/{case_id}/extraction              the review screen (HTML)
    POST  /api/cases/{case_id}/fields/confirm       confirm one candidate
    POST  /api/cases/{case_id}/fields/override      type a corrected value
    POST  /api/cases/{case_id}/fields/not-applicable  mark a field N/A
    GET   /api/blobs/{blob_id}                      serve one blob's bytes,
                                                     inline, so an operator
                                                     can verify a candidate
                                                     against its source page
                                                     without leaving the app

Pure HTTP translation layer — every rule (what a candidate is, what
"contested" means, the confirm/override/not-applicable state machine) lives
in app/extraction.py; this module opens a DB connection per request, calls
into it, and maps typed exceptions to the right status code and error code.
Matches app/routes/documents.py's self-contained-router pattern: `router`
mounts defensively in app/main.py's create_app() (`_try_import` then
`app.include_router(...)`), so this file being broken or absent degrades
the app rather than crashing it.

NO extraction happens here — no OCR, no vision, no LLM call. This module
only reads field_candidates rows a separate, not-yet-built extraction pass
already wrote, and records a human's decision about them.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app import config, db, extraction as extraction_mod, security

router = APIRouter()

_templates = Jinja2Templates(directory=str(config.TEMPLATES_DIR))


# --------------------------------------------------------------------------- #
# CONTRACT.md §6 envelope helpers — deliberately duplicated from
# app/routes/cases.py's identical two functions (same reasoning: avoids an
# import cycle back through app/main.py, and each router stays fully
# self-contained per that module's own precedent).
# --------------------------------------------------------------------------- #


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _err(code: str, message: str, status: int, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def _connect() -> sqlite3.Connection:
    # Resolved from config.DATA_DIR at CALL time, matching app/routes/
    # documents.py's own _connect() — lets a test monkeypatch
    # app.config.DATA_DIR to a throwaway tmp_path and get a fully isolated
    # database.
    db_path = config.DATA_DIR / "permit-review.db"
    conn = db.connect(db_path)
    db.migrate(conn, config.MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    return conn


async def _json_body(request: Request) -> dict[str, Any] | JSONResponse:
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return _err("validation_failed", "request body is not valid JSON", 400)
    if not isinstance(body, dict):
        return _err("validation_failed", "request body must be a JSON object", 400)
    return body


def _map_extraction_error(exc: extraction_mod.ExtractionError) -> JSONResponse:
    if isinstance(exc, extraction_mod.CaseNotFound):
        return _err("case_not_found", str(exc), 404)
    if isinstance(exc, extraction_mod.CandidateNotFound):
        return _err("candidate_not_found", str(exc), 404)
    if isinstance(exc, extraction_mod.ValidationError):
        return _err("validation_failed", "the request body failed validation", 400, details=exc.details)
    return _err("extraction_error", str(exc), 400)  # pragma: no cover — exhaustive above


# --------------------------------------------------------------------------- #
# GET /cases/{case_id}/extraction — the review screen.
# --------------------------------------------------------------------------- #


@router.get("/cases/{case_id}/extraction", response_class=HTMLResponse)
def extraction_review_page(request: Request, case_id: str):
    conn = _connect()
    try:
        case_row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
        if case_row is None:
            return _err("case_not_found", f"no case with id {case_id!r}", 404)
        case = dict(case_row)
        case["is_scratch"] = bool(case["is_scratch"])

        fields = extraction_mod.list_case_fields(conn, case_id)
        worklist = extraction_mod.list_absence_worklist(conn, case_id, actor_user_id=security.current_user().id)
        generation = extraction_mod.case_form_generation(conn, case_id)

        contested_count = sum(1 for f in fields if f["contested"])
        state_counts: dict[str, int] = {}
        for f in fields:
            state_counts[f["display_state"]] = state_counts.get(f["display_state"], 0) + 1

        return _templates.TemplateResponse(
            request, "extraction_review.html",
            {
                "review_available": True,
                "case": case,
                "fields": fields,
                "field_count": len(fields),
                "contested_count": contested_count,
                "state_counts": state_counts,
                "worklist": worklist,
                "generation": generation,
                "field_value_states": extraction_mod.FIELD_VALUE_STATES,
            },
        )
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/fields/confirm
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/fields/confirm")
async def confirm_field_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        try:
            field = extraction_mod.confirm_field(
                conn, case_id,
                field_def_id=body.get("field_def_id"),
                subject_key=body.get("subject_key"),
                candidate_id=body.get("candidate_id"),
                why=body.get("why"),
                actor_user_id=user.id,
            )
        except extraction_mod.ExtractionError as exc:
            return _map_extraction_error(exc)
        return _ok({"field": field})
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/fields/override
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/fields/override")
async def override_field_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        try:
            field = extraction_mod.override_field(
                conn, case_id,
                field_def_id=body.get("field_def_id"),
                subject_key=body.get("subject_key"),
                value_num=body.get("value_num"),
                value_text=body.get("value_text"),
                unit=body.get("unit"),
                reason=body.get("reason"),
                actor_user_id=user.id,
            )
        except extraction_mod.ExtractionError as exc:
            return _map_extraction_error(exc)
        return _ok({"field": field})
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{case_id}/fields/not-applicable
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/fields/not-applicable")
async def mark_not_applicable_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = security.current_user()
    conn = _connect()
    try:
        try:
            field = extraction_mod.mark_not_applicable(
                conn, case_id,
                field_def_id=body.get("field_def_id"),
                subject_key=body.get("subject_key"),
                why=body.get("why"),
                actor_user_id=user.id,
            )
        except extraction_mod.ExtractionError as exc:
            return _map_extraction_error(exc)
        return _ok({"field": field})
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# GET /api/blobs/{blob_id} — read-only, inline byte-serve.
#
# "Show the page thumbnail or the bbox crop for a candidate where feasible,
# so the operator can verify without opening [a separate viewer]." Neither
# page thumbnails nor bbox-cropped raster images exist anywhere in this app
# yet (pages.thumb_blob_id is always NULL — no thumbnailer has been built;
# that is a later, vision-adjacent workflow, out of W4's no-vision scope).
# What DOES already exist is the source document's own blob
# (documents.blob_id, committed by app/blobs.py at upload time) — serving
# THAT, with the browser's native inline PDF viewer honoring a `#page=N`
# fragment the template appends, is the "verify without leaving the app"
# affordance that is actually feasible today. If a later workflow populates
# pages.thumb_blob_id, this same route already serves it — the template
# only has to link to it.
# --------------------------------------------------------------------------- #


@router.get("/api/blobs/{blob_id}")
def get_blob(blob_id: str):
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM blobs WHERE id = ?;", (blob_id,)).fetchone()
        if row is None:
            return _err("blob_not_found", f"no blob with id {blob_id!r}", 404)
        blob = dict(row)
    finally:
        conn.close()

    # Resolved from config.DATA_DIR at CALL time, by sha256 — mirrors
    # app/blobs.py:_blob_target_path() exactly (its own comment explains why:
    # config.BLOBS_DIR is computed once at app.config's IMPORT time and goes
    # stale under a test's config.DATA_DIR monkeypatch; rel_path as stored,
    # "data/blobs/<ab>/<sha>", is only ever correct relative to DATA_DIR
    # itself, never a fixed APP_ROOT offset). The sha256[0:2]/sha256 shape is
    # still asserted below as a containment check (CONTRACT.md §1 S5) even
    # though nothing here is user-controlled (blob_id only selects a DB row).
    blobs_dir = config.DATA_DIR / "blobs"
    target = blobs_dir / blob["sha256"][:2] / blob["sha256"]
    if blobs_dir not in target.parents or not target.is_file():
        return _err("blob_not_found", f"blob {blob_id!r} is missing on disk", 404)

    filename = blob.get("original_name") or blob_id
    return FileResponse(
        path=str(target),
        media_type=blob["media_type"],
        filename=filename,
        content_disposition_type="inline",
    )
