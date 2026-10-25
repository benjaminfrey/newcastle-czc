"""Application forms as data: one YAML file per form and version in definitions/forms/.

A form is the official form's sections and fields. Each field says where its value
comes from (`source`): a plain question in the wizard, the property snapshot, the
signed-in account, another field, the signature at submit, or staff. Questions carry
the condition (`show_if`) that decides whether they are asked, in the language of
expr.py. Everything is validated on load; entries start as drafts the chair approves.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from portal_api.forms.definitions import DefinitionError, DraftEntry, _check_cite, _check_status
from portal_api.forms.expr import validate as validate_condition
from portal_api.ruleset import PINNED_KEY, Ruleset

DIR = Path(__file__).resolve().parent / "definitions" / "forms"
FORM_KEYS = ("use_permit", "small_project_plan", "entrance_permit")
FIELD_TYPES = {"text", "longtext", "number", "choice", "multichoice", "yesno", "date", "uses", "point", "upload"}
SOURCES = {"question", "property", "account", "derived", "at_submit", "staff"}
PROPERTY_KEYS = {"map_lot", "location", "acres", "districts", "streets", "on_state_highway"}
ACCOUNT_KEYS = {"email"}
SCOPES = ("answers.", "item.", "property.")
# How a question is drawn (the browser picks a default by type when none is named).
# Each control and the field types it can answer: a switch on a number would be refused at every save.
CONTROL_TYPES = {"stepper": {"number"}, "slider": {"number"}, "switch": {"yesno"}, "segmented": {"choice", "yesno"},
                 "tiles": {"choice"}, "picker": {"choice"}, "chips": {"multichoice"}, "building-picker": {"text"},
                 "street-picker": {"text"}, "building-type": {"choice"}}
CONTROLS = set(CONTROL_TYPES)
AUTOCOMPLETE = {"name", "tel", "email", "street-address"}
LAYOUTS = {"compass", "lot-diagram"}
# The outline icons an option may name: the vocabulary the web's Icon map draws.
ICONS = frozenset(line.strip() for line in (Path(__file__).parent / "icons.txt").read_text().splitlines()
                  if line.strip() and not line.startswith("#"))


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    official: str
    icon: str | None = None  # an outline icon beside the tile's words (ICONS)


@dataclass(frozen=True)
class Repeat:
    kind: str
    add_label: str
    min: int
    max: int


@dataclass(frozen=True)
class Step:
    id: str
    title: str


@dataclass(frozen=True)
class Screen:
    """Fields asked together on one screen of the wizard (deed book and page; the four setbacks),
    with the drawing they sit around, if any."""
    id: str
    layout: str | None = None


@dataclass(frozen=True)
class Field:
    id: str
    official_label: str
    source: str
    file: str
    status: str
    from_: str | None = None
    may_correct: bool = False
    label: str | None = None
    help: str | None = None
    why: str | None = None
    type: str | None = None
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    options: tuple = ()
    required: bool = False
    allow_unknown: bool = False
    show_if: dict | None = None
    compare: str | None = None
    approved_by: str | None = None
    approved_on: str | None = None
    step: str | None = None
    screen: str | None = None
    ask_first: int = 0  # asked before the rest of its item, lowest rank first; print order is unchanged
    control: str | None = None
    step_size: float | None = None
    default: object = None
    autocomplete: str | None = None
    copies: bool = False  # "Copy Building 1" brings this answer to the new item

    @property
    def is_question(self) -> bool:
        """Asked in the wizard: a question, or a property value the applicant may correct."""
        return self.source == "question" or self.may_correct


@dataclass(frozen=True)
class Section:
    id: str
    official_title: str
    chapter: str
    fields: tuple
    file: str
    status: str
    repeat: Repeat | None = None
    show_if: dict | None = None
    approved_by: str | None = None
    approved_on: str | None = None
    step: str | None = None
    screens: tuple = ()


@dataclass(frozen=True)
class FormDef:
    key: str
    version: int
    ruleset_key: str
    official_title: str
    sections: tuple
    steps: tuple = ()

    def step_of(self, field_id: str) -> str | None:
        """The step a field is asked in: its own, else its section's."""
        s, f = self.field(field_id)
        return f.step or s.step

    def fields(self):
        for s in self.sections:
            for f in s.fields:
                yield s, f

    def field(self, field_id: str) -> tuple["Section", Field]:
        for s, f in self.fields():
            if f.id == field_id:
                return s, f
        raise KeyError(field_id)

    def screen_layout(self, field_id: str) -> str | None:
        """The drawing a field's card sits around, wherever in its repeat the card is declared."""
        s, f = self.field(field_id)
        kind = s.repeat.kind if s.repeat else None
        for x in self.sections:
            if (x.repeat.kind if x.repeat else None) == kind:
                for sc in x.screens:
                    if sc.id == f.screen:
                        return sc.layout
        return None


