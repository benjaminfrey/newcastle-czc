"""Application forms (public) and applicants' draft applications (signed in).

Someone else's application, item or note answers 404, exactly like one that does not
exist. Events name the application, fields and items, never the values: the answer
table holds those, and the hash chain is permanent.
"""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field as PField
from sqlalchemy import Connection, text

from portal_api import applications as apps
from portal_api import auth
from portal_api import property as prop
from portal_api.db import transaction
from portal_api.events import append_event
from portal_api.forms.answers import AnswerError, check_value, missing
from portal_api.forms.definitions import DefinitionError
from portal_api.forms.formdefs import FORM_KEYS, FormDef, form_drafts, latest_version, load_form
from portal_api.ratelimit import lookup_limit
from portal_api.ruleset import load_ruleset

router = APIRouter()
NOTE_MAX = 10_000


def _json(status: int, detail) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


_NOT_FOUND = lambda: _json(404, "not_found")  # noqa: E731
_NOT_APPROVED = lambda: _json(503, "form_not_approved")  # noqa: E731


def _load(key: str, version: int | None = None, ruleset_key: str | None = None) -> FormDef | None:
    if key not in FORM_KEYS:
        return None
    try:
        return load_form(key, version or latest_version(key), load_ruleset(ruleset_key) if ruleset_key else load_ruleset())
    except DefinitionError:
        return None


def _refused(form: FormDef, request: Request) -> bool:
    return bool(form_drafts(form)) and not request.app.state.settings.allow_draft_rules


def form_json(form: FormDef, ruleset) -> dict:
    def why(ref):
        return {"cite": ref, "text": ruleset.cite(ref)} if ref else None

    return {
        "key": form.key, "version": form.version, "ruleset_key": form.ruleset_key,
        "official_title": form.official_title,
        "steps": [{"id": st.id, "title": st.title} for st in form.steps],
        "sections": [{
            "id": s.id, "official_title": s.official_title, "chapter": s.chapter, "show_if": s.show_if,
            "step": s.step, "screens": [{"id": x.id, "layout": x.layout} for x in s.screens],
            "repeat": None if s.repeat is None else {
                "kind": s.repeat.kind, "add_label": s.repeat.add_label, "min": s.repeat.min, "max": s.repeat.max},
            "fields": [{
                "id": f.id, "official_label": f.official_label, "source": f.source, "from": f.from_,
                "may_correct": f.may_correct, "label": f.label, "help": f.help, "why": why(f.why), "type": f.type,
                "unit": f.unit, "min": f.min, "max": f.max, "required": f.required, "allow_unknown": f.allow_unknown,
                "show_if": f.show_if, "step": f.step or s.step, "screen": f.screen, "ask_first": f.ask_first, "control": f.control,
                "step_size": f.step_size, "default": f.default, "autocomplete": f.autocomplete,
                "options": [{"value": o.value, "label": o.label, "official": o.official, "icon": o.icon} for o in f.options],
                "copies": f.copies,
            } for f in s.fields],
        } for s in form.sections],
    }


@router.get("/api/forms/{key}", dependencies=[Depends(lookup_limit)])
def get_form(key: str, request: Request):
    form = _load(key)
    if form is None:
        return _NOT_FOUND()
    return _NOT_APPROVED() if _refused(form, request) else form_json(form, load_ruleset())


@router.get("/api/forms/{key}/v/{version}", dependencies=[Depends(lookup_limit)])
def get_form_version(key: str, version: int, request: Request):
    form = _load(key, version)
    if form is None:
        return _NOT_FOUND()
    return _NOT_APPROVED() if _refused(form, request) else form_json(form, load_ruleset())


class LookupProperty(BaseModel):
    source: str
    parcel_id: int | None = None
    map_lot: str | None = PField(default=None, max_length=40)
    district_code: str | None = PField(default=None, max_length=40)


class Carry(BaseModel):
    """What the applicant said in "Do I need a permit?", so the application doesn't ask again."""
    work_kind: Literal["new", "addition", "renovation", "site"] | None = None
    floor_area: float | None = None
    new_homes: int | None = None


