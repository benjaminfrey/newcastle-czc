"""Applicants' projects (projects brief §5.4).

Someone else's project, part or note answers 404, exactly like one that does not exist.
Every write carries base_revision (409 `changed_elsewhere` on a stale one) and is refused
once staff have locked the project (409 `locked`). Events name the project, fields and
parts, never the values: the answer table holds those, and the hash chain is permanent.
"""

from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field as PField
from sqlalchemy import Connection, text

from portal_api import auth
from portal_api import projects as pj
from portal_api import property as prop
from portal_api.db import transaction
from portal_api.events import append_event
from portal_api.forms.answers import AnswerError, Current, check_value, missing
from portal_api.forms.definitions import load_definitions
from portal_api.forms.fees import load_fees
from portal_api.forms.formdefs import FormDef, form_drafts, load_form
from portal_api.forms.needs import drafts as needs_drafts, needs
from portal_api.forms.parts import derived, load_parts, project_form, wanted_forms
from portal_api.routes.forms import LookupProperty, _snapshot, form_json
from portal_api.ruleset import load_ruleset

router = APIRouter()
NOTE_MAX = 10_000
FORM_DEFAULT = "form-default"
TOWN_TZ = ZoneInfo("America/New_York")  # a clock's day is the Town's day


def _json(status: int, detail) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


_NOT_FOUND = lambda: _json(404, "not_found")  # noqa: E731
_LOCKED = lambda: _json(409, "locked")  # noqa: E731


def _actor(applicant: auth.Applicant) -> str:
    return f"applicant:{applicant.id}"


def _drafts(pinned: dict[str, int], ruleset) -> list:
    parts = load_parts()
    out = [p.id for p in parts.parts if p.status == "draft"] + (["project"] if parts.project_status == "draft" else [])
    return out + [d for k, v in pinned.items() for d in form_drafts(load_form(k, v, ruleset))]


def _refused(pinned: dict[str, int], request: Request) -> bool:
    return bool(_drafts(pinned, load_ruleset())) and not request.app.state.settings.allow_draft_rules


class Loaded:
    """A project as the rules see it: its parts, pinned forms, merged form and current state."""

    def __init__(self, conn: Connection, row: pj.ProjectRow):
        self.row = row
        self.ruleset = load_ruleset(row.ruleset_key)
        self.parts = pj.parts(conn, row.id)
        self.pinned = pj.forms(conn, row.id)
        self.form: FormDef = project_form(self.pinned, [p["kind"] for p in self.parts], self.ruleset)
        # Answers to questions no part asks any more (a part removed) stay in the history but
        # leave the project: not shown, not counted, not printed (Review Focus 2).
        asked = {f.id for _, f in self.form.fields()}
        stored = {k: v for k, v in pj.answers(conn, row.id).items() if k[0] in asked}
        self.derived = derived(self.parts, stored)
        self.snapshot = pj.snapshot(conn, row.id)
        self.cur = Current(answers={**stored, **self.derived},
                           items=[(p["id"], p["kind"], p["position"]) for p in self.parts],
                           property=self.snapshot["facts"], account=pj.account(conn, row.id))

    def missing(self) -> list[dict]:
        return [{"field_id": f, "part_id": i} for f, i in missing(self.form, self.cur)]

    def needs(self, conn: Connection, allow_drafts: bool, locked_at=None) -> dict:
        """The reviews, fees and clocks (brief §6–§8); withheld while anything they rest on is a draft."""
        defs, fees = load_definitions(self.ruleset), load_fees()
        if needs_drafts(defs, fees) and not allow_drafts:
            return {"refused": "not_approved"}
        if locked_at is None:
            locked_at = conn.execute(text("SELECT locked_at FROM project WHERE id = :p"), {"p": self.row.id}).scalar()
        return needs(self.parts, self.cur.answers, self.snapshot["facts"], self.ruleset, defs, fees, load_parts(),
                     locked_on=locked_at.astimezone(TOWN_TZ).date() if locked_at else None)


def _seed_defaults(conn: Connection, loaded: Loaded) -> None:
    """A question's default is written as an answer, marked as the form's, the first time the
    question applies to the project (or to the part), so the applicant sees it set and the record
    shows nobody typed it."""
    ever = {(r.field_id, str(r.part_id) if r.part_id else None) for r in conn.execute(text(
        "SELECT DISTINCT field_id, part_id FROM answer WHERE project_id = :p"), {"p": loaded.row.id})}
    live = {}
    for p in loaded.parts:
        live.setdefault(p["kind"], []).append(p["id"])
    changes = []
    for s, f in loaded.form.fields():
        if f.default is None:
            continue
        for part_id in (live.get(s.repeat.kind, []) if s.repeat else [None]):
            if (f.id, part_id) not in ever:
                changes.append((f.id, part_id, f.default))
    pj.save_answers(conn, loaded.row.id, changes, FORM_DEFAULT)


