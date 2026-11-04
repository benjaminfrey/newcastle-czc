"""The guided conversation for a project (guided plan 2).

Someone else's project answers 404, as in routes/projects.py. Every change carries
base_revision (409 `changed_elsewhere` on a stale one) and is refused once staff have locked the
project (409 `locked`). A state that rests on draft wording is refused (503
`guide_not_approved`) unless the deployment allows drafts. What a person types is stored and
shown back to them, and nothing reads it (spec decision 14); events never carry it.
"""

import dataclasses

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field as PField
from sqlalchemy import Connection

from portal_api import auth
from portal_api import projects as pj
from portal_api.db import transaction
from portal_api.events import append_event
from portal_api.guide import bridge, drawing, store
from portal_api.guide.checks import check_turn, limit_for
from portal_api.guide.content import drafts_in, load_content
from portal_api.guide.engine import PICK_OPENING, Action, AnswerRejected, Lot, _valid, _Build, apply, replay
from portal_api.routes.projects import Loaded, _refuse_stale

router = APIRouter()


def _json(status: int, detail) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=status)


def _actor(applicant: auth.Applicant) -> str:
    return f"applicant:{applicant.id}"


class StartBody(BaseModel):
    opening: str = PField(max_length=60)
    base_revision: int


class AnswerBody(BaseModel):
    turn_id: str = PField(max_length=120)
    value: str | int | float | bool | None = None
    base_revision: int


class RevisionBody(BaseModel):
    base_revision: int


class RevisitBody(BaseModel):
    turn_id: str = PField(max_length=120)
    base_revision: int


class CheckBody(BaseModel):
    turn_id: str = PField(max_length=120)
    value: str | int | float | bool | None = None


class NoteBody(BaseModel):
    body: str = PField(min_length=1, max_length=4000)
    base_revision: int


def _out(conn: Connection, project_id: str, state, revision: int) -> dict:
    asdict = dataclasses.asdict
    return {"revision": revision, "opening": state.opening,
            "current": asdict(state.current) if state.current else None,
            "history": [{"shown": asdict(s), "value": v} for s, v in state.history],
            "ending": state.ending, "step": asdict(state.current.step) if state.current else None,
            "unsure": list(state.unsure), "checks": dict(state.checks), "notes": store.notes(conn, project_id), "drafts": list(state.drafts)}


def _refused(state, request: Request) -> bool:
    return bool(state.drafts) and not request.app.state.settings.allow_draft_rules


def _load(conn: Connection, project_id: str, applicant: auth.Applicant):
    """(row, lot, opening, actions, state), or a refusal."""
    row = pj.owned(conn, project_id, applicant.id)
    if row is None:
        return _json(404, "not_found")
    convo = store.conversation(conn, row.id)
    if convo is None:
        return _json(404, "not_started")
    lot = Lot.from_snapshot(pj.snapshot(conn, row.id))
    opening, actions = convo
    return row, lot, opening, actions, replay(load_content(), opening, lot, actions)


