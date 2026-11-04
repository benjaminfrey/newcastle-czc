"""A person's numbers against the Code's standards for their lot (spec §4.4, §4.5).

Every number is worked out by the rulesets (plan 1's `standards`), never by the guide's wording.
A standard that can't be checked, a lot in two districts that disagree, a lot whose facts the
person disputes, or an input they aren't sure of all give `cannot_check`: a question for the
Town, never a "no". Stories are counted the way the Code counts them (5.7.c.3–6), not the way a
person might, so "three floors" with one inside the roof can still be two stories.
"""

from dataclasses import dataclass
from typing import Literal

from portal_api.ruleset import district_key_for
from portal_api.standards import check, standards_for

STORY_INPUTS = ("full_stories", "roof_floors", "top_knee_over_3ft", "basement_exposed_5ft")


@dataclass(frozen=True)
class Check:
    result: Literal["fits", "outside", "cannot_check"]
    value: float | None
    min: float | None
    max: float | None
    unit: str | None
    room: float | None
    gap: float | None
    direction: Literal["over", "short"] | None
    reason: str | None
    standard_keys: tuple[str, ...]
    nearest: tuple[dict, ...]   # {"id": "nearest", "value": v}; the engine adds the words


def _needed(b: dict, unsure) -> list[str]:
    """The story inputs this building needs: the knee wall only when a floor is inside the roof."""
    need = ["full_stories", "roof_floors", "basement_exposed_5ft"]
    roof = b.get("roof_floors")
    if isinstance(roof, (int, float)) and roof >= 1:
        need.append("top_knee_over_3ft")
    return need


def stories_settled(facts: dict, unsure=()) -> bool:
    """Every story input is answered, or answered "I'm not sure yet"."""
    b = facts.get("building") or {}
    return all(k in b or k in unsure for k in _needed(b, unsure))


def counted_stories(facts: dict) -> int | None:
    """Stories as the Code counts them, or None while any input is unknown.
    Full stories, plus every floor inside the roof but the top one (5.7.c.4), plus the top one
    when the roof meets the wall more than 3 feet above its floor (5.7.c.5), plus a basement with
    5 feet or more of wall exposed along the front (5.7.c.6). Space within the pitch is otherwise
    not a story (5.7.c.3)."""
    b = facts.get("building") or {}
    if any(k not in b for k in _needed(b, ())):
        return None
    roof = b["roof_floors"]
    count = b["full_stories"] + max(roof - 1, 0)
    if roof >= 1 and b["top_knee_over_3ft"]:
        count += 1
    if b["basement_exposed_5ft"]:
        count += 1
    return count


def _get(facts: dict, path: str):
    cur = facts
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _uncertain(reason: str, value=None, unit=None, keys=()) -> Check:
    return Check("cannot_check", value, None, None, unit, None, None, None, reason, tuple(keys), ())


def _lookup(spec: dict, lot, facts: dict) -> tuple[str | None, list]:
    """The lot's standards for `spec`, one per district, or why there are none to use."""
    if lot.disputed or _get(facts, "lot.confirmed") is False:
        return "lot_disputed", []
    keys = [district_key_for(c) for c in lot.district_codes]
    if not keys or None in keys:
        return "no_district", []
    found = [next((s for s in standards_for(k) if s.source == spec["source"] and s.field == spec["field"]
                   and s.building == spec.get("building")), None) for k in dict.fromkeys(keys)]
    if any(s is None for s in found):
        return "not_checkable", []
    return None, found


@dataclass(frozen=True)
class Limit:
    min: float | None
    max: float | None
    unit: str | None
    reason: str | None
    standard_keys: tuple[str, ...]


def limit_for(turn, lot, facts: dict | None = None) -> Limit | None:
    """The bounds the lot drawing shows for a number turn (plan 4), from the same standards
    check_turn uses, or why there are none: never a number the districts don't agree on."""
    spec = turn.standard
    if spec is None:
        return None
    reason, found = _lookup(spec, lot, facts or {})
    if reason:
        return Limit(None, None, turn.unit, reason, ())
    keys = tuple(s.key for s in found)
    unit = next((s.unit for s in found if s.unit), turn.unit)
    if len({(s.min, s.max) for s in found}) > 1:
        return Limit(None, None, unit, "two_districts", keys)
    return Limit(found[0].min, found[0].max, unit, None, keys)


def check_turn(turn, facts: dict, lot, unsure=(), standard: dict | None = None) -> Check | None:
    """The check for a number turn (or the turn that completes a computed one), or None when the
    turn has no standard or its value isn't settled yet. `standard` overrides the turn's own, for
    the inputs of a computed value that carry none."""
    spec = standard or turn.standard
    if spec is None:
        return None
    if turn.computed == "stories":
        if not stories_settled(facts, unsure):
            return None
        if any(k in unsure for k in STORY_INPUTS):
            return _uncertain("unknown_input", unit="stories")
        value = counted_stories(facts)
    else:
        value = _get(facts, turn.fact)
        if value is None:
            return None
    reason, found = _lookup(spec, lot, facts)
    if reason:
        return _uncertain(reason, value)
    results = [check(s, value) for s in found]
    std_keys = tuple(s.key for s in found)
    unit = next((s.unit for s in found if s.unit), turn.unit)
    if all(r == "cannot_check" for r in results):
        # A checkable standard that still can't say: past its limit, within what the Board may allow.
        board = all(s.status == "checkable" and s.board_may_allow_to is not None for s in found)
        return _uncertain("board_decides" if board else "not_checkable", value, unit, std_keys)
    if len(set(results)) > 1:
        return _uncertain("two_districts" if len(found) > 1 else "not_checkable", value, unit, std_keys)
    if results[0] == "outside" and len({(s.min, s.max) for s in found}) > 1:
        # Every district says no, but by how much depends on which district the work is in.
        return _uncertain("two_districts", value, unit, std_keys)
    mins = [s.min for s in found if s.min is not None]
    maxes = [s.max for s in found if s.max is not None]
    lo, hi = (max(mins) if mins else None), (min(maxes) if maxes else None)
    if results[0] == "within":
        room = min(r for r in (None if lo is None else value - lo, None if hi is None else hi - value)
                   if r is not None)
        return Check("fits", value, lo, hi, unit, room, None, None, None, std_keys, ())
    if lo is not None and value < lo:
        gap, direction, bound = lo - value, "short", lo
    else:
        gap, direction, bound = value - hi, "over", hi
    nearest = ({"id": "nearest", "value": bound},) if turn.fact and not turn.computed else ()
    return Check("outside", value, lo, hi, unit, None, gap, direction, None, std_keys, nearest)
