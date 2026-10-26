"""What a project needs (projects brief §6–§8): the screener's approved rules, run on the
project's parts; each outcome a review, priced from the Town's fee schedule and timed by the
Code's clocks.

The rules run once per building-type part (with that part's sizes), once per chosen use, and
once each for a driveway, a division and something else (§6.1). Outcomes merge by review (and
use): "needed" beats "may need". Structure is added once per new building (§12.3). A permit's
application fee counts once per project (§7). Clocks start at the staff lock (§12.1): before it a
review's clocks read in plain words; after it each gives its due date (§12.7).
"""

import calendar
from datetime import date, timedelta

from portal_api.forms.definitions import Definitions
from portal_api.forms.fees import Fees
from portal_api.forms.parts import PartsDef
from portal_api.forms.screener import run
from portal_api.ruleset import Ruleset

BUILD = ("building", "addition", "renovation", "site")
DIVIDED = {"yes": True, "no": False}


def _num(v):
    """A typed number; "I don't know yet" and blanks are unknown."""
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _set(d: dict, path: str, value) -> None:
    head, _, rest = path.partition(".")
    if rest:
        _set(d.setdefault(head, {}), rest, value)
    else:
        d[head] = value


def _runs(part_rows: list[dict], answers: dict, facts: dict, parts: PartsDef) -> list[tuple[dict, str | None]]:
    """The screener answers to run, with the part each came from."""
    prop = {"district_codes": [d["code"] for d in facts.get("districts") or [] if d.get("code")],
            "on_state_highway": facts.get("on_state_highway"), "civic": False}
    homes = sum(_num(answers.get(("dwelling_units", r["id"]))) or 0 for r in part_rows if r["kind"] == "building")
    any_homes_known = any(_num(answers.get(("dwelling_units", r["id"]))) is not None
                          for r in part_rows if r["kind"] == "building")
    project_level = {}
    for path, field in parts.project_inputs.items():
        _set(project_level, path, _num(answers.get((field, None))))
    out = []
    for r in part_rows:
        p = parts.get(r["kind"])
        if p is None:
            continue
        own = lambda field: answers.get((field, r["id"] if p.repeats else None))  # noqa: E731
        base = {"project": [p.rule["project"]], "property": dict(prop), "use_key": None,
                "building": {}, "division": {}}
        if "building.kind" in p.rule:
            base["building"]["kind"] = p.rule["building.kind"]
        if r["kind"] in BUILD:
            base["building"]["new_dwelling_units"] = homes if any_homes_known else None
            base["building"].update(project_level.get("building", {}))
        uses = None
        for path, field in p.inputs.items():
            if path == "use_key":
                uses = [u for u in (own(field) or []) if isinstance(u, str)]
            elif path == "division.divided_last_5_years":
                _set(base, path, DIVIDED.get(own(field)))
            elif path == "building.new_dwelling_units":
                continue  # summed across the project's new buildings (§6.1)
            else:
                v = _num(own(field))
                _set(base, path, int(v) if v is not None and path in ("building.parking_spaces", "division.lots_after") else v)
        if uses:
            out += [({**base, "use_key": u}, r["kind"]) for u in uses]
        else:
            out.append((base, r["kind"]))
    return out


def due_date(start: date, days: int, basis: str) -> tuple[date, bool]:
    """The due date of a clock started on `start`, and whether it is approximate: business days
    skip Saturdays and Sundays but not the Town's holidays, which the ruleset doesn't hold."""
    if basis == "calendar":
        return start + timedelta(days=days), False
    if basis == "business":
        d, left = start, days
        while left:
            d += timedelta(days=1)
            if d.weekday() < 5:
                left -= 1
        return d, True
    if basis == "months":
        m = start.month - 1 + days
        y, m = start.year + m // 12, m % 12 + 1
        return date(y, m, min(start.day, calendar.monthrange(y, m)[1])), False
    raise ValueError(f"unknown basis {basis!r}")


def fee_words(fee) -> str:
    if fee == "varies":
        return "Set by the Town Office"
    if isinstance(fee, dict):
        return f"${fee['per_sf']:.2f} a square foot"
    return "No permit fee" if fee == 0 else f"${fee:,.0f}"


