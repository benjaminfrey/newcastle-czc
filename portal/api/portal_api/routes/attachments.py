"""Uploads and downloads of a project's files.

An upload is checked in this order, and nothing is stored unless every check
passes: the project is the caller's (404) and not locked (409), the field is an upload
question of the project's form (422), the caller's hourly allowance (429), the size, read no further than
the limit (413), a virus scan (422 infected; 503 if the scanner can't be reached),
the type by the file's first bytes (415), then the store (503), then the row and the
event. Files go back only to their owner, streamed through the API.
"""

import hashlib
from urllib.parse import quote

from fastapi import APIRouter, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import Connection, text
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException, MultiPartParser

from portal_api import auth
from portal_api import projects as pj
from portal_api.db import transaction
from portal_api.events import append_event
from portal_api.ratelimit import SlidingWindow
from portal_api.routes.projects import Loaded
from portal_api.scan import ScannerUnavailable
from portal_api.storage import StoreUnavailable
from portal_api.uploads import safe_filename, sniff

router = APIRouter()
# Room for the multipart framing and the two small text fields around the file.
_OVERHEAD = 64 * 1024


def _json(status: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


async def bounded_body(request, limit: int) -> bytes | None:
    """The request body, or None as soon as it is known to exceed `limit` bytes."""
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > limit:
        return None
    buf = bytearray()
    async for chunk in request.stream():
        buf += chunk
        if len(buf) > limit:
            return None
    return bytes(buf)


async def _parse(request: Request, body: bytes):
    async def once():
        yield body
    return await MultiPartParser(request.headers, once(), max_files=1, max_fields=4, max_part_size=1024).parse()


def _limiter(request: Request) -> SlidingWindow:
    s = request.app.state
    if not hasattr(s, "upload_limiter"):
        s.upload_limiter = SlidingWindow(s.settings.upload_limit_per_hour, window_seconds=3600)
    return s.upload_limiter


@router.post("/api/projects/{project_id}/attachments", status_code=201)
async def upload(project_id: str, request: Request, applicant: auth.Applicant = auth.require,
                 conn: Connection = transaction):
    settings = request.app.state.settings
    row = await run_in_threadpool(pj.owned, conn, project_id, applicant.id)
    if row is None:
        return _json(404, "not_found")
    if row.status not in pj.EDITABLE:
        return _json(409, "locked")
    body = await bounded_body(request, settings.upload_max_bytes + _OVERHEAD)
    if body is None:
        return _json(413, "too_large")
    try:
        form = await _parse(request, body)
    except MultiPartException:
        return _json(422, "bad_upload")
    file, field_id, part_id = form.get("file"), form.get("field_id"), form.get("part_id") or None
    if not isinstance(file, UploadFile) or not isinstance(field_id, str):
        return _json(422, "bad_upload")
    loaded = await run_in_threadpool(Loaded, conn, row)
    formdef = loaded.form
    try:
        section, field = formdef.field(field_id)
    except KeyError:
        return _json(422, "not_an_upload_field")
    if field.type != "upload" or not field.is_question:
        return _json(422, "not_an_upload_field")
    live = {p["id"]: p["kind"] for p in loaded.parts}
    if (section.repeat is None and part_id is not None) or (
            section.repeat is not None and live.get(part_id) != section.repeat.kind):
        return _json(422, "wrong_part")
    if not _limiter(request).allow(applicant.id):
        return _json(429, "too_many_uploads")
    data = await file.read(settings.upload_max_bytes + 1)
    if len(data) > settings.upload_max_bytes:
        return _json(413, "too_large")
    try:
        result = await run_in_threadpool(request.app.state.scanner.scan, data)
    except ScannerUnavailable:
        return _json(503, "scanner_unavailable")
    if not result.clean:
        return _json(422, "infected")
    content_type = sniff(data[:64])
    if content_type is None:
        return _json(415, "unsupported_type")
    attachment_id = str(await run_in_threadpool(lambda: conn.execute(text("SELECT gen_random_uuid()")).scalar()))
    key = f"projects/{row.id}/{attachment_id}"
    try:
        await run_in_threadpool(request.app.state.store.put, key, data, content_type)
    except StoreUnavailable:
        return _json(503, "store_unavailable")
    digest = hashlib.sha256(data).hexdigest()
    name = safe_filename(file.filename or "")

    def record():
        conn.execute(text(
            "INSERT INTO attachment (id, project_id, field_id, part_id, filename, content_type, size_bytes,"
            " sha256, storage_key) VALUES (:id, :a, :f, :i, :n, :t, :s, :h, :k)"
        ), {"id": attachment_id, "a": row.id, "f": field_id, "i": part_id, "n": name, "t": content_type,
            "s": len(data), "h": digest, "k": key})
        append_event(conn, actor=f"applicant:{applicant.id}", kind="attachment.added",
                     payload={"project_id": row.id, "attachment_id": attachment_id, "field_id": field_id,
                              "part_id": part_id, "sha256": digest, "size_bytes": len(data),
                              "content_type": content_type})

    await run_in_threadpool(record)
    return {"id": attachment_id, "filename": name, "size_bytes": len(data), "content_type": content_type,
            "field_id": field_id, "part_id": part_id}


def _owned_attachment(conn: Connection, attachment_id: str, applicant_id: str):
    if pj.parse_id(attachment_id) is None:
        return None
    return conn.execute(text(
        "SELECT t.id, t.project_id, t.filename, t.content_type, t.storage_key, p.status FROM attachment t"
        " JOIN project p ON p.id = t.project_id"
        " WHERE t.id = :id AND p.applicant_id = :a AND t.removed_at IS NULL"
    ), {"id": attachment_id, "a": applicant_id}).one_or_none()


@router.get("/api/attachments/{attachment_id}")
def download(attachment_id: str, request: Request, applicant: auth.Applicant = auth.require,
             conn: Connection = transaction):
    r = _owned_attachment(conn, attachment_id, applicant.id)
    if r is None:
        return _json(404, "not_found")
    try:
        chunks = request.app.state.store.get(r.storage_key)
    except StoreUnavailable:
        return _json(503, "store_unavailable")
    return StreamingResponse(chunks, media_type=r.content_type, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(r.filename)}",
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
    })


@router.delete("/api/attachments/{attachment_id}", status_code=204)
def remove(attachment_id: str, applicant: auth.Applicant = auth.require, conn: Connection = transaction):
    r = _owned_attachment(conn, attachment_id, applicant.id)
    if r is None:
        return _json(404, "not_found")
    if r.status not in pj.EDITABLE:
        return _json(409, "locked")
    conn.execute(text("UPDATE attachment SET removed_at = now() WHERE id = :id"), {"id": r.id})
    append_event(conn, actor=f"applicant:{applicant.id}", kind="attachment.removed",
                 payload={"project_id": str(r.project_id), "attachment_id": str(r.id)})
    return Response(status_code=204)