def file_name(key: str, version: int) -> str:
    return f"{key.replace('_', '-')}.v{version}.yaml"


def _paths(expr) -> list[str]:
    (op, arg), = expr.items()
    if op in ("all", "any"):
        return [p for e in arg for p in _paths(e)]
    if op == "not":
        return _paths(arg)
    return [arg] if op == "known" else [arg[0]]


def _check_show_if(where: str, cond) -> None:
    if cond is None:
        return
    try:
        validate_condition(cond)
    except ValueError as exc:
        raise DefinitionError(f"{where}: {exc}") from None
    for p in _paths(cond):
        if not p.startswith(SCOPES):
            raise DefinitionError(f"{where}: condition path {p!r} must start with answers., item. or property.")


def _field(file: str, sec_id: str, f: dict, ruleset: Ruleset) -> Field:
    where = f"{file}: {f.get('id')}"
    _check_status(where, f)
    if f.get("source") not in SOURCES:
        raise DefinitionError(f"{where}: unknown source {f.get('source')!r}")
    if f["source"] in ("property", "derived", "account") and not f.get("from"):
        raise DefinitionError(f"{where}: a {f['source']} field needs from")
    if f["source"] == "property" and f["from"] not in PROPERTY_KEYS:
        raise DefinitionError(f"{where}: from {f['from']!r} is not a property fact")
    if f["source"] == "account" and f["from"] not in ACCOUNT_KEYS:
        raise DefinitionError(f"{where}: from {f['from']!r} is not an account fact")
    asked = f["source"] == "question" or f.get("may_correct")
    if asked:
        if not f.get("label"):
            raise DefinitionError(f"{where}: a question needs a label")
        if f.get("type") not in FIELD_TYPES:
            raise DefinitionError(f"{where}: unknown type {f.get('type')!r}")
        if f["type"] in ("choice", "multichoice"):
            opts = f.get("options") or []
            if not opts:
                raise DefinitionError(f"{where}: a {f['type']} needs options")
            values = [o.get("value") for o in opts]
            if len(set(values)) != len(values) or not all(o.get("label") and o.get("official") for o in opts):
                raise DefinitionError(f"{where}: option values must be unique, each with a label and official name")
            icons = [o.get("icon") for o in opts]
            if any(icons) and not all(icons):
                raise DefinitionError(f"{where}: give every option an icon, or none")
            for i in icons:
                if i is not None and i not in ICONS:
                    raise DefinitionError(f"{where}: unknown icon {i!r} (portal_api/forms/icons.txt)")
        if f.get("min") is not None and f.get("max") is not None and f["min"] > f["max"]:
            raise DefinitionError(f"{where}: min is above max")
        if f["type"] == "upload" and f.get("required"):
            raise DefinitionError(f"{where}: an upload is never required")
        if f.get("why") is None:
            raise DefinitionError(f"{where}: a question needs why (a Code citation)")
    if f.get("why") is not None:
        _check_cite(where, f["why"], ruleset)
    _check_show_if(where, f.get("show_if"))
    if f.get("control") is not None and f["control"] not in CONTROLS:
        raise DefinitionError(f"{where}: unknown control {f['control']!r}")
    if f.get("control") is not None and f.get("type") not in CONTROL_TYPES[f["control"]]:
        raise DefinitionError(f"{where}: a {f['control']} can't answer a {f.get('type')} question")
    if f.get("autocomplete") is not None and f["autocomplete"] not in AUTOCOMPLETE:
        raise DefinitionError(f"{where}: unknown autocomplete {f['autocomplete']!r}")
    if "default" in f and not asked:
        raise DefinitionError(f"{where}: only a question can have a default")
    rank = f.get("ask_first") or 0
    if rank is True:
        rank = 1
    if not isinstance(rank, int) or rank < 0:
        raise DefinitionError(f"{where}: ask_first is true or a rank (1, 2, …)")
    return Field(
        id=f["id"], official_label=f["official_label"], source=f["source"], file=file, status=f["status"],
        from_=f.get("from"), may_correct=bool(f.get("may_correct")), label=f.get("label"), help=f.get("help"),
        why=f.get("why"), type=f.get("type"), unit=f.get("unit"), min=f.get("min"), max=f.get("max"),
        options=tuple(Option(o["value"], o["label"], o["official"], o.get("icon")) for o in f.get("options") or ()),
        required=bool(f.get("required")), allow_unknown=bool(f.get("allow_unknown")), show_if=f.get("show_if"),
        compare=f.get("compare"), approved_by=f.get("approved_by"), approved_on=f.get("approved_on"),
        step=f.get("step"), screen=f.get("screen"), ask_first=rank, control=f.get("control"), step_size=f.get("step_size"),
        default=f.get("default"), autocomplete=f.get("autocomplete"), copies=bool(f.get("copies")),
    )