def _clocks(app, ruleset: Ruleset, locked_on: date | None) -> list[dict]:
    out = []
    for k in app.clock_keys:
        c = ruleset.clocks[k]
        entry = {"key": k, "label": c["label"], "plain": app.clock_plain.get(k, {}).get("text"),
                 "days": c["days"], "basis": c["basis"], "when": app.clock_when.get(k)}
        if locked_on is not None and c.get("start_event") == "submitted_at":
            due, about = due_date(locked_on, c["days"], c["basis"])
            what = "Decision due by" if k.endswith("_decision") else "Due by"
            entry |= {"due": due.isoformat(), "approximate": about,
                      "due_words": f"{what} {'about ' if about else ''}{due.strftime('%B')} {due.day}"}
        out.append(entry)
    return out


def drafts(defs: Definitions, fees: Fees) -> list[str]:
    """Every draft entry the needs rest on: the rules and applications, each clock's plain
    sentence, and the fee schedule."""
    out = [f"{d.file}: {d.id}" for d in defs.drafts()]
    out += [f"applications.yaml: {a.key}: clock_plain {k}" for a in defs.applications.values()
            for k, p in a.clock_plain.items() if p.get("status") == "draft"]
    return out + (["fees.yaml"] if fees.status == "draft" else [])


def needs(part_rows: list[dict], answers: dict, facts: dict, ruleset: Ruleset, defs: Definitions, fees: Fees,
          parts: PartsDef, locked_on: date | None = None) -> dict:
    merged: dict[tuple, dict] = {}
    notes, not_listed, town_only = [], [], False
    for screener_answers, _kind in _runs(part_rows, answers, facts, parts):
        result = run(screener_answers, ruleset, defs)
        town_only = town_only or result["town_only"]
        for n in result["notes"]:
            if not any(x["text"] == n["text"] for x in notes):
                notes.append(n)
        not_listed += [x for x in result["not_listed"] if x not in not_listed]
        for o in result["outcomes"]:
            key = (o["application"], o["use_key"])
            have = merged.get(key)
            if have is None:
                merged[key] = {**o, "districts": [o["district_name"]] if o["district_name"] else []}
            else:
                if o["certainty"] == "needed":
                    have["certainty"] = "needed"
                if o["district_name"] and o["district_name"] not in have["districts"]:
                    have["districts"].append(o["district_name"])
    if town_only:
        return {"permits": [], "application_fees_total": 0, "application_fees_vary": False, "notes": [],
                "not_listed": [], "town_only": True}
    reviews = []
    for (app_key, use_key), o in merged.items():
        app = defs.applications[app_key]
        permit, line = fees.line(app_key)
        reviews.append({"review_key": app_key, "use_key": use_key, "name": line.name, "code_name": app.code_name,
                        "plain": app.plain, "reviewer": app.reviewer, "certainty": o["certainty"],
                        "in_portal": app.in_portal, "districts": o["districts"], "fee": line.fee,
                        "fee_words": fee_words(line.fee), "clocks": _clocks(app, ruleset, locked_on),
                        "_permit": permit, "_line": line})
    for r in part_rows:
        if r["kind"] == "building":
            permit, line = fees.line("structure")
            reviews.append({"review_key": "structure", "use_key": None, "part_id": r["id"], "name": line.name,
                            "code_name": line.name, "plain": None, "reviewer": None, "certainty": "needed",
                            "in_portal": True, "districts": [], "fee": line.fee, "fee_words": fee_words(line.fee),
                            "clocks": [], "_permit": permit, "_line": line})
    use_order = [u for s, _ in _runs(part_rows, answers, facts, parts) if (u := s.get("use_key"))]
    permits = []
    for permit in fees.permits:
        mine = [r for r in reviews if r["_permit"] is permit]
        if not mine:
            continue
        lines = [ln.key for ln in permit.reviews]
        mine.sort(key=lambda r: (lines.index(r["_line"].key),
                                 use_order.index(r["use_key"]) if r["use_key"] in use_order else -1))
        permits.append({"key": permit.key, "name": permit.name, "application_fee": permit.application_fee,
                        "application_fee_words": None if permit.application_fee is None
                        else fee_words(permit.application_fee), "reviews": mine,
                        # Due when you send only for a permit the project needs and the portal takes;
                        # one that may not apply, or that the Town Office takes, isn't counted.
                        "due_at_send": any(r["certainty"] == "needed" and r["in_portal"] for r in mine)})
    for r in reviews:
        del r["_permit"], r["_line"]
    numeric = [p["application_fee"] for p in permits
               if p["due_at_send"] and isinstance(p["application_fee"], (int, float))]
    return {"permits": permits, "application_fees_total": sum(numeric),
            "application_fees_vary": any(p["due_at_send"] and p["application_fee"] == "varies" for p in permits),
            "notes": notes, "not_listed": not_listed, "town_only": False}