def _repin(conn: Connection, project_id: str) -> None:
    pj.pin_forms(conn, project_id, wanted_forms([p["kind"] for p in pj.parts(conn, project_id)], load_parts()))


def _title(kinds: list[str], facts: dict) -> str:
    labels = []
    for k in kinds:
        label = load_parts().get(k).label
        if label not in labels:
            labels.append(label)
    words = [labels[0]] + [x[0].lower() + x[1:] for x in labels[1:]]
    joined = words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]
    where = facts.get("location")
    return f"{joined} at {where.title()}" if where else joined


class NewProject(BaseModel):
    property: LookupProperty
    disputed: bool = False
    note: str = PField(default="", max_length=2000)
    parts: list[str] = PField(max_length=20)
    title: str | None = PField(default=None, max_length=200)


@router.post("/api/projects", status_code=201)
def create_project(body: NewProject, request: Request, applicant: auth.Applicant = auth.require,
                   conn: Connection = transaction):
    known = set(load_parts().ids)
    if not body.parts:
        return _json(422, "no_parts")
    if any(k not in known for k in body.parts):
        return _json(422, "unknown_part")
    singles = [k for k in body.parts if not load_parts().get(k).repeats]
    if len(singles) != len(set(singles)):
        return _json(422, "already_there")
    ruleset = load_ruleset()
    wanted = wanted_forms(body.parts, load_parts())
    if _refused(wanted, request):
        return _json(503, "form_not_approved")
    snap = _snapshot(conn, request, body)
    if isinstance(snap, JSONResponse):
        return snap
    title = (body.title or "").strip() or _title(body.parts, snap["facts"])
    project_id = pj.create(conn, applicant_id=applicant.id, ruleset_key=ruleset.key, title=title, snapshot=snap)
    for k in body.parts:
        pj.add_part(conn, project_id, k)
    pj.pin_forms(conn, project_id, wanted)
    _seed_defaults(conn, Loaded(conn, pj.owned(conn, project_id, applicant.id)))
    append_event(conn, actor=_actor(applicant), kind="project.created",
                 payload={"project_id": project_id, "parts": body.parts, "forms": wanted,
                          "property_source": snap["source"]})
    return {"id": project_id}


@router.get("/api/projects")
def list_projects(applicant: auth.Applicant = auth.require, conn: Connection = transaction):
    out = []
    for r in pj.mine(conn, applicant.id):
        loaded = Loaded(conn, pj.owned(conn, str(r.id), applicant.id))
        out.append({"id": str(r.id), "title": r.title, "status": r.status, "map_lot": r.map_lot,
                    "updated_at": r.updated_at.isoformat(),
                    "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                    "first_part": loaded.parts[0]["kind"] if loaded.parts else None,
                    "left": len(loaded.missing())})
    return out


def state(conn: Connection, loaded: Loaded, allow_drafts: bool, locked_at=None) -> dict:
    row = loaded.row
    status, revision = pj.state(conn, row.id)
    submitted_at = conn.execute(text("SELECT submitted_at FROM project WHERE id = :p"), {"p": row.id}).scalar()
    return {
        "id": row.id, "title": conn.execute(text("SELECT title FROM project WHERE id = :p"), {"p": row.id}).scalar(),
        "status": status, "revision": revision, "ruleset_key": row.ruleset_key,
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "property": loaded.snapshot, "parts": loaded.parts, "forms": loaded.pinned,
        "answers": [{"field_id": f, "part_id": i, "value": v, "derived": (f, i) in loaded.derived}
                    for (f, i), v in loaded.cur.answers.items()],
        "notes": pj.notes(conn, row.id), "attachments": pj.attachments(conn, row.id),
        "missing": loaded.missing(),
        "form": form_json(loaded.form, loaded.ruleset),
        "needs": loaded.needs(conn, allow_drafts, locked_at),
    }


def _owned(conn: Connection, project_id: str, applicant: auth.Applicant) -> pj.ProjectRow | None:
    return pj.owned(conn, project_id, applicant.id)


