"""The parts a project is made of (definitions/parts.yaml; projects brief §4), and the form a
project fills: the cover sheet, the sections its parts ask, and the project's own questions,
from the official forms it has pinned. Each part's questions are one dashboard row (a step).

Two answers are worked out from the parts, never typed: the Small Project Plan's "Type of
project" (`work_kinds`, brief §4) and the homes in the project's new buildings
(`new_homes_total`, which decides whether the five-year homes question is asked). The browser
works them out the same way (web/src/forms/derived.ts).
"""

import dataclasses
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

from portal_api.forms.definitions import DefinitionError, _check_status
from portal_api.forms.formdefs import FormDef, Repeat, Section, Step, latest_version, load_form
from portal_api.ruleset import Ruleset

FILE = Path(__file__).parent / "definitions" / "parts.yaml"
COVER = "cover_sheet"
QUESTIONS = "project_questions"  # asked, never printed


@dataclass(frozen=True)
class PartDef:
    id: str
    label: str
    step: str
    icon: str
    sections: tuple  # ((form_key, section_id), ...)
    rule: dict
    inputs: dict
    status: str
    repeats: bool = False
    repeat_of: str | None = None  # the form's repeat kind its sections walk (an addition walks "component")
    work_kind: str | None = None
    approved_by: str | None = None
    approved_on: str | None = None


@dataclass(frozen=True)
class ProjectSection:
    form_key: str
    section_id: str
    when_any: tuple


@dataclass(frozen=True)
class PartsDef:
    parts: tuple
    project_step: Step
    project_sections: tuple
    project_inputs: dict
    project_status: str
    project_approved_by: str | None = None
    project_approved_on: str | None = None

    def get(self, kind: str) -> PartDef | None:
        return next((p for p in self.parts if p.id == kind), None)

    @property
    def ids(self) -> list[str]:
        return [p.id for p in self.parts]


def _ref(s: str) -> tuple[str, str]:
    form_key, _, section_id = s.partition(":")
    if not section_id:
        raise DefinitionError(f"parts.yaml: {s!r} is not form_key:section_id")
    return form_key, section_id


@cache
def load_parts(path: Path = FILE) -> PartsDef:
    doc = yaml.safe_load(path.read_text())
    parts = []
    for p in doc["parts"]:
        _check_status(f"parts.yaml: {p.get('id')}", p)
        parts.append(PartDef(
            id=p["id"], label=p["label"], step=p["step"], icon=p["icon"],
            sections=tuple(_ref(s) for s in p["sections"]), rule=dict(p["rule"]), inputs=dict(p.get("inputs") or {}),
            status=p["status"], repeats=bool(p.get("repeats")), repeat_of=p.get("repeat_of"), work_kind=p.get("work_kind"),
            approved_by=p.get("approved_by"), approved_on=p.get("approved_on")))
    proj = doc["project"]
    _check_status("parts.yaml: project", proj)
    return PartsDef(
        parts=tuple(parts), project_step=Step(proj["step"]["id"], proj["step"]["title"]),
        project_sections=tuple(ProjectSection(*_ref(s["section"]), tuple(s["when_any"])) for s in proj["sections"]),
        project_inputs=dict(proj.get("inputs") or {}), project_status=proj["status"],
        project_approved_by=proj.get("approved_by"), project_approved_on=proj.get("approved_on"))


def wanted_forms(kinds: list[str], parts: PartsDef) -> dict[str, int]:
    """The forms a project with these parts fills (with the questions-only form), each at its
    latest version: the version a form is pinned at when it first applies."""
    keys = {fk for k in set(kinds) if (p := parts.get(k)) for fk, _ in p.sections}
    keys |= {ps.form_key for ps in parts.project_sections if set(ps.when_any) & set(kinds)}
    keys.add(COVER)  # every project has a lot and an applicant
    return {k: latest_version(k) for k in sorted(keys)}


def _forms(pinned: dict[str, int], ruleset: Ruleset) -> dict[str, FormDef]:
    return {k: load_form(k, v, ruleset) for k, v in pinned.items()}


def project_form(pinned: dict[str, int], kinds: list[str], ruleset: Ruleset, parts: PartsDef | None = None) -> FormDef:
    """One form for the project: the cover sheet (Your lot, About you), "About the work", then a
    step per part present (in tile order), then what only prints (headers, signatures, office
    use). A repeating part's sections walk items of the part's own kind."""
    parts = parts or load_parts()
    forms = _forms(pinned, ruleset)
    present = [p for p in parts.parts if p.id in set(kinds)]
    by_ref: dict[tuple, Section] = {}
    cover: list[Section] = []
    for key, form in forms.items():
        for s in form.sections:
            ref = (COVER if s.file.startswith("cover-sheet") else key, s.id)
            by_ref.setdefault(ref, s)
            if ref[0] == COVER and s not in cover:
                cover.append(s)
    used: set[tuple] = set()

    def place(ref: tuple, step: str | None, repeat_kind: str | None = None) -> Section | None:
        s = by_ref.get(ref)
        if s is None or ref in used:
            return None
        used.add(ref)
        repeat = None if s.repeat is None else dataclasses.replace(s.repeat, kind=repeat_kind or s.repeat.kind)
        return dataclasses.replace(s, step=step, repeat=repeat,
                                   fields=tuple(dataclasses.replace(f, step=None) for f in s.fields))

    sections, steps = [], []
    cover_steps = [st for f in forms.values() for st in f.steps if st.id in ("your_lot", "about_you")]
    for st in cover_steps:
        if st not in steps:
            steps.append(st)
    sections += [dataclasses.replace(s, fields=tuple(dataclasses.replace(f, step=None) for f in s.fields))
                 for s in cover if s.step is not None]
    used |= {(COVER, s.id) for s in cover if s.step is not None}
    work = [x for ps in parts.project_sections if set(ps.when_any) & set(kinds)
            if (x := place((ps.form_key, ps.section_id), parts.project_step.id))]
    if work:
        steps.append(parts.project_step)
        sections += work
    for p in present:
        placed = [x for ref in p.sections if (x := place(ref, p.id, p.id if p.repeats else None))]
        if placed:
            steps.append(Step(p.id, p.step))
            sections += placed
    # What only prints: the cover sheet's and each form's sections that ask nothing here.
    for key, form in forms.items():
        if key == QUESTIONS:
            continue
        for s in form.sections:
            ref = (COVER if s.file.startswith("cover-sheet") else key, s.id)
            if ref in used or s.repeat is not None or any(f.is_question for f in s.fields):
                continue
            used.add(ref)
            sections.append(s)
    return FormDef(key="project", version=1, ruleset_key=ruleset.key, official_title="Project",
                   sections=tuple(sections), steps=tuple(steps))


def printed_forms(pinned: dict[str, int], ruleset: Ruleset) -> dict[str, FormDef]:
    """The official forms the project prints (Milestone 5): every pinned form but the questions-only one."""
    return {k: f for k, f in _forms(pinned, ruleset).items() if k != QUESTIONS}


def derived(part_rows: list[dict], answers: dict, parts: PartsDef | None = None) -> dict:
    """The answers worked out from the parts: (field_id, None) -> value."""
    parts = parts or load_parts()
    kinds = {r["kind"] for r in part_rows}
    work = [p.work_kind for p in parts.parts if p.work_kind and p.id in kinds]
    homes = 0.0
    for r in part_rows:
        if r["kind"] == "building":
            v = answers.get(("dwelling_units", r["id"]))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                homes += v
    return {("work_kinds", None): work, ("new_homes_total", None): homes}