# The screener's kind of building work, as the Small Project Plan's work_kinds option.
WORK_KINDS = {"new": "new_building", "addition": "addition", "renovation": "renovation", "site": "site"}


def _carried_changes(form: FormDef, carry: "Carry | None", building_one: str | None) -> list[tuple]:
    """(field, item, value) to save as the screener's: the kind of work, and for a new building its
    floor area and homes on Building 1. Fields the form doesn't have are skipped."""
    if carry is None or carry.work_kind is None:
        return []
    have = {f.id for _, f in form.fields()}
    out = []
    if "work_kinds" in have:
        out.append(("work_kinds", None, [WORK_KINDS[carry.work_kind]]))
    if carry.work_kind == "new" and building_one is not None:
        if carry.floor_area is not None and "floor_area" in have:
            out.append(("floor_area", building_one, carry.floor_area))
        if carry.new_homes is not None and "dwelling_units" in have:
            out.append(("dwelling_units", building_one, carry.new_homes))
    return out


class NewApplication(BaseModel):
    form_key: str
    property: LookupProperty
    disputed: bool = False
    note: str = PField(default="", max_length=2000)
    use_key: str | None = None
    carry: Carry | None = None


def _snapshot(conn: Connection, request: Request, body: NewApplication) -> dict | JSONResponse:
    p = body.property
    common = {"disputed": body.disputed, "note": body.note.strip()}
    if p.source == "lookup" and p.parcel_id is not None:
        try:
            imp = prop.parcels_import(conn, request.app.state.settings)
        except prop.ParcelsUnavailable:
            return _json(503, "property_unavailable")
        facts = prop.facts(conn, p.parcel_id, imp)
        if facts is None:
            return _json(422, "no_such_parcel")
        facts.pop("geometry", None)
        if prop.active_import(conn, "streets") is None:
            # No street layer: nobody knows whether the lot is on a State road, so the
            # MaineDOT question must still be asked.
            facts["on_state_highway"] = None
        return {"source": "lookup", "parcel_id": facts["parcel_id"], "map_lot": facts["map_lot"], "facts": facts,
                "as_of": facts["as_of"]["parcels"], "verified": True, **common}
    if p.source == "manual" and p.map_lot and p.map_lot.strip():
        districts = []
        if p.district_code is not None:
            adopted = {d["code"]: d["name"] for d in prop.adopted_districts(conn)}
            if p.district_code not in adopted:
                return _json(422, "unknown_district")
            districts = [{"code": p.district_code, "name": adopted[p.district_code], "in_ruleset": True, "share": 1.0}]
        facts = {"map_lot": p.map_lot.strip(), "location": None, "acres": None, "districts": districts,
                 "streets": [], "on_state_highway": None}
        return {"source": "manual", "parcel_id": None, "map_lot": facts["map_lot"], "facts": facts,
                "as_of": None, "verified": False, **common}
    return _json(422, "property_required")


def _actor(applicant: auth.Applicant) -> str:
    return f"applicant:{applicant.id}"


@router.post("/api/applications", status_code=201)
def create_application(body: NewApplication, request: Request, applicant: auth.Applicant = auth.require,
                       conn: Connection = transaction):
    form = _load(body.form_key)
    if form is None:
        return _NOT_FOUND()
    if _refused(form, request):
        return _NOT_APPROVED()
    ruleset = load_ruleset()
    if body.use_key is not None and body.use_key not in {u["use_key"] for u in ruleset.uses}:
        return _json(422, "unknown_use")
    # Check carried values before anything is written.
    for fid, _, value in _carried_changes(form, body.carry, "check"):
        try:
            check_value(form.field(fid)[1], value)
        except AnswerError:
            return _json(422, "invalid")
    snap = _snapshot(conn, request, body)
    if isinstance(snap, JSONResponse):
        return snap
    app_id = apps.create(conn, applicant_id=applicant.id, form=form, snapshot=snap)
    first = next((i["id"] for i in apps.items(conn, app_id) if i["kind"] == "building"), None)
    carried = [(f, item, check_value(form.field(f)[1], v)) for f, item, v in _carried_changes(form, body.carry, first)]
    apps.save_answers(conn, app_id, carried, apps.SCREENER)
    if body.use_key is not None and any(f.id == "proposed_uses" for _, f in form.fields()):
        apps.save_answers(conn, app_id, [("proposed_uses", None, [body.use_key])], _actor(applicant))
    append_event(conn, actor=_actor(applicant), kind="application.created",
                 payload={"application_id": app_id, "form_key": form.key, "form_version": form.version,
                          "property_source": snap["source"]})
    return {"id": app_id}