@router.get("/api/projects/{project_id}")
def get_project(project_id: str, request: Request, applicant: auth.Applicant = auth.require,
                conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    return state(conn, Loaded(conn, row), request.app.state.settings.allow_draft_rules) if row else _NOT_FOUND()


def _refuse_stale(conn: Connection, project_id: str) -> JSONResponse:
    status, revision = pj.state(conn, project_id)
    if status not in pj.EDITABLE:
        return _LOCKED()
    return JSONResponse({"detail": "changed_elsewhere", "revision": revision}, status_code=409)


def _parcel_bounds(conn: Connection) -> tuple | None:
    imp = prop.active_import(conn, "parcels")
    if imp is None:
        return None
    r = conn.execute(text(
        "SELECT ST_XMin(e) AS x0, ST_YMin(e) AS y0, ST_XMax(e) AS x1, ST_YMax(e) AS y1"
        " FROM (SELECT ST_Extent(ST_Transform(geom, 4326)) AS e FROM parcel WHERE import_id = :i) t"
    ), {"i": imp.id}).one()
    return None if r.x0 is None else (r.x0, r.y0, r.x1, r.y1)


class Change(BaseModel):
    field_id: str = PField(max_length=100)
    part_id: str | None = None
    value: Any = None


class AnswersBody(BaseModel):
    base_revision: int
    changes: list[Change] = PField(max_length=200)


@router.put("/api/projects/{project_id}/answers")
def save_answers(project_id: str, body: AnswersBody, applicant: auth.Applicant = auth.require,
                 conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    if row.status not in pj.EDITABLE:
        return _LOCKED()
    loaded = Loaded(conn, row)
    live = {p["id"]: p["kind"] for p in loaded.parts}
    bounds = _parcel_bounds(conn)
    checked, errors = [], []
    for c in body.changes:
        try:
            section, f = loaded.form.field(c.field_id)
        except KeyError:
            errors.append({"field_id": c.field_id, "part_id": c.part_id, "reason": "not_a_question"})
            continue
        part_ok = (c.part_id is None) if section.repeat is None else (live.get(c.part_id) == section.repeat.kind)
        if not part_ok:
            errors.append({"field_id": c.field_id, "part_id": c.part_id, "reason": "wrong_part"})
            continue
        try:
            checked.append((c.field_id, c.part_id, check_value(f, c.value, bounds=bounds)))
        except AnswerError as e:
            errors.append({"field_id": c.field_id, "part_id": c.part_id, "reason": e.reason})
    if errors:
        return _json(422, errors)
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    pj.save_answers(conn, row.id, checked, _actor(applicant))
    append_event(conn, actor=_actor(applicant), kind="project.answers_saved",
                 payload={"project_id": row.id, "fields": [[f, i] for f, i, _ in checked]})
    return {"revision": rev, "missing": Loaded(conn, row).missing()}


class PartBody(BaseModel):
    kind: str = PField(max_length=40)
    base_revision: int
    copy_from: str | None = PField(default=None, max_length=40)  # "Copy Building 1": the part to copy


class RevisionBody(BaseModel):
    base_revision: int


def _repeat(form: FormDef, kind: str):
    return next((s.repeat for s in form.sections if s.repeat and s.repeat.kind == kind), None)


@router.post("/api/projects/{project_id}/parts", status_code=201)
def add_part(project_id: str, body: PartBody, request: Request, applicant: auth.Applicant = auth.require,
             conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    if row.status not in pj.EDITABLE:
        return _LOCKED()
    part = load_parts().get(body.kind)
    if part is None:
        return _json(422, "unknown_part")
    live = pj.parts(conn, row.id)
    same = [p for p in live if p["kind"] == body.kind]
    if same and not part.repeats:
        return _json(422, "already_there")
    source = None
    if body.copy_from is not None:
        # Checked before anything is written: a live part of this project, of the same kind.
        source = next((p for p in live if p["id"] == pj.parse_id(body.copy_from)), None)
        if source is None:
            return _NOT_FOUND()
        if source["kind"] != body.kind:
            return _json(422, "wrong_kind")
    wanted = wanted_forms([p["kind"] for p in live] + [body.kind], load_parts())
    if _refused(wanted, request):
        return _json(503, "form_not_approved")
    if part.repeats:
        repeat = _repeat(project_form(wanted, [body.kind], load_ruleset(row.ruleset_key)), body.kind)
        if repeat is not None and len(same) >= repeat.max:
            return _json(422, "too_many")
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    part_id = pj.add_part(conn, row.id, body.kind)
    _repin(conn, row.id)
    loaded = Loaded(conn, row)
    _seed_defaults(conn, loaded)
    if source is not None:
        fields = [f.id for s, f in loaded.form.fields() if f.copies and s.repeat and s.repeat.kind == body.kind]
        pj.copy_part_answers(conn, row.id, fields, source["id"], part_id)
    append_event(conn, actor=_actor(applicant), kind="project.part_added",
                 payload={"project_id": row.id, "part_id": part_id, "kind": body.kind,
                          **({"copied_from": source["id"]} if source else {})})
    return {"id": part_id, "revision": rev}


@router.delete("/api/projects/{project_id}/parts/{part_id}")
def remove_part(project_id: str, part_id: str, body: RevisionBody, applicant: auth.Applicant = auth.require,
                conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    if row.status not in pj.EDITABLE:
        return _LOCKED()
    live = pj.parts(conn, row.id)
    if pj.parse_id(part_id) not in {p["id"] for p in live}:
        return _NOT_FOUND()
    if len(live) <= 1:
        return _json(422, "at_least_one")
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    pj.remove_part(conn, row.id, part_id)
    _repin(conn, row.id)
    append_event(conn, actor=_actor(applicant), kind="project.part_removed",
                 payload={"project_id": row.id, "part_id": part_id})
    return {"revision": rev}


class NoteBody(BaseModel):
    base_revision: int
    section_id: str = PField(max_length=100)
    part_id: str | None = None
    text: str = PField(max_length=NOTE_MAX)


@router.put("/api/projects/{project_id}/notes")
def save_note(project_id: str, body: NoteBody, applicant: auth.Applicant = auth.require,
              conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    if row.status not in pj.EDITABLE:
        return _LOCKED()
    loaded = Loaded(conn, row)
    section = next((s for s in loaded.form.sections if s.id == body.section_id), None)
    if section is None:
        return _json(422, "unknown_section")
    live = {p["id"]: p["kind"] for p in loaded.parts}
    if (body.part_id is None) != (section.repeat is None) or (
            section.repeat and live.get(body.part_id) != section.repeat.kind):
        return _json(422, "wrong_part")
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    pj.save_note(conn, row.id, section.id, body.part_id, body.text.strip(), _actor(applicant))
    append_event(conn, actor=_actor(applicant), kind="project.note_saved",
                 payload={"project_id": row.id, "section_id": section.id, "part_id": body.part_id})
    return {"revision": rev}


class TitleBody(BaseModel):
    base_revision: int
    title: str = PField(min_length=1, max_length=200)


@router.put("/api/projects/{project_id}/title")
def set_title(project_id: str, body: TitleBody, applicant: auth.Applicant = auth.require,
              conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    if row.status not in pj.EDITABLE:
        return _LOCKED()
    title = body.title.strip()
    if not title:
        return _json(422, "title_required")
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    pj.set_title(conn, row.id, title)
    append_event(conn, actor=_actor(applicant), kind="project.renamed", payload={"project_id": row.id})
    return {"revision": rev}


@router.post("/api/projects/{project_id}/submit")
def submit(project_id: str, body: RevisionBody, applicant: auth.Applicant = auth.require,
           conn: Connection = transaction):
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    if row.status not in pj.EDITABLE:
        return _LOCKED()
    left = Loaded(conn, row).missing()
    if left:
        return JSONResponse({"detail": "incomplete", "missing": left}, status_code=422)
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    first = row.status == "draft"
    pj.submit(conn, row.id)
    append_event(conn, actor=_actor(applicant), kind="project.submitted",
                 payload={"project_id": row.id, "first": first})
    return {"revision": rev, "status": "submitted"}


def lock_snapshot(conn: Connection, loaded: Loaded, allow_drafts: bool, locked_at) -> dict:
    """What a submission freezes (brief §5.1): exactly the project as it stands at the lock,
    with its reviews, fees and clocks (started at the lock)."""
    s = state(conn, loaded, allow_drafts, locked_at)
    return {k: s[k] for k in ("title", "ruleset_key", "property", "parts", "forms", "answers", "notes", "needs")} | {
        "attachments": [dict(a, sha256=conn.execute(text("SELECT sha256 FROM attachment WHERE id = :i"),
                                                     {"i": a["id"]}).scalar()) for a in s["attachments"]]}


@router.post("/api/projects/{project_id}/lock")
def lock(project_id: str, body: RevisionBody, request: Request, applicant: auth.Applicant = auth.require,
         conn: Connection = transaction):
    """A test seam for the staff lock (Milestone 6 builds the staff side): off unless the
    deployment allows it."""
    if not request.app.state.settings.allow_test_lock:
        return _NOT_FOUND()
    row = _owned(conn, project_id, applicant)
    if row is None:
        return _NOT_FOUND()
    loaded = Loaded(conn, row)
    at = conn.execute(text("SELECT now()")).scalar()  # the transaction's time: the lock's locked_at
    snapshot = lock_snapshot(conn, loaded, request.app.state.settings.allow_draft_rules, at)
    seq = pj.lock(conn, row.id, body.base_revision, None, snapshot)
    if seq is None:
        status, revision = pj.state(conn, row.id)
        return JSONResponse({"detail": "not_sent" if status == "draft" else "changed_elsewhere",
                             "revision": revision}, status_code=409)
    pj.record_reviews(conn, row.id, seq, [
        {"review_key": r["review_key"], "use_key": r["use_key"], "permit_key": p["key"],
         "reviewer": r["reviewer"]}
        for p in snapshot["needs"].get("permits", []) for r in p["reviews"]])
    append_event(conn, actor=_actor(applicant), kind="project.locked", payload={"project_id": row.id, "seq": seq})
    return {"seq": seq, "revision": pj.state(conn, row.id)[1]}
