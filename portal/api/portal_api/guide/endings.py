"""How a conversation ends (spec §4.6), once no question is left.

The Town's own rules decide: the screener (`forms/screener.py`) says which reviews the project
needs and which uses the district lists, and the checks say what fits. In order:
- **not here**: the chosen use isn't listed in any of the lot's districts; the district's own
  list comes with it;
- **the Town's judgment**: anything the guide couldn't settle (an "I'm not sure", a standard that
  can't be checked, a number kept past its limit, a disputed lot, Town-only land);
- **ready to send**: the reviews the project needs;
- **no permit**: the Town's rules call for no review.

"You're already covered" is never reached: the Town has no permits or established uses on record
in a form the portal can read (spec §12 item 9; the rules coverage memo, §6).
"""

from portal_api.forms.definitions import load_definitions
from portal_api.forms.screener import run
from portal_api.ruleset import district_key_for, load_ruleset


def _set(d: dict, path: str, value) -> None:
    head, _, rest = path.partition(".")
    if rest:
        _set(d.setdefault(head, {}), rest, value)
    else:
        d[head] = value


def _answers(opening, facts: dict, lot) -> dict:
    out: dict = {"property": {"district_codes": list(lot.district_codes)}}
    for path, value in opening.screener.items():
        _set(out, path, value)
    b = facts.get("building") or {}
    if "floor_area_sf" in b:
        _set(out, "building.gross_floor_area_sf", b["floor_area_sf"])
    if "dwelling_units" in b:
        _set(out, "building.new_dwelling_units", b["dwelling_units"])
    use_key = (facts.get("use") or {}).get("use_key")
    if use_key:
        out["use_key"] = use_key
    return out


def _allowed(use_codes: list[str]) -> list[dict]:
    ruleset = load_ruleset()
    out = []
    for code in use_codes:
        dk = district_key_for(code)
        uses = [{"use_key": u["use_key"], "code_name": u["label"]} for u in ruleset.uses
                if (c := ruleset.cells.get((dk, u["use_key"]))) and (c.get("codes") or c.get("code"))]
        out.append({"district": code, "uses": uses})
    return out


KEPT = {"keep_mine": "kept_past_the_limit", "talk_to_town": "talk_to_town", "unsure": "unsure"}


def finish(content, opening: str, facts: dict, unsure: tuple, checks: dict, lot, kept: tuple = ()) -> dict:
    """The ending, without its words: the engine adds the title, body and entry from content."""
    o = content.openings[opening]
    ruleset = load_ruleset()
    result = run(_answers(o, facts, lot), ruleset, load_definitions(ruleset))
    use_key = (facts.get("use") or {}).get("use_key")
    mapped = [c for c in lot.district_codes if district_key_for(c)]
    missing_in = {n["district"] for n in result["not_listed"]}
    base = {"settled": [], "unsettled": [], "reviews": [], "allowed_uses": [], "notes": result["notes"],
            "not_listed": result["not_listed"], "screener_drafts": result["drafts_used"], "entry": None}
    disputed = lot.disputed or (facts.get("lot") or {}).get("confirmed") is False
    # A "no" rests on the lot's district and on the reading of the project: if the person doubts
    # either, it becomes a question for the Town (spec §4.5).
    uncertain = disputed or "lot" in unsure or "confirm" in unsure
    unsettled = []
    if use_key and mapped and all(c in missing_in for c in mapped):
        if not uncertain:
            return {**base, "kind": "not_here", "allowed_uses": _allowed(mapped), "entry": "use_not_listed"}
        unsettled.append({"turn_id": "use_key", "reason": "not_listed"})
    elif use_key:
        unsettled += [{"turn_id": "use_key", "reason": "not_listed_in_one_district", "district": c}
                      for c in mapped if c in missing_in]
    unsettled += [{"turn_id": t, "reason": "unsure"} for t in unsure if not t.startswith("doesnt_fit:")]
    # Which line is the front decides the setbacks (Code §2): a lot on two roads has a primary
    # and a secondary frontage, and "each frontage must be evaluated", so that is the Town's call.
    if len({(L["street"]["name"], L["street"]["type"]) for L in lot.lines if L["street"]}) > 1:
        unsettled.append({"turn_id": "front_line", "reason": "more_than_one_frontage"})
    if (facts.get("lot") or {}).get("front") == "other":
        unsettled.append({"turn_id": "front_line", "reason": "front_not_on_a_road"})
    unsettled += [{"turn_id": t, "reason": KEPT[choice], "standard_keys": list(checks[t]["standard_keys"])}
                  for t, choice in kept if t in checks]
    unsettled += [{"turn_id": t, "reason": c["reason"]} for t, c in checks.items() if c["result"] == "cannot_check"]
    unsettled += [{"turn_id": t, "reason": "kept_past_the_limit"} for t, c in checks.items()
                  if c["result"] == "outside" and not any(u["turn_id"] == t for u in unsettled)]
    if disputed:
        unsettled.append({"turn_id": "lot", "reason": "lot_disputed"})
    if result["town_only"]:
        unsettled.append({"turn_id": None, "reason": "town_only"})
    unsettled += [{"turn_id": None, "reason": "contact_town", "note": n} for n in result["notes"]
                  if n["kind"] == "contact_town"]
    settled = [{"turn_id": t, "check": c} for t, c in checks.items() if c["result"] == "fits"]
    if unsettled:
        return {**base, "kind": "town_judgment", "settled": settled, "unsettled": unsettled}
    if result["outcomes"]:
        return {**base, "kind": "ready", "settled": settled, "reviews": result["outcomes"]}
    return {**base, "kind": "no_permit", "settled": settled}
