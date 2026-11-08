"""The explanation library's review page (design 2, §7–8), for Town staff only.

Every entry is shown as a resident would read it, with the Code it cites. Decisions stay pending
until they are written into the library's files; a pull hides the entry at once.
"""

import dataclasses

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import Connection

from portal_api import auth
from portal_api.db import transaction
from portal_api.guide.content import load_content
from portal_api.library import load_library, records
from portal_api.library.load import check_edit
from portal_api.library.render import render
from portal_api.ruleset import RulesetError, load_ruleset

router = APIRouter()


def _json(status: int, detail) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": detail})


def _entry_json(e) -> dict:
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in dataclasses.asdict(e).items()}


def _code(ref: str) -> str:
    try:
        return load_ruleset().cite(ref)
    except RulesetError:
        return ""


@router.get("/api/library/batches")
def batches(staff: auth.Applicant = auth.require_staff, conn: Connection = transaction):
    lib = load_library()
    waiting = {d["entry_id"] for d in records.pending(conn)}
    pulled = records.pulled(conn)
    out = []
    for batch in sorted(lib.open_questions):
        es = [e for e in lib.entries.values() if e.batch == batch]
        count = lambda s: sum(1 for e in es if e.status == s and e.id not in pulled)  # noqa: E731
        out.append({"batch": batch, "total": len(es), "draft": count("draft"), "approved": count("approved"),
                    "ratified": count("ratified"), "pulled": sum(1 for e in es if e.status == "pulled" or e.id in pulled),
                    "pending": sum(1 for e in es if e.id in waiting), "open_questions": len(lib.open_questions[batch])})
    return out


@router.get("/api/library/batches/{batch}")
def batch(batch: str, staff: auth.Applicant = auth.require_staff, conn: Connection = transaction):
    lib = load_library()
    if batch not in lib.open_questions:
        return _json(404, "not_found")
    waiting = {d["entry_id"]: d for d in records.pending(conn)}
    pulls = {p["entry_id"]: p for p in records.pulls(conn)}
    entries = [{"entry": _entry_json(e), "flags": list(lib.flags.get(e.id, ())),
                "code": [{"cite": c, "text": _code(c)} for c in e.cites],
                "pending": waiting.get(e.id), "pulled": pulls.get(e.id)}
               for e in lib.entries.values() if e.batch == batch]
    districts = [{"key": d["district_key"], "code": d["code"], "name": d["display_name"],
                  "buildings": list((d.get("building_matrix") or {}).get("cols") or [])}
                 for d in load_ruleset().districts]
    return {"batch": batch, "open_questions": list(lib.open_questions[batch]), "entries": entries,
            "districts": districts}


@router.get("/api/library/entries/{entry_id}/preview")
def preview(entry_id: str, district: str, building: str | None = None,
            staff: auth.Applicant = auth.require_staff):
    e = load_library().entries.get(entry_id)
    if e is None:
        return _json(404, "not_found")
    r = render(e, district, building)
    if r is None:
        return _json(404, "not_for_this_district")
    wording = load_content().wording
    return {"id": e.id, "overline": e.overline, "answer": r.answer, "detail": r.detail, "why": e.why,
            "cites": list(e.cites), "version": e.version, "governs": wording["governs"]["text"], "picture": e.picture,
            "picture_alt": e.picture_alt, "interpretations": list(r.interpretations),
            "mark": wording["interpretation_mark"]["text"] if r.interpretations else None}


class DecisionBody(BaseModel):
    version: int
    action: str
    body: dict | None = None
    note: str | None = None


_TEXTS = frozenset({"overline", "answer", "detail", "why"})


@router.post("/api/library/entries/{entry_id}/decision", status_code=201)
def decision(entry_id: str, b: DecisionBody, staff: auth.Applicant = auth.require_staff,
             conn: Connection = transaction):
    e = load_library().entries.get(entry_id)
    if e is None:
        return _json(404, "not_found")
    if b.action not in records.ACTIONS:
        return _json(422, "bad_action")
    if b.version != e.version:
        return _json(409, "stale")
    if b.action == "send_back" and not (b.note or "").strip():
        return _json(422, "needs_note")
    if b.action == "edit" and (not b.body or set(b.body) != _TEXTS or not all(str(v).strip() for v in b.body.values())):
        return _json(422, "needs_body")
    if b.action == "edit" and (why := check_edit(e, b.body)):
        return _json(422, why)
    body = b.body if b.action == "edit" else None
    if b.action == "approve":
        # Approve right after an edit approves the edited text (design 2, §5), never the text before it.
        last = next((d for d in records.pending(conn) if d["entry_id"] == entry_id), None)
        body = last["body"] if last and last["action"] in ("edit", "approve") and last["version"] == b.version else None
    did = records.decide(conn, entry_id, b.version, b.action, staff.id, body, (b.note or "").strip() or None)
    return {"id": did}


class PullBody(BaseModel):
    version: int
    why: str


@router.post("/api/library/entries/{entry_id}/pull", status_code=201)
def pull(entry_id: str, b: PullBody, staff: auth.Applicant = auth.require_staff, conn: Connection = transaction):
    e = load_library().entries.get(entry_id)
    if e is None:
        return _json(404, "not_found")
    if b.version != e.version:
        return _json(409, "stale")
    if not b.why.strip():
        return _json(422, "needs_why")
    records.pull(conn, entry_id, b.version, b.why.strip(), staff.id)
    return {"entry_id": entry_id}
