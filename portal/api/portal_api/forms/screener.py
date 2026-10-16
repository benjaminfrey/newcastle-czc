"""The "Do I need a permit?" screener: rules + the adopted use table -> outcomes.

It never decides anything. Each outcome says what the Code calls for, who reviews
it, how long the Code gives them (only where clocks.json says so) and why, quoting
the Code. drafts_used lists every draft entry an answer rests on; the API refuses
to show such an answer to applicants unless drafts are allowed (development).
"""

from typing import Literal

from pydantic import BaseModel, Field

from portal_api.forms.definitions import Definitions
from portal_api.forms.expr import evaluate
from portal_api.gis.sources import _district_name
from portal_api.ruleset import Ruleset, district_key_for

APP_FOR_CODE = {"u": "use_permit", "rc": "residential_companion", "ex": "expanded_use", "sp": "special_permit"}


class PropertyAnswer(BaseModel):
    district_codes: list[str] = Field(default_factory=list, max_length=20)
    on_state_highway: bool | None = None
    civic: bool = False


class BuildingAnswer(BaseModel):
    kind: Literal["new", "addition", "renovation"] | None = None
    gross_floor_area_sf: float | None = Field(default=None, ge=0, le=10_000_000)
    dwelling_units: int | None = Field(default=None, ge=0, le=10_000)


class DivisionAnswer(BaseModel):
    lots_after: int | None = Field(default=None, ge=1, le=10_000)


class Answers(BaseModel):
    project: list[Literal["build", "use", "driveway", "divide", "other"]] = Field(min_length=1, max_length=5)
    property: PropertyAnswer = Field(default_factory=PropertyAnswer)
    use_key: str | None = Field(default=None, max_length=80)
    building: BuildingAnswer = Field(default_factory=BuildingAnswer)
    division: DivisionAnswer = Field(default_factory=DivisionAnswer)


def _days(app, ruleset: Ruleset) -> list[dict]:
    out = []
    for k in app.clock_keys:
        c = ruleset.clocks[k]
        cit = c["citation"]
        out.append({"label": c["label"], "days": c["days"], "basis": c["basis"],
                    "cite": f"{cit['article']}.{cit['section']}.{cit['subsection']}"})
    return out


def run(answers: dict, ruleset: Ruleset, defs: Definitions) -> dict:
    outcomes: dict[tuple, dict] = {}
    notes, not_listed, drafts = [], [], []
    town_only = False

    def draft(file, ident, status):
        if status == "draft" and (file, ident) not in drafts:
            drafts.append((file, ident))

    def add_app(key, district, certainty):
        app = defs.applications[key]
        draft("applications.yaml", key, app.status)
        outcomes.setdefault((key, district), {
            "application": key, "code_name": app.code_name, "plain": app.plain, "reviewer": app.reviewer,
            "certainty": certainty, "district": district,
            "district_name": (_district_name(district, ruleset.districts) or district) if district else None,
            "in_portal": app.in_portal,
            "days": _days(app, ruleset), "why": {"cite": app.cite, "text": ruleset.cite(app.cite)},
        })

    if answers.get("use_key"):
        for g in defs.groups:
            for u in g.uses:
                if u.use_key == answers["use_key"]:
                    draft("use-groups.yaml", u.use_key, u.status)

    for rule in defs.rules:
        if evaluate(rule.when, answers) is not True:
            continue
        draft("rules.yaml", rule.id, rule.status)
        kind = rule.outcome["kind"]
        if kind == "town_only":
            town_only = True
        elif kind == "application":
            add_app(rule.outcome["application"], None, rule.outcome.get("certainty", "needed"))
        elif kind in ("note", "contact_town"):
            notes.append({"kind": kind, "text": rule.outcome["text"], "cite": rule.cite})
        elif kind == "use_table":
            codes = answers.get("property", {}).get("district_codes") or []
            if not codes:
                notes.append({"kind": "note", "cite": rule.cite,
                              "text": "Find your property first so we can check which district it's in."})
            for code in codes:
                dk = district_key_for(code)
                if dk is None:
                    continue
                cell = ruleset.cells[(dk, answers["use_key"])]
                permits = cell.get("codes") or ([cell["code"]] if cell["code"] else [])
                if not permits:
                    name = _district_name(code, ruleset.districts) or code
                    not_listed.append({"district": code, "use": answers["use_key"], "cite": "8.19.b.1", "text": (
                        f"The Code doesn't list this use in the {name} district. A variance can't be granted "
                        "for a use (Art. 8 §19.b). The Code Enforcement Officer can talk you through your options.")})
                for p in permits:
                    add_app(APP_FOR_CODE[p], code, "needed")
        if rule.stop:
            break

    if town_only:
        outcomes, notes, not_listed = {}, [], []
    return {"outcomes": list(outcomes.values()), "notes": notes, "not_listed": not_listed,
            "town_only": town_only, "drafts_used": [f"{f}: {i}" for f, i in drafts]}


def use_groups(ruleset: Ruleset, defs: Definitions) -> tuple[list[dict], list[str]]:
    labels = {u["use_key"]: u["label"] for u in ruleset.uses}
    groups, drafts = [], []
    for g in defs.groups:
        uses = []
        for u in g.uses:
            if u.status == "draft":
                drafts.append(f"use-groups.yaml: {u.use_key}")
            uses.append({"use_key": u.use_key, "code_name": labels[u.use_key], "example": u.example,
                         "definition": ruleset.definitions[u.definition_key]["definition"]})
        groups.append({"key": g.key, "plain": g.plain, "uses": uses})
    return groups, drafts
