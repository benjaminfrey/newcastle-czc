"""Implements CONTRACT.md §6's HTTP envelope (`{"ok":..., "data"|"error":...}`)
for the W3 case-lifecycle endpoints:

    POST   /api/cases
    GET    /api/cases
    GET    /api/cases/{id}
    PATCH  /api/cases/{id}/dates
    POST   /api/cases/{id}/status

Pure HTTP translation layer -- every rule (the binding gate, the state
machine, date-kind validation) lives in app/cases.py; this module opens a DB
connection per request, calls into app.cases, and maps its typed exceptions
to the right status code and error code. No uploads, no OCR, no LLM, no PII
(CONTRACT.md §1.2) -- a case here is metadata + dates + status only.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import cases as cases_mod
from app.config import DB_PATH
from app.db import connect
from app.security import current_user

router = APIRouter()


# --------------------------------------------------------------------------- #
# CONTRACT.md §6 envelope helpers -- deliberately duplicated from
# app/main.py's identical two functions rather than imported, to avoid a
# main.py <-> app.routes.cases import cycle (main.py includes this router).
# --------------------------------------------------------------------------- #


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def err(code: str, message: str, status: int, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"ok": False, "error": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def _conn():
    return connect(DB_PATH)


async def _json_body(request: Request) -> dict[str, Any] | JSONResponse:
    """Parses the request body; returns a JSONResponse error in place of a
    dict on failure, so callers can `body = await _json_body(request)` then
    `if isinstance(body, JSONResponse): return body`."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return err("validation_failed", "request body is not valid JSON", 400)
    if not isinstance(body, dict):
        return err("validation_failed", "request body must be a JSON object", 400)
    return body


# --------------------------------------------------------------------------- #
# POST /api/cases
# --------------------------------------------------------------------------- #


@router.post("/api/cases")
async def create_case_endpoint(request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = current_user()
    conn = _conn()
    try:
        try:
            case = cases_mod.create_case(
                conn,
                application_type=body.get("application_type"),
                map_lot=body.get("map_lot"),
                situs_address=body.get("situs_address"),
                applicant_name=body.get("applicant_name"),
                case_number=body.get("case_number"),
                label=body.get("label"),
                district_key=body.get("district_key"),
                ruleset_key=body.get("ruleset_key"),
                is_scratch=bool(body.get("is_scratch", False)),
                binding_override=bool(body.get("binding_override", False)),
                override_reason=body.get("override_reason"),
                actor_user_id=user.id,
            )
        except cases_mod.ValidationError as exc:
            return err("validation_failed", "the request body failed validation", 400, details=exc.details)
        except cases_mod.UnknownRuleset as exc:
            return err("unknown_ruleset", str(exc), 404)
        except cases_mod.NonBindingRulesetRefused as exc:
            return err("non_binding_ruleset", str(exc), 403)
        return ok(case)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# GET /api/cases
# --------------------------------------------------------------------------- #


@router.get("/api/cases")
def list_cases_endpoint(
    status: str | None = None,
    ruleset_key: str | None = None,
    is_scratch: bool | None = None,
):
    if status is not None and status not in cases_mod.STATUSES:
        return err("validation_failed", f"unknown status {status!r}", 400,
                   details=[{"field": "status", "message": f"must be one of {list(cases_mod.STATUSES)}"}])

    conn = _conn()
    try:
        rows = cases_mod.list_cases(conn, status=status, ruleset_key=ruleset_key, is_scratch=is_scratch)
        return ok({"cases": rows, "count": len(rows)})
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# GET /api/cases/{id}
# --------------------------------------------------------------------------- #


@router.get("/api/cases/{case_id}")
def get_case_endpoint(case_id: str):
    conn = _conn()
    try:
        case = cases_mod.get_case(conn, case_id)
        if case is None:
            return err("case_not_found", f"no case with id {case_id!r}", 404)
        return ok({
            "case": case,
            "dates": cases_mod.case_dates_for(conn, case_id),
            "history": cases_mod.case_history_for(conn, case_id),
        })
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# PATCH /api/cases/{id}/dates
# --------------------------------------------------------------------------- #


@router.patch("/api/cases/{case_id}/dates")
async def record_dates_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = current_user()
    conn = _conn()
    try:
        try:
            result = cases_mod.record_dates(
                conn,
                case_id,
                entries=body.get("dates"),
                why=body.get("why"),
                actor_user_id=user.id,
            )
        except cases_mod.CaseNotFound:
            return err("case_not_found", f"no case with id {case_id!r}", 404)
        except cases_mod.ValidationError as exc:
            return err("validation_failed", "the request body failed validation", 400, details=exc.details)
        return ok(result)
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{id}/status
# --------------------------------------------------------------------------- #


@router.post("/api/cases/{case_id}/status")
async def transition_status_endpoint(case_id: str, request: Request):
    body = await _json_body(request)
    if isinstance(body, JSONResponse):
        return body

    user = current_user()
    conn = _conn()
    try:
        try:
            case = cases_mod.transition_status(
                conn,
                case_id,
                to_status=body.get("to_status"),
                why=body.get("why"),
                actor_user_id=user.id,
            )
        except cases_mod.CaseNotFound:
            return err("case_not_found", f"no case with id {case_id!r}", 404)
        except cases_mod.ValidationError as exc:
            return err("validation_failed", "the request body failed validation", 400, details=exc.details)
        except cases_mod.InvalidTransition as exc:
            return err(
                "invalid_transition", str(exc), 409,
                details=[{"from_status": exc.from_status, "to_status": exc.to_status,
                          "allowed": sorted(exc.allowed)}],
            )
        return ok(case)
    finally:
        conn.close()
