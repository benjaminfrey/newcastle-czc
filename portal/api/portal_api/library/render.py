"""An entry, filled in for one district and building (design 2, §4).

Numbers come only from the standards (the pinned ruleset, merged with the chair's recorded
answers), never from the entry's text. A slot whose value the Code doesn't establish leaves the
entry unrendered, so the standard goes to the Town rather than showing a blank. A value that comes
from the chair's recorded answer carries its note, to be shown as the Town's interpretation
(decision 16).
"""

import string
from dataclasses import dataclass

from portal_api.standards import Standard, load_standards, standards_for

from .model import Library, LibraryEntry

PARTS = frozenset({"min", "max", "range", "raw"})
# How a range reads (part "range"): drafts for the chair, shown in each entry's memo.
RANGE = {"both": "between {lo} and {hi}", "min": "at least {lo}", "max": "at most {hi}"}
_UNITS = {"sf": "sq ft"}
_ONE = {"stories": "story", "units": "unit"}


def standard_key(s: Standard) -> str:
    """A standard as one entry explains it, whatever the district or building type."""
    return f"dimension:{s.field}" if s.source == "dimension" else f"building:{s.field}"


def all_keys() -> frozenset[str]:
    return frozenset(standard_key(s) for s in load_standards())


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def _shown(n: float) -> str:
    return f"{n:,.0f}" if n == int(n) else f"{n:g}"


def number(n: float, unit: str | None) -> str:
    unit = _ONE.get(unit, unit) if n == 1 else _UNITS.get(unit, unit)
    return f"{_shown(n)} {unit}" if unit else _shown(n)


def limit(s: Standard) -> str | None:
    if s.min is not None and s.max is not None:
        return RANGE["both"].format(lo=_shown(s.min), hi=number(s.max, s.unit))
    if s.min is not None:
        return RANGE["min"].format(lo=number(s.min, s.unit))
    if s.max is not None:
        return RANGE["max"].format(hi=number(s.max, s.unit))
    return None


def slot_keys(slot: dict) -> tuple[str, ...]:
    """A slot names one standard key, or the same standard under each name the districts use."""
    k = slot.get("standard")
    return tuple(k) if isinstance(k, list) else (k,)


@dataclass(frozen=True)
class Rendered:
    answer: str
    detail: str
    interpretations: tuple[str, ...]


def _find(key: str, district_key: str, building: str | None) -> Standard | None:
    for s in standards_for(district_key):
        if standard_key(s) == key and (s.source == "dimension" or s.building == building):
            return s
    return None


def render(e: LibraryEntry, district_key: str, building: str | None) -> Rendered | None:
    values, notes = {}, []
    for name, slot in e.slots.items():
        s = next((x for k in slot_keys(slot) if (x := _find(k, district_key, building)) is not None), None)
        if s is None:
            return None
        if slot["part"] == "raw":
            values[name] = s.raw
        elif slot["part"] == "range":
            if s.status != "checkable" or (shown := limit(s)) is None:
                return None
            values[name] = shown
        else:
            n = getattr(s, slot["part"])
            if s.status != "checkable" or n is None:
                return None
            values[name] = number(n, s.unit)
        if s.provenance == "override" and s.note and s.note not in notes:
            notes.append(s.note)
    detail = e.detail.format(**values)
    if district_key in e.district_notes:
        detail = f"{detail} {e.district_notes[district_key].format(**values)}"
    return Rendered(answer=e.answer.format(**values), detail=detail, interpretations=tuple(notes))


def entry_for(lib: Library, key: str) -> LibraryEntry | None:
    return next((e for e in lib.entries.values() if key in e.standards), None)


def spec_key(spec: dict) -> str:
    """A turn's standard ({source, field, building}) as a standard key."""
    return f"dimension:{spec['field']}" if spec["source"] == "dimension" else f"building:{spec['field']}"


def entry_for_spec(entries: dict[str, LibraryEntry], spec: dict | None) -> LibraryEntry | None:
    if spec is None:
        return None
    key = spec_key(spec)
    return next((e for e in entries.values() if key in e.standards), None)
