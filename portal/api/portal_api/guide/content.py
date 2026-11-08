"""The guide's words and questions (YAML in definitions/), validated on load.

Every word an applicant reads comes from these files, and every entry is a draft until the chair
approves it (spec §11). Loading checks what the forms' loader checks (status, citations,
conditions) and more: an answer may set only a fact the engine knows, a number question needs a
fact and bounds, and a template may fill only the slots listed here. Nothing a person types is
ever read by this package (spec decision 14).
"""

import dataclasses
import functools
import hashlib
import re
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from portal_api.forms.definitions import DefinitionError, _check_cite, _check_status, load_definitions
from portal_api.forms.expr import validate as validate_condition
from portal_api.forms.parts import load_parts
from portal_api.library import LibraryEntry, LibraryError, is_live, load_library, view
from portal_api.library.model import NEVER_WORDS  # noqa: F401 (re-exported: the guide's tests and endings use it)
from portal_api.ruleset import load_ruleset

DIR = Path(__file__).resolve().parent / "definitions"
_FILES = ("openings.yaml", "turns.yaml", "wording.yaml")  # the entries are the library's (design 2)

# The facts the engine knows. An answer may set only these; `opening` and `confirmed` are set by
# the engine and the "So you mean…" answers.
FACTS = frozenset({
    "opening", "confirmed", "lot.confirmed", "lot.has_outline", "lot.corner", "lot.front",
    "building.full_stories", "building.roof_floors", "building.top_knee_over_3ft",
    "building.basement_exposed_5ft", "building.floor_area_sf", "building.dwelling_units",
    "building.setback.front", "building.setback.side_1", "building.setback.side_2",
    "building.setback.rear", "building.setback.secondary", "use.group", "use.use_key",
})
TEMPLATE_SLOTS = frozenset({"opening", "map_lot", "districts"})
# Number templates checks.py fills with numbers and units only.
_NUMBER_SLOTS = {"nearest": {"value", "unit"}, "doesnt_fit": {"gap", "unit", "direction"}, "front_along": {"street"}, "front_along_length": {"street", "n"}, "front_primary": {"street"}}
_ANSWERS_FROM = {"use_groups", "use_group_uses", "lot_lines"}
_DRAWINGS = {"front", "front_setback", "side_1", "side_2", "secondary", "rear"}
_KINDS = {"lot", "confirm", "choice", "number"}



class ContentError(Exception):
    pass


@dataclass(frozen=True)
class Answer:
    id: str
    label: str
    hint: str | None
    set: dict


# An entry is the library's (design 2); the guide keeps the name.
Entry = LibraryEntry


@dataclass(frozen=True)
class Turn:
    id: str
    order: int
    step: str
    kind: Literal["lot", "confirm", "choice", "number"]
    ask: str
    status: str
    when: dict | None = None
    help: str | None = None
    answers: tuple[Answer, ...] = ()
    answers_from: str | None = None
    fact: str | None = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    standard: dict | None = None
    computed: str | None = None
    answer_field: str | None = None
    why: str | None = None
    defines: tuple[str, ...] = ()
    cite: str | None = None
    approved_by: str | None = None
    approved_on: str | None = None
    drawing: str | None = None      # the part of the lot drawing this turn asks about (plan 4)


@dataclass(frozen=True)
class Opening:
    id: str
    label: str
    picture: str          # the spot's id in the opening scene (plan 5)
    guided: bool          # False: the spot says "coming soon" until its conversation is built
    status: str
    part: str | None = None
    facts: dict | None = None
    screener: dict | None = None
    confirm: str | None = None
    approved_by: str | None = None
    approved_on: str | None = None


@dataclass(frozen=True)
class Content:
    openings: dict
    turns: tuple
    entries: dict
    wording: dict
    use_answers: dict      # use group key -> its uses as answers (approved content, Code names)
    group_answers: tuple   # the use groups as answers
    digest: str
    covers_standards: bool = False   # this request's view (library/view.py)

    def turn(self, turn_id: str) -> Turn | None:
        return next((t for t in self.turns if t.id == turn_id), None)


def _status(where: str, e: dict) -> None:
    try:
        _check_status(where, e)
    except DefinitionError as exc:
        raise ContentError(str(exc)) from None


def _cite(where: str, ref: str, ruleset) -> None:
    try:
        _check_cite(where, ref, ruleset)
    except DefinitionError as exc:
        raise ContentError(str(exc)) from None