@router.get("/api/applications")
def list_applications(applicant: auth.Applicant = auth.require, conn: Connection = transaction):
    out = []
    for r in apps.mine(conn, applicant.id):
        form = _load(r.form_key, r.form_version)
        out.append({"id": str(r.id), "form_key": r.form_key, "official_title": form.official_title if form else r.form_key,
                    "map_lot": r.map_lot, "status": r.status, "updated_at": r.updated_at.isoformat()})
    return out


def _form_for(row: apps.AppRow) -> FormDef:
    return load_form(row.form_key, row.form_version, load_ruleset(row.ruleset_key))


def _state(conn: Connection, row: apps.AppRow, applicant: auth.Applicant) -> dict:
    form = _form_for(row)
    cur = apps.current(conn, row.id, applicant.email)
    carried = apps.carried(conn, row.id)
    return {
        "id": row.id, "form_key": row.form_key, "form_version": row.form_version, "ruleset_key": row.ruleset_key,
        "status": row.status, "revision": apps.revision(conn, row.id), "property": apps.snapshot(conn, row.id),
        "items": apps.items(conn, row.id),
        "answers": [{"field_id": f, "item_id": i, "value": v, "carried": (f, i) in carried}
                    for (f, i), v in cur.answers.items()],
        "notes": apps.notes(conn, row.id), "attachments": apps.attachments(conn, row.id),
        "missing": [{"field_id": f, "item_id": i} for f, i in missing(form, cur)],
        "newer_version": latest_version(row.form_key) > row.form_version,
    }


@router.get("/api/applications/{app_id}")
def get_application(app_id: str, applicant: auth.Applicant = auth.require, conn: Connection = transaction):
    row = apps.owned(conn, app_id, applicant.id)
    return _state(conn, row, applicant) if row else _NOT_FOUND()


class Change(BaseModel):
    field_id: str = PField(max_length=100)
    item_id: str | None = None
    value: Any = None


class AnswersBody(BaseModel):
    base_revision: int
    changes: list[Change] = PField(max_length=200)


def _parcel_bounds(conn: Connection) -> tuple | None:
    imp = prop.active_import(conn, "parcels")
    if imp is None:
        return None
    r = conn.execute(text(
        "SELECT ST_XMin(e) AS x0, ST_YMin(e) AS y0, ST_XMax(e) AS x1, ST_YMax(e) AS y1"
        " FROM (SELECT ST_Extent(ST_Transform(geom, 4326)) AS e FROM parcel WHERE import_id = :i) t"
    ), {"i": imp.id}).one()
    return None if r.x0 is None else (r.x0, r.y0, r.x1, r.y1)


def _conflict(conn: Connection, app_id: str) -> JSONResponse:
    return JSONResponse({"detail": "changed_elsewhere", "revision": apps.revision(conn, app_id)}, status_code=409)


@router.put("/api/applications/{app_id}/answers")
def save_answers(app_id: str, body: AnswersBody, applicant: auth.Applicant = auth.require,
                 conn: Connection = transaction):
    row = apps.owned(conn, app_id, applicant.id)
    if row is None:
        return _NOT_FOUND()
    form = _form_for(row)
    live = {i["id"]: i["kind"] for i in apps.items(conn, row.id)}
    bounds = _parcel_bounds(conn)
    checked, errors = [], []
    for c in body.changes:
        try:
            section, f = form.field(c.field_id)
        except KeyError:
            errors.append({"field_id": c.field_id, "item_id": c.item_id, "reason": "not_a_question"})
            continue
        item_ok = (c.item_id is None) if section.repeat is None else (live.get(c.item_id) == section.repeat.kind)
        if not item_ok:
            errors.append({"field_id": c.field_id, "item_id": c.item_id, "reason": "wrong_item"})
            continue
        try:
            checked.append((c.field_id, c.item_id, check_value(f, c.value, bounds=bounds)))
        except AnswerError as e:
            errors.append({"field_id": c.field_id, "item_id": c.item_id, "reason": e.reason})
    if errors:
        return _json(422, errors)
    rev = apps.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _conflict(conn, row.id)
    apps.save_answers(conn, row.id, checked, _actor(applicant))
    append_event(conn, actor=_actor(applicant), kind="application.answers_saved",
                 payload={"application_id": row.id, "fields": [[f, i] for f, i, _ in checked]})
    return {"revision": rev,
            "missing": [{"field_id": f, "item_id": i} for f, i in missing(form, apps.current(conn, row.id, applicant.email))]}


