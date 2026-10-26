"""Application forms and parts (public), and what the project routes share with them:
loading a form, refusing one with drafts, and the property snapshot."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field as PField
from sqlalchemy import Connection

from portal_api import property as prop
from portal_api.forms.definitions import DefinitionError
from portal_api.forms.formdefs import FORM_KEYS, FormDef, form_drafts, latest_version, load_form
from portal_api.forms.parts import load_parts
from portal_api.ratelimit import lookup_limit
from portal_api.ruleset import load_ruleset

router = APIRouter()


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
            "step": s.step, "screens": [{"id": x.id, "layout": x.layout, "title": x.title, "help": x.help} for x in s.screens],
            "repeat": None if s.repeat is None else {
                "kind": s.repeat.kind, "add_label": s.repeat.add_label, "min": s.repeat.min, "max": s.repeat.max},
            "fields": [{
                "id": f.id, "official_label": f.official_label, "source": f.source, "from": f.from_,
                "may_correct": f.may_correct, "label": f.label, "help": f.help, "why": why(f.why), "type": f.type,
                "unit": f.unit, "min": f.min, "max": f.max, "required": f.required, "allow_unknown": f.allow_unknown,
                "show_if": f.show_if, "step": f.step or s.step, "screen": f.screen, "ask_first": f.ask_first, "control": f.control,
                "step_size": f.step_size, "default": f.default, "autocomplete": f.autocomplete,
                "options": [{"value": o.value, "label": o.label, "official": o.official, "icon": o.icon} for o in f.options],
                "copies": f.copies, "short": f.short,
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


@router.get("/api/parts", dependencies=[Depends(lookup_limit)])
def get_parts():
    """The parts a project can have, in tile order (projects brief §4)."""
    return [{"id": p.id, "label": p.label, "step": p.step, "icon": p.icon, "repeats": p.repeats} for p in load_parts().parts]


def _snapshot(conn: Connection, request: Request, body) -> dict | JSONResponse:
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