def _sections(file: str, doc: dict, ruleset: Ruleset) -> list[Section]:
    if doc.get("ruleset_key") != PINNED_KEY or doc.get("ruleset_key") != ruleset.key:
        raise DefinitionError(f"{file}: written for ruleset {doc.get('ruleset_key')!r}, not {ruleset.key!r}")
    out = []
    for s in doc.get("sections") or []:
        where = f"{file}: {s.get('id')}"
        _check_status(where, s)
        _check_show_if(where, s.get("show_if"))
        # The sheets' pages and "Add a building" presets gave way to one question per screen.
        if "pages" in s:
            raise DefinitionError(f"{where}: pages are gone; group fields with screens")
        if any("page" in f for f in s.get("fields") or ()):
            raise DefinitionError(f"{where}: a field's page is gone; use screen")
        rep = s.get("repeat")
        repeat = None
        if rep is not None:
            if "add_options" in rep:
                raise DefinitionError(f"{where}: add_options are gone; a building's type is its first question")
            try:
                repeat = Repeat(rep["kind"], rep["add_label"], int(rep["min"]), int(rep["max"]))
            except (KeyError, TypeError, ValueError):
                raise DefinitionError(f"{where}: repeat needs kind, add_label, min and max") from None
            if not 0 <= repeat.min <= repeat.max or repeat.max < 1:
                raise DefinitionError(f"{where}: repeat min must be between 0 and max")
        screens = []
        for sc in s.get("screens") or ():
            if not isinstance(sc, dict) or not sc.get("id"):
                raise DefinitionError(f"{where}: each screen needs an id")
            if sc.get("layout") is not None and sc["layout"] not in LAYOUTS:
                raise DefinitionError(f"{where}: unknown layout {sc['layout']!r}")
            screens.append(Screen(sc["id"], sc.get("layout")))
        fields = tuple(_field(file, s["id"], f, ruleset) for f in s.get("fields") or ())
        for f in fields:
            if f.copies and repeat is None:
                raise DefinitionError(f"{file}: {f.id}: copies is only for a building's or an addition's questions")
        out.append(Section(
            id=s["id"], official_title=s["official_title"], chapter=s["chapter"], file=file, status=s["status"],
            fields=fields,
            repeat=repeat, show_if=s.get("show_if"), approved_by=s.get("approved_by"), approved_on=s.get("approved_on"),
            step=s.get("step"), screens=tuple(screens),
        ))
    return out


def _steps(file: str, doc: dict) -> list[Step]:
    out = []
    for st in doc.get("steps") or ():
        if not isinstance(st, dict) or not st.get("id") or not st.get("title"):
            raise DefinitionError(f"{file}: each step needs an id and a title")
        out.append(Step(st["id"], st["title"]))
    return out


def _read(root: Path, name: str) -> dict:
    path = root / name
    if not path.exists():
        raise DefinitionError(f"no form file {name}")
    return yaml.safe_load(path.read_text()) or {}


