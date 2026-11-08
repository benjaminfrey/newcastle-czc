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

PARTS = frozenset({"min", "max", "raw"})
_UNITS = {"sf": "sq ft"}
_ONE = {"stories": "story", "units": "unit"}


def standard_key(s: Standard) -> str:
    """A standard as one entry explains it, whatever the district or building type."""
    return f"dimension:{s.field}" if s.source == "dimension" else f"building:{s.field}"


def all_keys() -> frozenset[str]:
    return frozenset(standard_key(s) for s in load_standards())


def placeholders(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def number(n: float, unit: str | None) -> str:
    unit = _ONE.get(unit, unit) if n == 1 else _UNITS.get(unit, unit)
    shown = f"{n:,.0f}" if n == int(n) else f"{n:g}"
    return f"{shown} {unit}" if unit else shown


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
        s = _find(slot["standard"], district_key, building)
        if s is None:
            return None
        if slot["part"] == "raw":
            values[name] = s.raw
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
