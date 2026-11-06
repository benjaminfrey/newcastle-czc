"""The guide's conversation, worked out from what the person has answered so far.

Nothing is kept between requests except the answers themselves. `replay` turns the recorded
actions into the facts, the turns already answered (exactly as they were shown), and the turn to
ask next, so a reload, a second tab or Back always lands on the same place. The same content,
lot and answers always give the same state (spec §5: consistency is tested, not assumed).

The next turn is the first, in order, whose condition holds and that has no answer yet. An
answer to a turn the content no longer has, or one its bounds no longer allow, is set aside and
the turn is asked again. "I'm not sure yet" is an answer on every question; it leaves the fact
unknown and moves on. Free text is not an action: what a person types never reaches this module.
"""

import dataclasses
import math
from dataclasses import dataclass
from typing import Literal

from portal_api.forms.expr import evaluate
from portal_api.guide.checks import Check, check_turn, stories_settled
from portal_api.guide import endings
from portal_api.guide.content import Answer, Content, Turn, drafts_in
from portal_api.guide.drawing import frontages, fronting

UNSURE = "unsure"
PICK_OPENING = "pick_opening"
DOESNT_FIT = "doesnt_fit:"


@dataclass(frozen=True)
class Lot:
    map_lot: str | None
    district_codes: tuple[str, ...]
    district_names: tuple[str, ...]
    acres: float | None            # from the tax map: approximate
    frontage_ft: int | None        # from the tax map: approximate
    disputed: bool = False         # the applicant said the Town's facts were wrong when starting
    lines: tuple[dict, ...] = ()   # the tax-map lot lines (lot_outline.py): id, length_ft, street, points

    @staticmethod
    def from_snapshot(snapshot: dict) -> "Lot":
        facts = snapshot.get("facts") or {}
        districts = [d for d in facts.get("districts") or [] if d.get("code")]
        streets = facts.get("streets") or []
        frontage = sum(s.get("frontage_ft") or 0 for s in streets) if streets else None
        return Lot(map_lot=snapshot.get("map_lot") or facts.get("map_lot"),
                   district_codes=tuple(d["code"] for d in districts),
                   district_names=tuple(d.get("name") or d["code"] for d in districts),
                   acres=facts.get("acres"), frontage_ft=frontage, disputed=bool(snapshot.get("disputed")),
                   lines=tuple({"id": L["id"], "length_ft": L["length_ft"], "street": L["street"],
                                "points": L.get("points")}
                               for L in (facts.get("outline") or {}).get("lines") or []))


@dataclass(frozen=True)
class Step:
    n: int
    of: int
    label: str


@dataclass(frozen=True)
class Shown:
    turn_id: str
    kind: str
    step: Step
    ask: str
    help: str | None
    answers: tuple[dict, ...]
    input: dict | None = None
    why: dict | None = None
    defines: tuple[dict, ...] = ()
    check: dict | None = None
    facts_shown: dict | None = None
    drawing: str | None = None      # which part of the lot drawing this turn asks about (plan 4)


@dataclass(frozen=True)
class Action:
    kind: Literal["answer", "back", "revisit"]
    turn_id: str | None
    value: object


@dataclass(frozen=True)
class State:
    opening: str
    facts: dict
    history: tuple[tuple[Shown, object], ...]
    current: Shown | None
    ending: dict | None
    unsure: tuple[str, ...]
    drafts: tuple[str, ...]
    live: tuple[tuple[str, object], ...]   # the answers in force, in the order they were given
    checks: tuple[tuple[str, dict], ...] = ()   # the latest check for each checked turn
    kept: tuple[tuple[str, str], ...] = ()      # a number kept past its limit: (turn, keep_mine / talk_to_town / unsure)
    current_turn: Turn | None = None
    undo: tuple[tuple, ...] = ()                # the answers in force before each answer or Change, for Back
    changed: tuple | None = None                # the last Change: (turn, the answers in force before it)
    reopened: tuple[str, ...] = ()              # later answers that Change put out of force, to ask again


class AnswerRejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _set(facts: dict, path: str, value) -> None:
    head, _, rest = path.partition(".")
    if rest:
        _set(facts.setdefault(head, {}), rest, value)
    else:
        facts[head] = value


def _holds(turn: Turn, facts: dict) -> bool | None:
    return True if turn.when is None else evaluate(turn.when, facts)