class ItemBody(BaseModel):
    kind: str = PField(max_length=40)
    base_revision: int


class RevisionBody(BaseModel):
    base_revision: int


def _repeat(form: FormDef, kind: str):
    return next((s.repeat for s in form.sections if s.repeat and s.repeat.kind == kind), None)


@router.post("/api/applications/{app_id}/items", status_code=201)
def add_item(app_id: str, body: ItemBody, applicant: auth.Applicant = auth.require, conn: Connection = transaction):
    row = apps.owned(conn, app_id, applicant.id)
    if row is None:
        return _NOT_FOUND()
    form = _form_for(row)
    repeat = _repeat(form, body.kind)
    if repeat is None:
        return _json(422, "unknown_kind")
    if sum(1 for i in apps.items(conn, row.id) if i["kind"] == body.kind) >= repeat.max:
        return _json(422, "too_many")
    rev = apps.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _conflict(conn, row.id)
    item_id = apps.new_item(conn, row.id, form, body.kind)
    append_event(conn, actor=_actor(applicant), kind="application.item_added",
                 payload={"application_id": row.id, "item_id": item_id, "kind": body.kind})
    return {"id": item_id, "revision": rev}


@router.delete("/api/applications/{app_id}/items/{item_id}")
def remove_item(app_id: str, item_id: str, body: RevisionBody, applicant: auth.Applicant = auth.require,
                conn: Connection = transaction):
    row = apps.owned(conn, app_id, applicant.id)
    if row is None:
        return _NOT_FOUND()
    live = {i["id"]: i["kind"] for i in apps.items(conn, row.id)}
    kind = live.get(apps.parse_id(item_id) or "")
    if kind is None:
        return _NOT_FOUND()
    repeat = _repeat(_form_for(row), kind)
    if repeat and sum(1 for k in live.values() if k == kind) <= repeat.min:
        return _json(422, "at_least_one")
    rev = apps.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _conflict(conn, row.id)
    apps.remove_item(conn, row.id, item_id)
    append_event(conn, actor=_actor(applicant), kind="application.item_removed",
                 payload={"application_id": row.id, "item_id": item_id})
    return {"revision": rev}


class NoteBody(BaseModel):
    base_revision: int
    section_id: str = PField(max_length=100)
    item_id: str | None = None
    text: str = PField(max_length=NOTE_MAX)


@router.put("/api/applications/{app_id}/notes")
def save_note(app_id: str, body: NoteBody, applicant: auth.Applicant = auth.require, conn: Connection = transaction):
    row = apps.owned(conn, app_id, applicant.id)
    if row is None:
        return _NOT_FOUND()
    section = next((s for s in _form_for(row).sections if s.id == body.section_id), None)
    if section is None:
        return _json(422, "unknown_section")
    live = {i["id"]: i["kind"] for i in apps.items(conn, row.id)}
    if (body.item_id is None) != (section.repeat is None) or (
            section.repeat and live.get(body.item_id) != section.repeat.kind):
        return _json(422, "wrong_item")
    rev = apps.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _conflict(conn, row.id)
    apps.save_note(conn, row.id, section.id, body.item_id, body.text.strip(), _actor(applicant))
    append_event(conn, actor=_actor(applicant), kind="application.note_saved",
                 payload={"application_id": row.id, "section_id": section.id, "item_id": body.item_id})
    return {"revision": rev}