def _change(conn, request, applicant, project_id, base_revision, act, turn_id=None):
    """The shared path of every change: load, apply, gate, bump, record, bridge."""
    loaded = _load(conn, project_id, applicant)
    if isinstance(loaded, JSONResponse):
        return loaded
    row, lot, opening, actions, state = loaded
    if row.status not in pj.EDITABLE:
        return _json(409, "locked")
    # A stale page is told so before its answer is judged: another tab may have moved the turn on.
    if pj.state(conn, row.id)[1] != base_revision:
        return _refuse_stale(conn, row.id)
    try:
        new, record, kind = act(row, lot, state)
    except AnswerRejected as e:
        return _json(422, e.reason)
    if _refused(new, request):
        return _json(503, "guide_not_approved")
    rev = pj.bump(conn, row.id, base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    record()
    bridge.sync(conn, Loaded(conn, row), new, _actor(applicant))
    append_event(conn, actor=_actor(applicant), kind=kind, payload={"project_id": row.id, "turn_id": _turn_of(new, kind, turn_id)})
    return _out(conn, row.id, new, rev)


def _turn_of(state, kind, turn_id=None):
    if kind == "guide.revisited":
        return turn_id
    return state.history[-1][0].turn_id if kind == "guide.answered" and state.history else None


@router.post("/api/projects/{project_id}/guide", status_code=201)
def start(project_id: str, body: StartBody, request: Request, applicant: auth.Applicant = auth.require,
          conn: Connection = transaction):
    row = pj.owned(conn, project_id, applicant.id)
    if row is None:
        return _json(404, "not_found")
    if row.status not in pj.EDITABLE:
        return _json(409, "locked")
    content = load_content()
    o = content.openings.get(body.opening)
    if o is None:
        return _json(422, "unknown_opening")
    if o.part not in {p["kind"] for p in pj.parts(conn, row.id)}:
        return _json(422, "wrong_project")
    lot = Lot.from_snapshot(pj.snapshot(conn, row.id))
    convo = store.conversation(conn, row.id)
    if convo is not None:
        before = replay(content, convo[0], lot, convo[1])
        if before.current is None or before.current.turn_id != PICK_OPENING:
            return _json(409, "already_started")
    new = replay(content, body.opening, lot, [])
    if _refused(new, request):
        return _json(503, "guide_not_approved")
    rev = pj.bump(conn, row.id, body.base_revision)
    if rev is None:
        return _refuse_stale(conn, row.id)
    if convo is None:
        store.start(conn, row.id, body.opening, content.digest)
        kind = "guide.started"
    else:
        store.restart(conn, row.id, body.opening, dataclasses.asdict(before.current), content.digest, _actor(applicant))
        kind = "guide.restarted"
    append_event(conn, actor=_actor(applicant), kind=kind, payload={"project_id": row.id, "turn_id": None})
    return _out(conn, row.id, new, rev)


@router.get("/api/projects/{project_id}/guide")
def get_guide(project_id: str, request: Request, applicant: auth.Applicant = auth.require,
              conn: Connection = transaction):
    loaded = _load(conn, project_id, applicant)
    if isinstance(loaded, JSONResponse):
        return loaded
    row, _, _, _, state = loaded
    if _refused(state, request):
        return _json(503, "guide_not_approved")
    return _out(conn, row.id, state, pj.state(conn, row.id)[1])


@router.post("/api/projects/{project_id}/guide/answers")
def answer(project_id: str, body: AnswerBody, request: Request, applicant: auth.Applicant = auth.require,
           conn: Connection = transaction):
    action = Action("answer", body.turn_id, body.value)
    content = load_content()

    def act(row, lot, state):
        new = apply(content, state, lot, action)
        shown = dataclasses.asdict(state.current)
        return new, lambda: store.record(conn, row.id, action, shown, content.digest, _actor(applicant)), "guide.answered"
    return _change(conn, request, applicant, project_id, body.base_revision, act)


@router.post("/api/projects/{project_id}/guide/back")
def back(project_id: str, body: RevisionBody, request: Request, applicant: auth.Applicant = auth.require,
         conn: Connection = transaction):
    action = Action("back", None, None)
    content = load_content()

    def act(row, lot, state):
        new = apply(content, state, lot, action)
        shown = dataclasses.asdict(state.current) if state.current else {"ending": state.ending}
        return new, lambda: store.record(conn, row.id, action, shown, content.digest, _actor(applicant)), "guide.back"
    return _change(conn, request, applicant, project_id, body.base_revision, act)


@router.post("/api/projects/{project_id}/guide/revisit")
def revisit(project_id: str, body: RevisitBody, request: Request, applicant: auth.Applicant = auth.require,
            conn: Connection = transaction):
    """Change: the answer to one turn out of force, so it is asked again; later answers stand."""
    action = Action("revisit", body.turn_id, None)
    content = load_content()

    def act(row, lot, state):
        new = apply(content, state, lot, action)
        shown = dataclasses.asdict(state.current) if state.current else {"ending": state.ending}
        return new, lambda: store.record(conn, row.id, action, shown, content.digest, _actor(applicant)), "guide.revisited"
    return _change(conn, request, applicant, project_id, body.base_revision, act, body.turn_id)


DRAWN_LIMITS = {"front": "setback_front", "side": "setback_side_1", "rear": "setback_rear"}


@router.get("/api/projects/{project_id}/guide/drawing")
def get_drawing(project_id: str, request: Request, applicant: auth.Applicant = auth.require,
                conn: Connection = transaction):
    """The lot drawing (plan 4): the tax-map outline, what each line is once the front is chosen,
    and the setback limits for this lot from the rulesets. No words, so no draft gate."""
    loaded = _load(conn, project_id, applicant)
    if isinstance(loaded, JSONResponse):
        return loaded
    row, lot, _, _, state = loaded
    outline = (pj.snapshot(conn, row.id).get("facts") or {}).get("outline")
    front = (state.facts.get("lot") or {}).get("front")
    content = load_content()
    limits = {}
    for role, turn_id in DRAWN_LIMITS.items():
        lim = limit_for(content.turn(turn_id), lot, state.facts)
        limits[role] = dataclasses.asdict(lim) if lim else None
    return {"outline": outline, "front": front if outline else None,
            "roles": drawing.roles(outline["lines"], front) if outline else None, "limits": limits}


@router.get("/api/projects/{project_id}/guide/openings")
def openings(project_id: str, request: Request, applicant: auth.Applicant = auth.require,
             conn: Connection = transaction):
    """The pictures this project's parts can start from, before the guide has started."""
    row = pj.owned(conn, project_id, applicant.id)
    if row is None:
        return _json(404, "not_found")
    content = load_content()
    kinds = {p["kind"] for p in pj.parts(conn, row.id)}
    listed = [o for o in content.openings.values() if o.part in kinds]
    drafts = [d for o in listed for d in drafts_in(content, opening=o.id, turn_ids=[], entry_ids=[], wording_keys=[])]
    if drafts and not request.app.state.settings.allow_draft_rules:
        return _json(503, "guide_not_approved")
    return {"openings": [{"id": o.id, "label": o.label, "part": o.part} for o in listed]}


@router.post("/api/projects/{project_id}/guide/notes", status_code=201)
def note(project_id: str, body: NoteBody, request: Request, applicant: auth.Applicant = auth.require,
         conn: Connection = transaction):
    def act(row, lot, state):
        return state, lambda: store.add_note(conn, row.id, body.body, _actor(applicant)), "guide.note"
    return _change(conn, request, applicant, project_id, body.base_revision, act)


@router.post("/api/projects/{project_id}/guide/check")
def check(project_id: str, body: CheckBody, request: Request, applicant: auth.Applicant = auth.require,
          conn: Connection = transaction):
    """The check for a value not yet given, so the screen can show the room left as it changes
    (spec §4.4). Saves nothing."""
    loaded = _load(conn, project_id, applicant)
    if isinstance(loaded, JSONResponse):
        return loaded
    _, lot, opening, _, state = loaded
    if _refused(state, request):
        return _json(503, "guide_not_approved")
    turn = state.current_turn
    if turn is None or turn.id != body.turn_id or turn.kind != "number":
        return _json(422, "not_current")
    reason = "bad_value" if body.value == "unsure" else _valid(_Build(load_content(), opening, lot), turn,
                                                                state.facts, body.value)
    if reason is not None:
        return _json(422, reason)
    facts = _with(state.facts, turn.fact, body.value)
    c = check_turn(turn, facts, lot, state.unsure)
    return dataclasses.asdict(c) if c else {"result": None}


def _with(facts: dict, path: str, value) -> dict:
    import copy
    out = copy.deepcopy(facts)
    cur = out
    *head, last = path.split(".")
    for p in head:
        cur = cur.setdefault(p, {})
    cur[last] = value
    return out