class _Build:
    """One derivation: the wording keys and entries it shows, for the drafts list."""

    def __init__(self, content: Content, opening: str, lot: Lot):
        self.content, self.opening, self.lot = content, opening, lot
        self.wording: list[str] = []
        self.entries: list[str] = []

    def word(self, key: str) -> str:
        self.wording.append(key)
        return self.content.wording[key]["text"]

    def entry(self, key: str) -> dict:
        e = self.content.entries[key]
        self.entries.append(key)
        return {"id": e.id, "overline": e.overline, "answer": e.answer, "detail": e.detail, "why": e.why,
                "cites": list(e.cites), "version": e.version, "governs": self.word("governs"),
                "picture": e.picture, "picture_alt": e.picture_alt}

    def answers(self, turn: Turn, facts: dict) -> tuple:
        if turn.answers_from == "use_groups":
            base = self.content.group_answers
        elif turn.answers_from == "use_group_uses":
            base = self.content.use_answers.get((facts.get("use") or {}).get("group"), ())
        elif turn.answers_from == "lot_lines":
            fr = frontages(list(self.lot.lines))
            on_road = [L for L in self.lot.lines if fronting(L)]
            if fr["kind"] == "corner":
                # The Code's front only (the chair, 2026-11-05): another road goes to the Town.
                L = next(x for x in on_road if x["id"] == fr["primary"])
                return (Answer(L["id"], self.word("front_primary").format(street=L["street"]["name"]), None,
                               {"lot.front": L["id"]}),
                        Answer("other", self.word("front_other"), None, {"lot.front": "other"}))
            names = [L["street"]["name"] for L in on_road]
            def label(L):
                # Two lines along one road (the lot wraps round it) are told apart by length.
                if names.count(L["street"]["name"]) > 1:
                    return self.word("front_along_length").format(street=L["street"]["name"], n=L["length_ft"])
                return self.word("front_along").format(street=L["street"]["name"])
            base = tuple(Answer(L["id"], label(L), None, {"lot.front": L["id"]}) for L in on_road)
            base += (Answer("other", self.word("front_other"), None, {"lot.front": "other"}),)
        else:
            base = turn.answers
        return base

    def help(self, turn: Turn) -> str | None:
        if turn.answers_from == "lot_lines" and frontages(list(self.lot.lines))["kind"] == "corner":
            return self.word("front_help_corner")
        return turn.help

    def steps(self, facts: dict) -> list[str]:
        return list(dict.fromkeys(t.step for t in self.content.turns if _holds(t, facts) is not False))

    def step(self, label: str, facts: dict) -> Step:
        labels = self.steps(facts)
        return Step(labels.index(label) + 1 if label in labels else len(labels), len(labels), label)

    def ask(self, turn: Turn) -> str:
        if turn.kind != "confirm":
            return turn.ask
        o = self.content.openings[self.opening]
        lot = self.lot
        districts = " and ".join(lot.district_names) if lot.district_names else self.word("district_unknown")
        slots = {"opening": o.label[:1].lower() + o.label[1:], "map_lot": lot.map_lot or self.word("map_lot_unknown"),
                 "districts": districts}
        return self.word(o.confirm).format(**slots)

    def facts_shown(self) -> dict:
        lot = self.lot
        return {"map_lot": lot.map_lot,
                "districts": [{"code": c, "name": n} for c, n in zip(lot.district_codes, lot.district_names)],
                "acres": {"value": lot.acres, "approximate": True},
                "frontage_ft": {"value": lot.frontage_ft, "approximate": True}}

    def shown(self, turn: Turn, facts: dict) -> Shown:
        answers = tuple({"id": a.id, "label": a.label, "hint": a.hint} for a in self.answers(turn, facts))
        answers += ({"id": UNSURE, "label": self.word("unsure"), "hint": None},)
        return Shown(
            turn_id=turn.id, kind=turn.kind, step=self.step(turn.step, facts), ask=self.ask(turn), help=self.help(turn),
            answers=answers,
            input={"unit": turn.unit, "min": turn.min, "max": turn.max} if turn.kind == "number" else None,
            why=self.entry(turn.why) if turn.why else None,
            defines=tuple(self.entry(d) for d in turn.defines),
            facts_shown=self.facts_shown() if turn.kind == "lot" else None, drawing=turn.drawing)

    def picker(self, facts: dict) -> Shown:
        answers = tuple({"id": o.id, "label": o.label, "hint": None} for o in self.content.openings.values())
        confirm = next((t for t in self.content.turns if t.kind == "confirm"), None)
        label = confirm.step if confirm else ""
        return Shown(turn_id=PICK_OPENING, kind="choice", step=self.step(label, facts), ask=self.word("pick_opening"),
                     help=None, answers=answers)


