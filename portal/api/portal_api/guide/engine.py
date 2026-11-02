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

import math
from dataclasses import dataclass
from typing import Literal

from portal_api.forms.expr import evaluate
from portal_api.guide.content import Content, Turn, drafts_in

UNSURE = "unsure"
PICK_OPENING = "pick_opening"


@dataclass(frozen=True)
class Lot:
    map_lot: str | None
    district_codes: tuple[str, ...]
    district_names: tuple[str, ...]
    acres: float | None            # from the tax map: approximate
    frontage_ft: int | None        # from the tax map: approximate
    disputed: bool = False         # the applicant said the Town's facts were wrong when starting

    @staticmethod
    def from_snapshot(snapshot: dict) -> "Lot":
        facts = snapshot.get("facts") or {}
        districts = [d for d in facts.get("districts") or [] if d.get("code")]
        streets = facts.get("streets") or []
        frontage = sum(s.get("frontage_ft") or 0 for s in streets) if streets else None
        return Lot(map_lot=snapshot.get("map_lot") or facts.get("map_lot"),
                   district_codes=tuple(d["code"] for d in districts),
                   district_names=tuple(d.get("name") or d["code"] for d in districts),
                   acres=facts.get("acres"), frontage_ft=frontage, disputed=bool(snapshot.get("disputed")))


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


@dataclass(frozen=True)
class Action:
    kind: Literal["answer", "back"]
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
                "cites": list(e.cites), "version": e.version, "governs": self.word("governs")}

    def answers(self, turn: Turn, facts: dict) -> tuple:
        if turn.answers_from == "use_groups":
            base = self.content.group_answers
        elif turn.answers_from == "use_group_uses":
            base = self.content.use_answers.get((facts.get("use") or {}).get("group"), ())
        else:
            base = turn.answers
        return base

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
            turn_id=turn.id, kind=turn.kind, step=self.step(turn.step, facts), ask=self.ask(turn), help=turn.help,
            answers=answers,
            input={"unit": turn.unit, "min": turn.min, "max": turn.max} if turn.kind == "number" else None,
            why=self.entry(turn.why) if turn.why else None,
            defines=tuple(self.entry(d) for d in turn.defines),
            facts_shown=self.facts_shown() if turn.kind == "lot" else None)

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


def _derive(content: Content, opening: str, lot: Lot, live: tuple) -> State:
    build = _Build(content, opening, lot)
    o = content.openings[opening]
    facts: dict = {"opening": opening}
    for path, v in o.facts.items():
        _set(facts, path, v)
    given = dict(live)
    done: set[str] = set()
    history, unsure = [], []
    current = None
    while True:
        if facts.get("confirmed") is False:
            current = build.picker(facts)
            break
        turn = next((t for t in content.turns if t.id not in done and _holds(t, facts) is True), None)
        if turn is None:
            break
        done.add(turn.id)
        shown = build.shown(turn, facts)
        value = given.get(turn.id, _MISSING)
        if value is _MISSING or _valid(build, turn, facts, value) is not None:
            current = shown
            break
        _record(build, turn, facts, value)
        if value == UNSURE:
            unsure.append(turn.id)
        history.append((shown, value))
    shown_turns = [s.turn_id for s, _ in history] + ([current.turn_id] if current else [])
    drafts = drafts_in(content, opening=opening, turn_ids=shown_turns, entry_ids=build.entries,
                       wording_keys=build.wording)
    return State(opening=opening, facts=facts, history=tuple(history), current=current, ending=None,
                 unsure=tuple(unsure), drafts=tuple(drafts), live=live)


_MISSING = object()


def _push(live: tuple, turn_id: str, value) -> tuple:
    return tuple((t, v) for t, v in live if t != turn_id) + ((turn_id, value),)


def replay(content: Content, opening: str, lot: Lot, actions: list[Action]) -> State:
    """The state after the recorded actions. Answers were checked when they were given; here an
    answer the content no longer accepts is set aside rather than refused."""
    live: tuple = ()
    for action in actions:
        if action.kind == "back":
            live = live[:-1]
        elif action.kind == "answer":
            live = _push(live, action.turn_id, action.value)
        else:
            raise AnswerRejected("not_an_action")
    return _derive(content, opening, lot, live)


def apply(content: Content, state: State, lot: Lot, action: Action) -> State:
    """One new action, checked against the turn being asked now."""
    if action.kind == "back":
        return _derive(content, state.opening, lot, state.live[:-1])
    if action.kind != "answer":
        raise AnswerRejected("not_an_action")
    current = state.current
    if current is None or current.turn_id != action.turn_id or current.turn_id == PICK_OPENING:
        raise AnswerRejected("not_current")
    turn = content.turn(action.turn_id)
    reason = _valid(_Build(content, state.opening, lot), turn, state.facts, action.value)
    if reason is not None:
        raise AnswerRejected(reason)
    return _derive(content, state.opening, lot, _push(state.live, action.turn_id, action.value))