def _slots(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def _answers(where: str, raw: list) -> tuple[Answer, ...]:
    out, seen = [], set()
    for a in raw:
        if not a.get("id") or a["id"] in seen or a["id"] == "unsure":
            raise ContentError(f"{where}: answer ids must be present, unique and not 'unsure'")
        seen.add(a["id"])
        for path in a.get("set") or {}:
            if path not in FACTS:
                raise ContentError(f"{where}: answer {a['id']!r} sets {path!r}, which is not a known fact")
        out.append(Answer(str(a["id"]), a["label"], a.get("hint"), dict(a.get("set") or {})))
    return tuple(out)


def _turn(t: dict, entries: dict, ruleset) -> Turn:
    where = f"turns.yaml: {t.get('id')}"
    _status(where, t)
    if t.get("kind") not in _KINDS:
        raise ContentError(f"{where}: kind must be one of {sorted(_KINDS)}")
    if t.get("when") is not None:
        try:
            validate_condition(t["when"])
        except ValueError as exc:
            raise ContentError(f"{where}: {exc}") from None
    if t.get("cite"):
        _cite(where, t["cite"], ruleset)
    for key in [t.get("why"), *(t.get("defines") or [])]:
        if key is not None and key not in entries:
            raise ContentError(f"{where}: no entry {key!r}")
    if t["kind"] == "number":
        for k in ("fact", "min", "max"):
            if t.get(k) is None:
                raise ContentError(f"{where}: a number question needs {k}")
        if t["fact"] not in FACTS:
            raise ContentError(f"{where}: fact {t['fact']!r} is not a known fact")
        if t["min"] > t["max"]:
            raise ContentError(f"{where}: min is above max")
    if t.get("answers_from") is not None and t["answers_from"] not in _ANSWERS_FROM:
        raise ContentError(f"{where}: answers_from must be one of {sorted(_ANSWERS_FROM)}")
    if t.get("drawing") is not None and t["drawing"] not in _DRAWINGS:
        raise ContentError(f"{where}: drawing must be one of {sorted(_DRAWINGS)}")
    if t["kind"] in ("lot", "confirm") or (t["kind"] == "choice" and not t.get("answers_from")):
        if not t.get("answers"):
            raise ContentError(f"{where}: needs answers")
    keep = {k: v for k, v in t.items() if k in Turn.__dataclass_fields__}
    keep["answers"] = _answers(where, t.get("answers") or [])
    keep["defines"] = tuple(t.get("defines") or ())
    return Turn(**keep)


def _use_answers(ruleset) -> tuple[tuple[Answer, ...], dict]:
    """The use groups and their uses as answers: the approved groups' plain names and examples,
    and each use under its Code name (use-groups.yaml; not retyped here)."""
    names = {u["use_key"]: u["label"] for u in ruleset.uses}
    defs = load_definitions(ruleset)
    groups = tuple(Answer(g.key, g.plain, None, {"use.group": g.key}) for g in defs.groups)
    uses = {g.key: tuple(Answer(u.use_key, names[u.use_key], u.example, {"use.use_key": u.use_key}) for u in g.uses)
            for g in defs.groups}
    return groups, uses


@functools.cache
def _load(root: Path, library_root: Path | None) -> Content:
    ruleset = load_ruleset()
    raw = {name: yaml.safe_load((root / name).read_text()) for name in _FILES}
    try:
        library = load_library(library_root)
    except LibraryError as exc:
        raise ContentError(f"library: {exc}") from None
    digest = hashlib.sha256(b"".join((root / name).read_bytes() for name in _FILES)
                            + library.digest.encode()).hexdigest()
    entries = library.entries

    wording = raw["wording.yaml"]
    for key, w in wording.items():
        _status(f"wording.yaml: {key}", w)
        if "text" in w:
            allowed = _NUMBER_SLOTS.get(key, TEMPLATE_SLOTS)
            extra = _slots(w["text"]) - allowed
            if extra:
                raise ContentError(f"wording.yaml: {key}: unknown slot {', '.join(sorted(extra))}")

    part_ids = set(load_parts().ids)
    openings = {}
    for o in raw["openings.yaml"]:
        where = f"openings.yaml: {o.get('id')}"
        _status(where, o)
        if not isinstance(o.get("guided"), bool):
            raise ContentError(f"{where}: guided must be true or false")
        if o["guided"]:
            if o.get("part") not in part_ids:
                raise ContentError(f"{where}: no part {o.get('part')!r}")
            if o.get("confirm") not in wording:
                raise ContentError(f"{where}: no template {o.get('confirm')!r}")
        openings[o["id"]] = Opening(**{k: v for k, v in o.items() if k in Opening.__dataclass_fields__})

    turns, seen = [], set()
    for t in raw["turns.yaml"]:
        if t.get("id") in seen:
            raise ContentError(f"turns.yaml: {t.get('id')}: duplicate id")
        seen.add(t.get("id"))
        turns.append(_turn(t, entries, ruleset))
    groups, uses = _use_answers(ruleset)
    return Content(openings=openings, turns=tuple(sorted(turns, key=lambda t: t.order)), entries=entries,
                   wording=wording, use_answers=uses, group_answers=groups, digest=digest)


def load_content(root: Path | None = None, library_root: Path | None = None) -> Content:
    """The guide's content, with only the entries this request's view may show."""
    c = _load((root or DIR).resolve(), library_root.resolve() if library_root else None)
    v = view.current()
    entries = {k: e for k, e in c.entries.items() if view.visible(e, public=v.public, pulled=v.pulled)}
    return dataclasses.replace(c, entries=entries, covers_standards=v.covers_standards)


def drafts_in(content: Content, *, opening: str, turn_ids: list[str], entry_ids: list[str],
              wording_keys: list[str]) -> list[str]:
    """Every draft a state shows, as "file: id", in a stable order."""
    out = []
    o = content.openings.get(opening)
    if o is not None and o.status == "draft":
        out.append(f"openings.yaml: {opening}")
    for t in dict.fromkeys(turn_ids):
        turn = content.turn(t)
        if turn is not None and turn.status == "draft":
            out.append(f"turns.yaml: {t}")
    for e in dict.fromkeys(entry_ids):
        if e in content.entries and not is_live(content.entries[e]):
            out.append(f"library/{content.entries[e].batch}: {e}")
    for w in dict.fromkeys(wording_keys):
        if w in content.wording and content.wording[w].get("status") == "draft":
            out.append(f"wording.yaml: {w}")
    return out