def _valid(build: _Build, turn: Turn, facts: dict, value) -> str | None:
    """None if `value` answers `turn`, else why not."""
    if value == UNSURE:
        return None
    if turn.kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            return "bad_value"
        if value < turn.min or value > turn.max:
            return "out_of_range"
        return None
    if not isinstance(value, str) or value not in {a.id for a in build.answers(turn, facts)}:
        return "not_an_answer"
    return None


def _record(build: _Build, turn: Turn, facts: dict, value) -> None:
    if value == UNSURE:
        return
    if turn.kind == "number":
        _set(facts, turn.fact, value)
        return
    answer = next(a for a in build.answers(turn, facts) if a.id == value)
    for path, v in answer.set.items():
        _set(facts, path, v)


def _derive(content: Content, opening: str, lot: Lot, live: tuple, undo: tuple = (),
            changed: tuple | None = None) -> State:
    build = _Build(content, opening, lot)
    o = content.openings[opening]
    facts: dict = {"opening": opening, "lot": {"has_outline": bool(lot.lines),
                                               "corner": frontages(list(lot.lines))["kind"] == "corner"}}
    for path, v in o.facts.items():
        _set(facts, path, v)
    given = dict(live)
    done: set[str] = set()
    history, unsure, checks, kept = [], [], {}, []
    current = current_turn = None

    def ask(turn: Turn) -> bool:
        """Record `turn`'s answer if it has a valid one; otherwise make it the current turn."""
        nonlocal current, current_turn
        shown = build.shown(turn, facts)
        value = given.get(turn.id, _MISSING)
        if value is _MISSING or _valid(build, turn, facts, value) is not None:
            current, current_turn = shown, turn
            return False
        settled_before = stories_settled(facts, unsure)
        _record(build, turn, facts, value)
        if value == UNSURE:
            unsure.append(turn.id)
        chk = _check(content, turn, facts, lot, unsure, settled_before) if value != UNSURE else None
        if chk is not None:
            checks[turn.id] = dataclasses.asdict(chk)
            shown = dataclasses.replace(shown, check=checks[turn.id])
        history.append((shown, value))
        if chk is None or chk.result != "outside":
            return True
        fit = _doesnt_fit(build, turn, chk)
        before = given.get(fit.id, _MISSING)
        if not ask(fit):
            return False
        if before in ("keep_mine", "talk_to_town", UNSURE):
            kept.append((turn.id, before))
        else:  # the nearest version: the fact is replaced, so check it again
            again = _check(content, turn, facts, lot, unsure, False)
            checks[turn.id] = dataclasses.asdict(again)
        return True

    while True:
        if facts.get("confirmed") is False:
            current = build.picker(facts)
            break
        turn = next((t for t in content.turns if t.id not in done and _holds(t, facts) is True), None)
        if turn is None:
            break
        done.add(turn.id)
        if not ask(turn):
            break
    ending = None
    if current is None:
        end = endings.finish(content, opening, facts, tuple(dict.fromkeys(unsure)), checks, lot, tuple(kept))
        build.wording.append(end["kind"])
        words = content.wording[end["kind"]]
        ending = {**end, "title": words["title"], "body": words["body"],
                  "entry": build.entry(end["entry"]) if end["entry"] else None}
    shown_turns = [s.turn_id for s, _ in history] + ([current.turn_id] if current else [])
    drafts = drafts_in(content, opening=opening, turn_ids=shown_turns, entry_ids=build.entries,
                       wording_keys=build.wording)
    if ending is not None:
        drafts += ending.pop("screener_drafts")
    # What a Change reopened (the chair, 2026-11-05): once the changed question is answered again,
    # the answers given before it that no longer stand, where their question still applies.
    reopened: tuple = ()
    answered = {sh.turn_id for sh, _ in history}
    if changed is not None and changed[0] in answered:
        reopened = tuple(t for t, _ in changed[1] if t != changed[0] and not t.startswith(DOESNT_FIT)
                         and t not in answered and (x := content.turn(t)) is not None and _holds(x, facts) is not False)
    return State(opening=opening, facts=facts, history=tuple(history), current=current, ending=ending,
                 unsure=tuple(dict.fromkeys(unsure)), drafts=tuple(drafts), live=live,
                 checks=tuple(checks.items()), current_turn=current_turn, kept=tuple(kept), undo=undo,
                 changed=changed, reopened=reopened)