def _load(key: str, version: int, ruleset: Ruleset, root: Path) -> FormDef:
    name = file_name(key, version)
    doc = _read(root, name)
    if doc.get("key") != key or doc.get("version") != version:
        raise DefinitionError(f"{name}: says it is {doc.get('key')!r} v{doc.get('version')!r}")
    sections, steps = [], []
    for inc in doc.get("include") or []:
        inc_doc = _read(root, f"{inc}.yaml")
        sections += _sections(f"{inc}.yaml", inc_doc, ruleset)
        steps += _steps(f"{inc}.yaml", inc_doc)
    sections += _sections(name, doc, ruleset)
    steps += _steps(name, doc)
    ids = [s.id for s in sections] + [f.id for s in sections for f in s.fields]
    seen = set()
    for i in ids:
        if i in seen:
            raise DefinitionError(f"{name}: {i}: duplicate id")
        seen.add(i)
    field_ids = {f.id for s in sections for f in s.fields}
    for s in sections:
        for f in s.fields:
            if f.source == "derived" and f.from_ not in field_ids and f.from_ not in PROPERTY_KEYS | ACCOUNT_KEYS:
                raise DefinitionError(f"{f.file}: {f.id}: from {f.from_!r} names no field")
    _check_steps(name, sections, steps)
    form = FormDef(key=key, version=version, ruleset_key=doc["ruleset_key"],
                   official_title=doc["official_title"], sections=tuple(sections), steps=tuple(steps))
    _check_defaults(form)
    return form


def _check_steps(name: str, sections: list, steps: list) -> None:
    """A form that declares steps places every question in one. A field's screen (its card) is
    declared once for its repeat (or once outside repeats), by any section; a card's questions
    share one step."""
    step_ids = [st.id for st in steps]
    if len(set(step_ids)) != len(step_ids):
        raise DefinitionError(f"{name}: duplicate step id")
    kind_of = lambda s: s.repeat.kind if s.repeat else None
    declared: set[tuple] = set()
    for s in sections:
        for x in s.screens:
            if (kind_of(s), x.id) in declared:
                raise DefinitionError(f"{name}: {s.id}: duplicate screen {x.id!r}")
            declared.add((kind_of(s), x.id))
    card_step: dict[tuple, str | None] = {}
    for s in sections:
        for f in s.fields:
            where = f"{f.file}: {f.id}"
            step = f.step or s.step
            if step is not None and step not in step_ids:
                raise DefinitionError(f"{where}: step {step!r} is not declared")
            if steps and f.is_question and step is None:
                raise DefinitionError(f"{where}: a question needs a step")
            if f.screen is not None:
                key = (kind_of(s), f.screen)
                if key not in declared:
                    raise DefinitionError(f"{where}: screen {f.screen!r} is not declared for this repeat ({key[0] or 'none'})")
                if key in card_step and card_step[key] != step:
                    raise DefinitionError(f"{where}: screen {f.screen!r} has questions in two steps")
                card_step[key] = step


def _check_defaults(form: FormDef) -> None:
    from portal_api.forms.answers import AnswerError, check_value  # answers imports this module

    for s, f in form.fields():
        if f.default is not None:
            try:
                check_value(f, f.default)
            except AnswerError as e:
                raise DefinitionError(f"{f.file}: {f.id}: bad default ({e.reason})") from None


_CACHE: dict[tuple, FormDef] = {}


def load_form(key: str, version: int, ruleset: Ruleset, root: Path | None = None) -> FormDef:
    root = (root or DIR).resolve()
    k = (key, version, ruleset.key, root)
    if k not in _CACHE or root != DIR.resolve():
        _CACHE[k] = _load(key, version, ruleset, root)
    return _CACHE[k]


def latest_version(key: str, root: Path | None = None) -> int:
    pattern = re.compile(re.escape(key.replace("_", "-")) + r"\.v(\d+)\.yaml$")
    versions = [int(m.group(1)) for p in (root or DIR).iterdir() if (m := pattern.match(p.name))]
    if not versions:
        raise DefinitionError(f"no form {key!r}")
    return max(versions)


def form_drafts(form: FormDef) -> list[DraftEntry]:
    out = []
    for s in form.sections:
        if s.status == "draft":
            out.append(DraftEntry(s.file, s.id))
        out += [DraftEntry(f.file, f.id) for f in s.fields if f.status == "draft"]
    return out
