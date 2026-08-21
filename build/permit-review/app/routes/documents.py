"""app/routes/documents.py — document upload for a case (W3 ingest task).

Implements CONTRACT.md §2's `ingest/` scope ("upload, PDF page split") for
the HTTP layer: a case's documents are uploaded here, streamed and content-
addressed by app/blobs.py, then censused and tiered by ingest/triage.py.
Envelope shape matches CONTRACT.md §6's preamble
(`{"ok": true, "data": {...}}` / `{"ok": false, "error": ..., "message": ...}`).

Scope, restated from the task brief that commissioned this file: uploads,
content-addressed blobs, page census and tiering. NO extraction of field
values, NO OCR, NO vision, NO LLM call happens anywhere in this file --
later workflows own those.

`router` is a complete, self-contained FastAPI APIRouter -- app/main.py's
create_app() mounts it defensively (`_try_import("app.routes.documents")`
then `app.include_router(documents_routes_mod.router)`), the same pattern
every other sibling module in that file uses, so this file is never
imported at all if it or its own imports fail. See tests/test_documents.py
for both a standalone-router mount and route-level coverage against the
real fixture PDFs; verified separately, by hand, through the actual
app/main.py:create_app() (Host/Origin guard included) end-to-end.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date as date_cls, datetime, timezone
from typing import Any

from fastapi import APIRouter, Form, UploadFile
from fastapi.responses import JSONResponse

from app import audit, blobs, config, db, security
from ingest import triage

router = APIRouter()

# F13c -- a document's title (whether typed in explicitly or derived from
# the uploaded filename) is display data, not a legal value; it is bounded
# here rather than rejected outright, so a pathologically long filename
# (the adversarial review's example: 5000 characters) never turns into an
# equally pathological documents.title row -- while a real, if verbose,
# filename still uploads successfully.
_MAX_TITLE_LEN = 300

# ---------------------------------------------------------------------------
# doc_role -> (documents.kind, default source_priority)
#
# app/migrations/0001_init.sql's `documents` table (CONTRACT.md §3.6) ships
# `kind` fixed to a 9-value enum with a DB trigger pinning source_priority
# for kind IN (plan, survey, deed, form) to EXACTLY 100/90/80/40 -- "the
# form is wrong, the plan governs." The task brief that commissioned this
# route named a richer, 10-value `doc_role` vocabulary (application_form,
# plan_sheet, engineer_letter, applicant_narrative, staff_review,
# abutter_comment, state_permit, ...) that doesn't exist in that DDL.
# Following this app's own precedent for a brief/CONTRACT mismatch (see
# app/config.py's port-8790-vs-8781 note), CONTRACT.md's kind/source_priority
# invariant is left exactly as specified; `doc_role` is layered on top as an
# additive column (0004_page_triage.sql) and mapped onto (kind,
# source_priority) here. The four core roles are pinned to the DB trigger's
# exact values; the rest get a sensible default priority of their own.
# ---------------------------------------------------------------------------
DOC_ROLE_TO_KIND: dict[str, tuple[str, int]] = {
    "application_form": ("form", 40),  # trigger-pinned
    "plan_sheet": ("plan", 100),  # trigger-pinned
    "survey": ("survey", 90),  # trigger-pinned
    "deed": ("deed", 80),  # trigger-pinned
    "engineer_letter": ("correspondence", 70),
    "applicant_narrative": ("narrative", 60),
    "staff_review": ("other", 65),
    "abutter_comment": ("correspondence", 30),
    "state_permit": ("other", 85),
    "other": ("other", 10),
}

# When a document contains at least one tier-D (plansheet) page, the task
# brief requires forcing source_priority to 100 -- "the plan governs" applies
# even when the submitter mis-labeled a plan set as e.g. an application form.
# kind is bumped to 'plan' alongside it so the (kind, source_priority) pair
# stays trigger-consistent for any FUTURE row-level revalidation; doc_role is
# left untouched, preserving what the submitter actually called it.
_PLANSHEET_FORCED_KIND = "plan"
_PLANSHEET_FORCED_PRIORITY = 100


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _err(code: str, message: str, status: int, **extra: Any) -> JSONResponse:
    body: dict[str, Any] = {"ok": False, "error": code, "message": message}
    body.update(extra)
    return JSONResponse(status_code=status, content=body)


def _ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def _connect() -> sqlite3.Connection:
    # Resolved from config.DATA_DIR at CALL time, not a `from app.config
    # import DB_PATH` name-bound copy -- see app/blobs.py's matching note.
    # Lets a test monkeypatch app.config.DATA_DIR to a throwaway tmp_path
    # and get a fully isolated database, matching this repo's established
    # "throwaway temp-dir SQLite file per test" convention.
    db_path = config.DATA_DIR / "permit-review.db"
    conn = db.connect(db_path)
    db.migrate(conn, config.MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    return conn


def _bounded_title(raw: str) -> str:
    """F13c: clamps a title (explicit or filename-derived) to
    _MAX_TITLE_LEN, trimmed at a whole character with a trailing marker so
    it's visibly truncated rather than silently cut. Never raises -- a long
    title is a data-hygiene issue, not a reason to reject an otherwise valid
    upload.
    """
    raw = raw.strip()
    if len(raw) <= _MAX_TITLE_LEN:
        return raw
    return raw[:_MAX_TITLE_LEN].rstrip() + "…"


def _doc_date_error(raw: str) -> str | None:
    """F13c: validates an optional `doc_date` Form field as a real ISO
    calendar date before it reaches `documents.doc_date` (previously
    unvalidated -- `doc_date="not-a-date"` stored verbatim). Mirrors
    app/cases.py's own `_occurred_on_error` (first 10 characters must parse
    as YYYY-MM-DD; a trailing time-of-day is tolerated). Returns None when
    valid.
    """
    try:
        date_cls.fromisoformat(raw[:10])
    except ValueError:
        return (
            f"{raw!r} is not a valid ISO date -- must be a real calendar date in "
            f"YYYY-MM-DD form"
        )
    return None


def _page_public_row(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    for boolish in ("has_label_tokens", "is_plansheet"):
        if d.get(boolish) is not None:
            d[boolish] = bool(d[boolish])
    return d


@router.post("/api/cases/{case_id}/documents")
async def upload_document(
    case_id: str,
    file: UploadFile,
    doc_role: str = Form(...),
    title: str | None = Form(None),
    sheet_label: str | None = Form(None),
    doc_date: str | None = Form(None),
):
    """Upload one document into a case: stream + content-address the bytes,
    then census/tier every page. CONTRACT.md §1.1 S1 (validate-all-then-
    write): the file is streamed to a temp location and triaged BEFORE
    anything is written to data/blobs/ or any row is inserted, so a
    validation failure discovered THERE (bad doc_role, unsupported media
    type, oversized upload, an unopenable PDF) leaves the database and
    data/blobs/ exactly as they were.

    F13a -- the one remaining gap that note used to overstate: once triage
    passes, blobs.commit_blob() moves the file into its permanent,
    content-addressed location as the FIRST step inside this route's own
    transaction, and a filesystem rename is not something a later SQL
    ROLLBACK can undo. If a subsequent statement in this same transaction
    (the `documents`/`pages` INSERTs, the audit event) fails, this route
    now explicitly deletes that just-committed file (blobs.
    discard_committed_file) alongside the ROLLBACK, so data/blobs/ is
    restored to its pre-request state either way -- not just for the
    triage-time failures the original wording described.
    """
    if doc_role not in DOC_ROLE_TO_KIND:
        return _err(
            "validation_failed",
            f"unknown doc_role {doc_role!r}",
            400,
            details=[{"field": "doc_role", "message": f"must be one of {sorted(DOC_ROLE_TO_KIND)}"}],
        )
    kind, default_priority = DOC_ROLE_TO_KIND[doc_role]

    # F13c -- validate-all-then-write for doc_date before any I/O: a bad
    # value used to be stored verbatim (`doc_date="not-a-date"`).
    if doc_date is not None and doc_date.strip():
        date_error = _doc_date_error(doc_date.strip())
        if date_error is not None:
            return _err(
                "validation_failed",
                "the request failed validation",
                400,
                details=[{"field": "doc_date", "message": date_error}],
            )

    conn = _connect()
    try:
        case_row = conn.execute("SELECT id FROM cases WHERE id = ?;", (case_id,)).fetchone()
        if case_row is None:
            return _err("unknown_case", f"case {case_id!r} not found", 404)

        # --- Stream + content-address (app/blobs.py). Nothing durable yet:
        # the temp file lives under data/tmp/ until commit_blob() below. ---
        try:
            streamed = await blobs.consume_upload_file(file)
        except blobs.UnsupportedMediaType as exc:
            return _err("unsupported_media_type", str(exc), 415)
        except blobs.UploadTooLarge as exc:
            return _err("payload_too_large", str(exc), 413)
        except blobs.UnsafeFilename as exc:
            return _err("invalid_filename", str(exc), 400)

        # --- Triage the TEMP file before committing anything (S1). A
        # corrupt/unopenable PDF writes nothing at all. ---
        try:
            pages = triage.triage_pdf(streamed.tmp_path)
        except triage.UnreadablePdf as exc:
            blobs.discard(streamed)
            # F13b: ingest.triage.UnreadablePdf's own message embeds the
            # ABSOLUTE server-side temp path (it exists to be useful in a
            # server log, not a client-facing error body) -- str(exc) used
            # to go straight into the HTTP response, leaking this app's
            # filesystem layout. Log the full detail server-side; the client
            # gets a clean message plus whatever original filename it
            # already knows (sanitize_original_name already stripped any
            # path component from it, so this cannot itself leak a path).
            print(f"[permit-review] WARNING: rejected unreadable PDF upload: {exc}")
            name_suffix = f" ({streamed.original_name})" if streamed.original_name else ""
            return _err(
                "unreadable_pdf",
                f"the uploaded file could not be opened as a PDF{name_suffix}",
                422,
            )

        plansheet_forced = triage.any_plansheet(pages)
        final_kind = _PLANSHEET_FORCED_KIND if plansheet_forced else kind
        final_priority = _PLANSHEET_FORCED_PRIORITY if plansheet_forced else default_priority

        actor_user_id = security.current_user().id
        now = _utc_now_iso()
        doc_id = uuid.uuid4().hex

        final_title = _bounded_title(title) if title else (
            _bounded_title(streamed.original_name) if streamed.original_name else "(untitled)"
        )

        conn.execute("BEGIN;")
        # F13a: set the moment blobs.commit_blob() reports a NEWLY-created
        # blob (i.e. the moment it did an os.replace() this transaction
        # cannot ask SQLite to undo) -- see the except block below, and
        # blobs.discard_committed_file()'s own docstring for why this is
        # safe (single-writer SQLite, same still-open transaction).
        committed_new_blob_sha: str | None = None
        try:
            blob_row, blob_is_new = blobs.commit_blob(conn, streamed, actor_user_id=actor_user_id)
            if blob_is_new:
                committed_new_blob_sha = blob_row["sha256"]

            conn.execute(
                """
                INSERT INTO documents
                    (id, case_id, blob_id, kind, source_priority, title, sheet_label,
                     doc_date, page_count, received_at, created_at, actor_user_id, doc_role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    doc_id, case_id, blob_row["id"], final_kind, final_priority,
                    final_title, sheet_label, doc_date,
                    len(pages), now, now, actor_user_id, doc_role,
                ),
            )

            for p in pages:
                page_id = uuid.uuid4().hex
                r = p.as_row()
                conn.execute(
                    """
                    INSERT INTO pages
                        (id, document_id, page_number, width_pt, height_pt, text, text_source,
                         ocr_confidence, thumb_blob_id, created_at, actor_user_id,
                         char_count, image_count, rotation, vector_path_count,
                         page_sha256, tier, has_label_tokens, is_plansheet)
                    VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        page_id, doc_id, r["page_number"], r["width_pt"], r["height_pt"],
                        now, actor_user_id, r["char_count"], r["image_count"], r["rotation"],
                        r["vector_path_count"], r["page_sha256"], r["tier"],
                        r["has_label_tokens"], r["is_plansheet"],
                    ),
                )

            census = triage.tier_census(pages)
            audit.append_event(
                conn,
                actor_user_id=actor_user_id,
                kind="document.uploaded",
                case_id=case_id,
                entity_table="documents",
                entity_id=doc_id,
                payload={
                    "case_id": case_id,
                    "document_id": doc_id,
                    "blob_id": blob_row["id"],
                    "blob_sha256": blob_row["sha256"],
                    "blob_is_new": blob_is_new,
                    "doc_role": doc_role,
                    "kind": final_kind,
                    "source_priority": final_priority,
                    "plansheet_forced": plansheet_forced,
                    "page_count": len(pages),
                    "tier_census": census,
                },
            )
            conn.execute("COMMIT;")
        except Exception:
            conn.execute("ROLLBACK;")
            if committed_new_blob_sha is not None:
                # F13a: the blobs row this transaction inserted for a
                # brand-new blob is gone after ROLLBACK, but the file
                # blobs.commit_blob() already moved into place is not --
                # remove it so data/blobs/ returns to its pre-request state,
                # matching this route's own docstring guarantee.
                blobs.discard_committed_file(committed_new_blob_sha)
            raise

        doc_row = dict(conn.execute("SELECT * FROM documents WHERE id = ?;", (doc_id,)).fetchone())
        page_rows = [
            _page_public_row(r)
            for r in conn.execute(
                "SELECT * FROM pages WHERE document_id = ? ORDER BY page_number;", (doc_id,)
            ).fetchall()
        ]

        return _ok({
            "document": doc_row,
            "blob": {**blob_row, "is_new": blob_is_new},
            "pages": page_rows,
            "tier_census": triage.tier_census(pages),
        })
    finally:
        conn.close()


@router.get("/api/cases/{case_id}/documents")
def list_documents(case_id: str):
    """List every document on a case, each with its page tier census --
    the raw material a later case dashboard reads (this task does not build
    that dashboard, only the data it needs)."""
    conn = _connect()
    try:
        case_row = conn.execute("SELECT id FROM cases WHERE id = ?;", (case_id,)).fetchone()
        if case_row is None:
            return _err("unknown_case", f"case {case_id!r} not found", 404)

        docs = conn.execute(
            "SELECT * FROM documents WHERE case_id = ? ORDER BY created_at;", (case_id,)
        ).fetchall()
        out = []
        for d in docs:
            pages = conn.execute(
                "SELECT * FROM pages WHERE document_id = ? ORDER BY page_number;", (d["id"],)
            ).fetchall()
            counts = {"A": 0, "B": 0, "C": 0, "D": 0}
            for p in pages:
                if p["tier"] in counts:
                    counts[p["tier"]] += 1
            out.append({
                "document": dict(d),
                "pages": [_page_public_row(p) for p in pages],
                "tier_census": counts,
            })
        return _ok({"case_id": case_id, "documents": out})
    finally:
        conn.close()
