"""Answers to a form: checking a value, and working out what applies.

`applicable` lists the questions the wizard asks, in order; `missing` the required
ones still unanswered; `printed` what the official form shows. A question hidden by
a later change keeps its answer in the record but is neither counted nor printed;
if the question comes back, so does the answer. The browser mirrors these rules in
web/src/forms/applicability.ts.
"""

import math
from dataclasses import dataclass, field
from datetime import date
from numbers import Real

from portal_api.forms.expr import shown
from portal_api.forms.formdefs import Field, FormDef, Section
from portal_api.ruleset import load_ruleset

TEXT_MAX = 2_000
LONGTEXT_MAX = 10_000
UNKNOWN = {"unknown": True}


class AnswerError(Exception):
    def __init__(self, field_id: str, reason: str):
        super().__init__(f"{field_id}: {reason}")
        self.field_id = field_id
        self.reason = reason


@dataclass
class Current:
    """An application's current state: answers keyed by (field_id, item_id or None),
    live items as (id, kind, position), the property snapshot, and the account."""
    answers: dict
    items: list
    property: dict
    account: dict = field(default_factory=dict)


def _number(v) -> bool:
    return isinstance(v, Real) and not isinstance(v, bool) and math.isfinite(v)


def check_value(f: Field, value, *, bounds: tuple | None = None):
    """The normalised value to store, or AnswerError. None (or blank text) clears."""
    err = lambda reason: AnswerError(f.id, reason)
    if not f.is_question:
        raise err("not_a_question")
    if value is None:
        return None
    if value == UNKNOWN:
        if not f.allow_unknown:
            raise err("unknown_not_allowed")
        return dict(UNKNOWN)
    t = f.type
    if t in ("text", "longtext"):
        if not isinstance(value, str):
            raise err("wrong_type")
        value = value.strip()
        if len(value) > (TEXT_MAX if t == "text" else LONGTEXT_MAX):
            raise err("too_long")
        return value or None
    if t == "number":
        if not _number(value):
            raise err("wrong_type")
        if (f.min is not None and value < f.min) or (f.max is not None and value > f.max):
            raise err("out_of_range")
        return float(value)
    if t == "yesno":
        if not isinstance(value, bool):
            raise err("wrong_type")
        return value
    if t == "date":
        try:
            return date.fromisoformat(value).isoformat()
        except (TypeError, ValueError):
            raise err("wrong_type") from None
    if t == "choice":
        if not isinstance(value, str):
            raise err("wrong_type")
        if value not in {o.value for o in f.options}:
            raise err("not_an_option")
        return value
    if t in ("multichoice", "uses"):
        if not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            raise err("wrong_type")
        allowed = {o.value for o in f.options} if t == "multichoice" else {u["use_key"] for u in load_ruleset().uses}
        if any(v not in allowed for v in value):
            raise err("not_an_option")
        return list(dict.fromkeys(value))
    if t == "point":
        if not (isinstance(value, dict) and set(value) == {"lon", "lat"} and _number(value["lon"]) and _number(value["lat"])):
            raise err("wrong_type")
        if bounds is not None:
            min_lon, min_lat, max_lon, max_lat = bounds
            if not (min_lon <= value["lon"] <= max_lon and min_lat <= value["lat"] <= max_lat):
                raise err("out_of_range")
        return {"lon": float(value["lon"]), "lat": float(value["lat"])}
    # Uploads are attachments, added through their own endpoint.
    raise err("wrong_type")


def _live_items(cur: Current, kind: str) -> list:
    return [i for i, k, _ in sorted((it for it in cur.items if it[1] == kind), key=lambda it: it[2])]


def _scope(cur: Current, item_id) -> dict:
    top = {fid: v for (fid, item), v in cur.answers.items() if item is None}
    item = {fid: v for (fid, it), v in cur.answers.items() if item_id is not None and it == item_id}
    return {"answers": top, "item": item, "property": cur.property}


def _blocks(form: FormDef, cur: Current):
    """(section, item_id) in form order. Consecutive sections repeating the same kind
    are walked item by item, so each building gets all of its sections in turn."""
    sections = list(form.sections)
    i = 0
    while i < len(sections):
        s = sections[i]
        if s.repeat is None:
            yield s, None
            i += 1
            continue
        run = [s]
        while i + len(run) < len(sections) and sections[i + len(run)].repeat \
                and sections[i + len(run)].repeat.kind == s.repeat.kind:
            run.append(sections[i + len(run)])
        for item_id in _live_items(cur, s.repeat.kind):
            for rs in run:
                yield rs, item_id
        i += len(run)


def _shown_blocks(form: FormDef, cur: Current):
    for s, item_id in _blocks(form, cur):
        data = _scope(cur, item_id)
        if shown(s.show_if, data):
            yield s, item_id, data


def applicable(form: FormDef, cur: Current) -> list[tuple[Section, Field, str | None]]:
    return [(s, f, item_id) for s, item_id, data in _shown_blocks(form, cur)
            for f in s.fields if f.is_question and shown(f.show_if, data)]


def _property_value(key: str, prop: dict, *, prefill: bool):
    v = prop.get(key)
    if key == "districts":
        names = [d.get("name") or d.get("code") for d in v or []]
        return "; ".join(n for n in names if n) or None
    if key == "streets":
        if not v:
            return None
        if prefill:
            return float(sum(s.get("frontage_ft") or 0 for s in v))
        return "; ".join(f"{s['name']}" + (f" ({s['type_name']})" if s.get("type_name") else "")
                         + (f", about {s['frontage_ft']} ft" if s.get("frontage_ft") is not None else "") for s in v)
    return v


def value_of(form: FormDef, f: Field, item_id, cur: Current, _depth: int = 0):
    """What a field holds now: the answer, or a property, account or derived value."""
    if f.source == "question" or f.may_correct:
        v = cur.answers.get((f.id, item_id))
        if v is None and f.may_correct:
            return _property_value(f.from_, cur.property, prefill=True)
        return v
    if f.source == "property":
        return _property_value(f.from_, cur.property, prefill=False)
    if f.source == "account":
        return cur.account.get(f.from_)
    if f.source == "parts":
        return cur.answers.get((f.from_, None))
    if f.source == "derived" and _depth < 5:
        try:
            _, src = form.field(f.from_)
        except KeyError:
            return _property_value(f.from_, cur.property, prefill=False)
        return value_of(form, src, None, cur, _depth + 1)
    return None


def missing(form: FormDef, cur: Current) -> list[tuple[str, str | None]]:
    return [(f.id, item_id) for _, f, item_id in applicable(form, cur)
            if f.required and f.type != "upload" and value_of(form, f, item_id, cur) in (None, [], "")]


def printed(form: FormDef, cur: Current) -> list[tuple[Section, str | None, list]]:
    out = []
    for s, item_id, data in _shown_blocks(form, cur):
        rows = [(f, value_of(form, f, item_id, cur)) for f in s.fields
                if not f.is_question or shown(f.show_if, data)]
        out.append((s, item_id, rows))
    return out
