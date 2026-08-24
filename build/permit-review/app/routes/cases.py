"""Implements CONTRACT.md §6's HTTP envelope (`{"ok":..., "data"|"error":...}`)
for the W3 case-lifecycle endpoints:

    POST   /api/cases
    GET    /api/cases
    GET    /api/cases/{id}
    PATCH  /api/cases/{id}/dates
    POST   /api/cases/{id}/status

...and the W6 "draft document" endpoint (CONTRACT.md §10):

    POST   /api/cases/{id}/findings/render

...and the W7 "adopted final" endpoint (render/case_findings.py:render_adopted_final()):

    POST   /api/cases/{id}/findings/adopt

Pure HTTP translation layer -- every rule (the binding gate, the state
machine, date-kind validation) lives in app/cases.py; this module opens a DB
connection per request, calls into app.cases, and maps its typed exceptions
to the right status code and error code. No uploads, no OCR, no LLM, no PII
(CONTRACT.md §1.2) -- a case here is metadata + dates + status only.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import cases as cases_mod
from app.audit import append_event
from app.config import APP_ROOT, DB_PATH, EXPORTS_DIR
from app.db import connect
from app.security import current_user
from render import case_findings as case_findings_mod

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


# --------------------------------------------------------------------------- #
# POST /api/cases/{id}/findings/render -- CONTRACT.md §10.3
#
# Assembles the case's current findings_nodes tree into a PDF
# (render.case_findings, read-only against the DB) and, on success, records
# a `generated_documents` row (kind='findings_draft') plus an `events` row
# in the SAME transaction -- CONTRACT.md §3.3's "every mutation appends an
# events row in the same transaction", matching app/cases.py's own write
# pattern rather than app/main.py's worksheet endpoint (which has no
# generated_documents table row to write, being a bare, caseless excerpt).
# This is the row engine/deadlines.py's F8 check already reads
# (`generated_documents.kind IN ('findings_draft','findings_final')`) --
# wiring this write is what lets that already-built check ever see one.
# --------------------------------------------------------------------------- #


def _rel_export_path(p) -> str:
    resolved = p.resolve()
    exports_resolved = EXPORTS_DIR.resolve()
    if exports_resolved != resolved and exports_resolved not in resolved.parents:
        raise ValueError("CONTRACT.md 1 S5: renderer wrote outside data/exports/")
    return str(resolved.relative_to(APP_ROOT.resolve()))


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


@router.post("/api/cases/{case_id}/findings/render")
async def render_findings_endpoint(case_id: str, request: Request):
    try:
        raw_body = await request.json()
    except Exception:  # noqa: BLE001 -- an empty/absent body is fine; provenance just defaults off
        raw_body = {}
    body = raw_body if isinstance(raw_body, dict) else {}
    provenance = bool(body.get("provenance", False))

    if shutil.which("pandoc") is None or shutil.which("typst") is None:
        missing = "pandoc" if shutil.which("pandoc") is None else "typst"
        return err("render_unavailable", f"required tool not found on PATH: {missing}", 500)

    user = current_user()
    conn = _conn()
    try:
        case = cases_mod.get_case(conn, case_id)
        if case is None:
            return err("case_not_found", f"no case with id {case_id!r}", 404)

        try:
            pdf_path, unresolved = case_findings_mod.render_case_findings(
                conn, case_id, EXPORTS_DIR, provenance=provenance,
            )
        except case_findings_mod.CaseNotFound:
            return err("case_not_found", f"no case with id {case_id!r}", 404)
        except case_findings_mod.FindingsRenderError as exc:
            return err("render_failed", str(exc), 500)

        try:
            rel = _rel_export_path(pdf_path)
        except ValueError as exc:
            return err("render_failed", str(exc), 500)
        if not pdf_path.exists():
            return err("render_failed", "renderer reported success but wrote no file", 500)
        data_bytes = pdf_path.read_bytes()
        if not data_bytes:
            return err("render_failed", "renderer produced a zero-byte file", 500)
        sha = hashlib.sha256(data_bytes).hexdigest()

        doc_id = uuid.uuid4().hex
        now = _utc_now_iso()
        conn.execute("BEGIN;")
        try:
            conn.execute(
                """
                INSERT INTO generated_documents (
                    id, case_id, case_review_id, ruleset_id, kind, rel_path, sha256,
                    byte_size, template, renderer, unresolved_json, generated_at,
                    created_at, actor_user_id
                ) VALUES (?, ?, NULL, ?, 'findings_draft', ?, ?, ?, ?, 'pandoc->typst', ?, ?, ?, ?);
                """,
                (
                    doc_id, case_id, case["ruleset_id"], rel, sha, len(data_bytes),
                    "style/findings-template.typ", json.dumps(unresolved), now, now, user.id,
                ),
            )
            append_event(
                conn,
                actor_user_id=user.id,
                kind="findings.rendered",
                payload={
                    "case_id": case_id, "generated_document_id": doc_id, "rel_path": rel,
                    "sha256": sha, "byte_size": len(data_bytes), "unresolved_count": len(unresolved),
                },
                case_id=case_id,
                entity_table="generated_documents",
                entity_id=doc_id,
            )
            conn.execute("COMMIT;")
        except Exception as exc:  # noqa: BLE001 -- deliberately broad: roll back, then re-raise unchanged
            if conn.in_transaction:
                conn.execute("ROLLBACK;")
            raise exc

        return ok({
            "id": doc_id, "path": rel, "bytes": len(data_bytes), "sha256": sha,
            "unresolved": unresolved, "generated_at": now,
        })
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# GET /api/cases/{id}/findings/documents -- prior findings-draft renders,
# newest first, for the case-detail page's "regenerate" panel.
# --------------------------------------------------------------------------- #


@router.get("/api/cases/{case_id}/findings/documents")
def list_findings_documents_endpoint(case_id: str):
    conn = _conn()
    try:
        case = cases_mod.get_case(conn, case_id)
        if case is None:
            return err("case_not_found", f"no case with id {case_id!r}", 404)
        rows = conn.execute(
            """
            SELECT id, rel_path, sha256, byte_size, unresolved_json, generated_at
            FROM generated_documents
            WHERE case_id = ? AND kind IN ('findings_draft', 'findings_final')
            ORDER BY generated_at DESC;
            """,
            (case_id,),
        ).fetchall()
        docs = []
        for r in rows:
            d = dict(r)
            try:
                d["unresolved_count"] = len(json.loads(d.pop("unresolved_json")))
            except (TypeError, ValueError):
                d["unresolved_count"] = None
                d.pop("unresolved_json", None)
            docs.append(d)
        return ok({"documents": docs})
    finally:
        conn.close()


# --------------------------------------------------------------------------- #
# POST /api/cases/{id}/findings/adopt -- W7: "produce adopted final".
#
# Refuses (409) unless render.case_findings.verify_adopted() finds a REAL
# carried adoption motion (verbatim wording) and a REAL recorded decision --
# this endpoint never adopts anything itself, it only records what already
# happened. On success: renders via render.case_findings.render_adopted_final()
# (draft=False, provenance=False, no second renderer -- it reuses
# build_case_findings_nodes()/render_nodes()/build-findings.sh exactly like
# the draft route above), writes ONE generated_documents row (kind=
# 'findings_final', carrying BOTH the PDF file's own sha256/byte_size AND
# the separate content_sha256 + snapshot_rel_path 0018_adopted_final.sql
# added) plus ONE events row, in the same transaction (CONTRACT.md §3.3) --
# exactly the draft route's own
# pattern above. THEN, in a second transaction, feeds the decision date into
# the EXISTING clock engine (app.cases.record_dates -> a 'decision_issued'
# case_milestones row -> engine.deadlines picks it up the next time anything
# computes this case's deadlines, e.g. the case-detail page) so the §8.f.1
# Clerk-filing clock and the §23.d.1 appeal window it starts become visible
# without this route reimplementing any clock arithmetic itself. The
# response's `downstream_clocks` block reports what engine.deadlines.
# compute_deadlines() returns immediately after that write, for the caller
# to see without a second round trip.
# --------------------------------------------------------------------------- #


def _deadline_view(d) -> dict[str, Any]:
    return {
        "clock_key": d.clock_key,
        "label": d.label,
        "citation": d.citation_short,
        "status": d.status,
        "start_event": d.start_event,
        "start_date": d.start_date.isoformat() if d.start_date else None,
        "due_date": d.due_date.isoformat() if d.due_date else None,
        "satisfying_event": d.satisfying_event,
        "satisfied_at": d.satisfied_at.isoformat() if d.satisfied_at else None,
    }


@router.post("/api/cases/{case_id}/findings/adopt")
async def produce_adopted_final_endpoint(case_id: str):
    if shutil.which("pandoc") is None or shutil.which("typst") is None:
        missing = "pandoc" if shutil.which("pandoc") is None else "typst"
        return err("render_unavailable", f"required tool not found on PATH: {missing}", 500)

    user = current_user()
    conn = _conn()
    try:
        case = cases_mod.get_case(conn, case_id)
        if case is None:
            return err("case_not_found", f"no case with id {case_id!r}", 404)

        try:
            result = case_findings_mod.render_adopted_final(conn, case_id, EXPORTS_DIR)
        except case_findings_mod.CaseNotFound:
            return err("case_not_found", f"no case with id {case_id!r}", 404)
        except case_findings_mod.NotAdoptedError as exc:
            return err("not_adopted", str(exc), 409)
        except case_findings_mod.FindingsRenderError as exc:
            return err("render_failed", str(exc), 500)

        try:
            pdf_rel = _rel_export_path(result.pdf_path)
            snapshot_rel = _rel_export_path(result.snapshot_path)
        except ValueError as exc:
            return err("render_failed", str(exc), 500)

        doc_id = uuid.uuid4().hex
        now = _utc_now_iso()
        conn.execute("BEGIN;")
        try:
            conn.execute(
                """
                INSERT INTO generated_documents (
                    id, case_id, case_review_id, ruleset_id, kind, rel_path, sha256,
                    byte_size, template, renderer, unresolved_json, content_sha256,
                    snapshot_rel_path, generated_at, created_at, actor_user_id
                ) VALUES (?, ?, NULL, ?, 'findings_final', ?, ?, ?, ?, 'pandoc->typst', ?, ?, ?, ?, ?, ?);
                """,
                (
                    doc_id, case_id, case["ruleset_id"], pdf_rel, result.pdf_sha256,
                    result.pdf_byte_size, "style/findings-template.typ",
                    json.dumps(result.unresolved_inventory), result.content_sha256,
                    snapshot_rel, now, now, user.id,
                ),
            )
            append_event(
                conn,
                actor_user_id=user.id,
                kind="findings.adopted",
                payload={
                    "case_id": case_id, "generated_document_id": doc_id,
                    "rel_path": pdf_rel, "pdf_sha256": result.pdf_sha256,
                    "content_sha256": result.content_sha256,
                    "snapshot_rel_path": snapshot_rel,
                    "byte_size": result.pdf_byte_size,
                    "adoption_motion_id": result.adoption_motion_id,
                    "decision_id": result.decision_id,
                },
                case_id=case_id,
                entity_table="generated_documents",
                entity_id=doc_id,
            )
            conn.execute("COMMIT;")
        except Exception as exc:  # noqa: BLE001 -- roll back, then re-raise unchanged
            if conn.in_transaction:
                conn.execute("ROLLBACK;")
            raise exc

        # Second, separate transaction (app.cases.record_dates manages its
        # own BEGIN/COMMIT) -- feeds the recorded decision into the existing
        # deadline engine. Skipped if a live 'decision_issued' milestone for
        # this exact date is already recorded, so re-running this endpoint
        # (e.g. after an operator re-triggers it) never piles up duplicate
        # milestone rows for the same real-world fact.
        decision_row = conn.execute(
            "SELECT decided_at FROM decisions WHERE id = ?;", (result.decision_id,)
        ).fetchone()
        decided_on = (decision_row["decided_at"] or "")[:10] if decision_row else None
        milestones_recorded: list[str] = []
        if decided_on:
            already = conn.execute(
                """
                SELECT 1 FROM case_milestones
                WHERE case_id = ? AND kind = 'decision_issued' AND superseded_by IS NULL
                  AND substr(occurred_on, 1, 10) = ?;
                """,
                (case_id, decided_on),
            ).fetchone()
            if already is None:
                cases_mod.record_dates(
                    conn, case_id,
                    entries=[{
                        "kind": "decision_issued", "occurred_on": decided_on,
                        "note": f"Adopted final produced; decision {result.decision_id} recorded.",
                    }],
                    why="Board adopted the findings of fact and decided the application "
                        f"(decisions.id={result.decision_id}); recording the decision date "
                        "starts the §8.f.1 Clerk-filing clock.",
                    actor_user_id=user.id,
                )
                milestones_recorded.append("decision_issued")

        try:
            clocks = case_findings_mod.downstream_clocks(conn, case_id)
            downstream = [_deadline_view(d) for d in clocks]
            downstream_error = None
        except Exception as exc:  # noqa: BLE001 -- reporting-only; the adopted final is already saved
            downstream = []
            downstream_error = str(exc)

        return ok({
            "id": doc_id,
            "path": pdf_rel,
            "bytes": result.pdf_byte_size,
            "pdf_sha256": result.pdf_sha256,
            "content_sha256": result.content_sha256,
            "snapshot_path": snapshot_rel,
            "unresolved": result.unresolved_inventory,
            "adoption_motion_id": result.adoption_motion_id,
            "decision_id": result.decision_id,
            "generated_at": now,
            "milestones_recorded": milestones_recorded,
            "downstream_clocks": downstream,
            "downstream_clocks_error": downstream_error,
        })
    finally:
        conn.close()