def _check(content: Content, turn: Turn, facts: dict, lot: Lot, unsure: list, settled_before: bool) -> Check | None:
    """A turn's own check, or, for a computed value, the check on the turn that completes it."""
    if turn.computed is None:
        return check_turn(turn, facts, lot, unsure)
    if settled_before or not stories_settled(facts, unsure):
        return None
    standard = next((t.standard for t in content.turns if t.computed == turn.computed and t.standard), None)
    return check_turn(turn, facts, lot, unsure, standard=standard)


def _number(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _doesnt_fit(build: _Build, turn: Turn, chk: Check) -> Turn:
    """The page for a number past its limit (spec §4.5): the gap, the nearest version that fits
    (for a number the person sets directly), keeping their number, or the Town Office."""
    unit = chk.unit or turn.unit or ""
    direction = build.word("direction_over" if chk.direction == "over" else "direction_short")
    ask = build.word("doesnt_fit").format(gap=_number(chk.gap), unit=unit, direction=direction)
    answers = tuple(Answer("nearest", build.word("nearest").format(value=_number(n["value"]), unit=unit), None,
                           {turn.fact: n["value"]}) for n in chk.nearest)
    answers += (Answer("keep_mine", build.word("keep_mine"), None, {}),
                Answer("talk_to_town", build.word("talk_to_town"), None, {}))
    return Turn(id=DOESNT_FIT + turn.id, order=turn.order, step=turn.step, kind="choice", ask=ask,
                status="draft", answers=answers, why=turn.why, cite=turn.cite)


_MISSING = object()


def _push(live: tuple, turn_id: str, value) -> tuple:
    return tuple((t, v) for t, v in live if t != turn_id) + ((turn_id, value),)


def _without(content: Content, live: tuple, turn_id: str) -> tuple:
    """Change ("revisit"): the answer to `turn_id`, and its "doesn't fit" choice, out of force, so
    that turn is asked again and every later answer still stands where it still applies. A computed
    value (stories) is checked on the turn that completes it, so changing any of its inputs clears
    that value's "doesn't fit" choice too: an old "keep mine" never covers a new number unasked."""
    turn = content.turn(turn_id)
    group = [t.id for t in content.turns if turn is not None and turn.computed and t.computed == turn.computed]
    gone = {turn_id, DOESNT_FIT + turn_id, *(DOESNT_FIT + t for t in group)}
    return tuple((t, v) for t, v in live if t not in gone)


def _back(live: tuple, undo: tuple) -> tuple[tuple, tuple]:
    """Back undoes the last answer or Change: the answers in force before it, so Back after a
    Change puts that answer back rather than dropping a later one."""
    return (undo[-1], undo[:-1]) if undo else (live[:-1], ())


def replay(content: Content, opening: str, lot: Lot, actions: list[Action]) -> State:
    """The state after the recorded actions. Answers were checked when they were given; here an
    answer the content no longer accepts is set aside rather than refused."""
    live: tuple = ()
    undo: tuple = ()
    changed = None
    for action in actions:
        if action.kind == "back":
            live, undo = _back(live, undo)
            changed = None
        elif action.kind == "answer":
            live, undo = _push(live, action.turn_id, action.value), undo + (live,)
        elif action.kind == "revisit":
            changed = (action.turn_id, live)
            live, undo = _without(content, live, action.turn_id), undo + (live,)
        else:
            raise AnswerRejected("not_an_action")
    return _derive(content, opening, lot, live, undo, changed)


def apply(content: Content, state: State, lot: Lot, action: Action) -> State:
    """One new action, checked against the turn being asked now."""
    if action.kind == "back":
        return _derive(content, state.opening, lot, *_back(state.live, state.undo))
    if action.kind == "revisit":
        if action.turn_id not in dict(state.live) or action.turn_id.startswith(DOESNT_FIT):
            raise AnswerRejected("not_answered")
        return _derive(content, state.opening, lot, _without(content, state.live, action.turn_id),
                       state.undo + (state.live,), (action.turn_id, state.live))
    if action.kind != "answer":
        raise AnswerRejected("not_an_action")
    current = state.current
    if current is None or current.turn_id != action.turn_id or current.turn_id == PICK_OPENING:
        raise AnswerRejected("not_current")
    turn = state.current_turn
    reason = _valid(_Build(content, state.opening, lot), turn, state.facts, action.value)
    if reason is not None:
        raise AnswerRejected(reason)
    return _derive(content, state.opening, lot, _push(state.live, action.turn_id, action.value),
                   state.undo + (state.live,), state.changed)
