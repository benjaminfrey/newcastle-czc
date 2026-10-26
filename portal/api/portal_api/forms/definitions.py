"""The screener's data: applications, rules and use groups (YAML in definitions/).

Everything is validated on load: ids unique, conditions well formed, every citation
resolves in the pinned ruleset, every clock exists, and an approved entry names who
approved it and when. Entries start as drafts; drafts() lists what still needs the
chair's approval.
"""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from portal_api.forms.expr import validate as validate_condition
from portal_api.ruleset import Ruleset, RulesetError

DIR = Path(__file__).resolve().parent / "definitions"
_OUTCOME_KINDS = {"application", "use_table", "note", "town_only", "contact_town"}


class DefinitionError(Exception):
    pass


@dataclass(frozen=True)
class Application:
    key: str
    code_name: str
    plain: str
    reviewer: str
    cite: str
    clock_keys: list
    in_portal: bool
    status: str
    approved_by: str | None = None
    approved_on: str | None = None
    clock_when: dict = field(default_factory=dict)
    ruling: dict | None = None
    clock_plain: dict = field(default_factory=dict)  # clock key -> {text, status, approved_by?, approved_on?}


@dataclass(frozen=True)
class Rule:
    id: str
    order: int
    when: dict
    outcome: dict
    cite: str
    status: str
    stop: bool = False
    approved_by: str | None = None
    approved_on: str | None = None
    ruling: dict | None = None


@dataclass(frozen=True)
class UseEntry:
    use_key: str
    definition_key: str
    example: str
    status: str
    approved_by: str | None = None
    approved_on: str | None = None


@dataclass(frozen=True)
class Group:
    key: str
    plain: str
    uses: list


@dataclass(frozen=True)
class DraftEntry:
    file: str
    id: str


@dataclass
class Definitions:
    applications: dict = field(default_factory=dict)
    rules: list = field(default_factory=list)
    groups: list = field(default_factory=list)

    def drafts(self) -> list[DraftEntry]:
        out = [DraftEntry("applications.yaml", a.key) for a in self.applications.values() if a.status == "draft"]
        out += [DraftEntry("rules.yaml", r.id) for r in self.rules if r.status == "draft"]
        out += [DraftEntry("use-groups.yaml", u.use_key) for g in self.groups for u in g.uses if u.status == "draft"]
        return out


def _check_status(where: str, e: dict) -> None:
    if e.get("status") not in ("draft", "approved"):
        raise DefinitionError(f"{where}: status must be draft or approved")
    if e["status"] == "approved":
        if not e.get("approved_by"):
            raise DefinitionError(f"{where}: an approved entry needs approved_by")
        try:
            date.fromisoformat(str(e.get("approved_on")))
        except ValueError:
            raise DefinitionError(f"{where}: an approved entry needs approved_on (YYYY-MM-DD)") from None


def _check_ruling(where: str, e: dict) -> None:
    r = e.get("ruling")
    if r is None:
        return
    if not (isinstance(r, dict) and r.get("by") and r.get("text")):
        raise DefinitionError(f"{where}: a ruling needs by, on and text")
    try:
        date.fromisoformat(str(r.get("on")))
    except ValueError:
        raise DefinitionError(f"{where}: a ruling's on must be YYYY-MM-DD") from None


def _check_cite(where: str, ref: str, ruleset: Ruleset) -> None:
    try:
        ruleset.cite(ref)
    except RulesetError as exc:
        raise DefinitionError(f"{where}: {exc}") from None


def validate_entries(file: str, entries: list, ruleset: Ruleset) -> None:
    """Validate one file's entries; errors name the file and the entry."""
    seen = set()
    for e in entries:
        ident = e.get("id") or e.get("key") or e.get("use_key")
        where = f"{file}: {ident}"
        if not ident or ident in seen:
            raise DefinitionError(f"{where}: missing or duplicate id")
        seen.add(ident)
        if file == "use-groups.yaml":
            continue
        _check_status(where, e)
        _check_ruling(where, e)
        _check_cite(where, e["cite"], ruleset)
        if file == "rules.yaml":
            try:
                validate_condition(e["when"])
            except ValueError as exc:
                raise DefinitionError(f"{where}: {exc}") from None
            if e["outcome"].get("kind") not in _OUTCOME_KINDS:
                raise DefinitionError(f"{where}: unknown outcome kind")
            uk = e["outcome"].get("use_key")
            if uk is not None and uk not in {u["use_key"] for u in ruleset.uses}:
                raise DefinitionError(f"{where}: use_key {uk!r} is not in {ruleset.key}")
        if file == "applications.yaml":
            for k in e.get("clock_keys", []):
                if k not in ruleset.clocks:
                    raise DefinitionError(f"{where}: no clock {k!r} in {ruleset.key}")
            for k in e.get("clock_when", {}):
                if k not in e.get("clock_keys", []):
                    raise DefinitionError(f"{where}: clock_when names {k!r}, which is not in clock_keys")
            for k, plain in (e.get("clock_plain") or {}).items():
                if k not in e.get("clock_keys", []):
                    raise DefinitionError(f"{where}: clock_plain names {k!r}, which is not in clock_keys")
                if not plain.get("text"):
                    raise DefinitionError(f"{where}: clock_plain {k!r} needs text")
                _check_status(f"{where}: clock_plain {k}", plain)


def _read(name: str) -> list:
    return yaml.safe_load((DIR / name).read_text()) or []


def _load(ruleset: Ruleset) -> Definitions:
    apps, rules, groups = _read("applications.yaml"), _read("rules.yaml"), _read("use-groups.yaml")
    validate_entries("applications.yaml", apps, ruleset)
    validate_entries("rules.yaml", rules, ruleset)
    validate_entries("use-groups.yaml", groups, ruleset)
    use_keys = {u["use_key"] for u in ruleset.uses}
    seen_uses = set()
    for g in groups:
        for u in g["uses"]:
            where = f"use-groups.yaml: {u['use_key']}"
            _check_status(where, u)
            if u["use_key"] not in use_keys:
                raise DefinitionError(f"{where}: not a use in {ruleset.key}")
            if u["use_key"] in seen_uses:
                raise DefinitionError(f"{where}: in more than one group")
            if u["definition_key"] not in ruleset.definitions:
                raise DefinitionError(f"{where}: no definition {u['definition_key']!r}")
            seen_uses.add(u["use_key"])
    app_keys = {a["key"] for a in apps}
    for r in rules:
        if r["outcome"].get("kind") == "application" and r["outcome"].get("application") not in app_keys:
            raise DefinitionError(f"rules.yaml: {r['id']}: unknown application")
    keep = lambda d, cls: {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
    return Definitions(
        applications={a["key"]: Application(**keep(a, Application)) for a in apps},
        rules=sorted((Rule(**keep(r, Rule)) for r in rules), key=lambda r: r.order),
        groups=[Group(key=g["key"], plain=g["plain"], uses=[UseEntry(**keep(u, UseEntry)) for u in g["uses"]])
                for g in groups],
    )


_CACHE: dict[str, Definitions] = {}


def load_definitions(ruleset: Ruleset) -> Definitions:
    if ruleset.key not in _CACHE:
        _CACHE[ruleset.key] = _load(ruleset)
    return _CACHE[ruleset.key]
