"""The packet (guided plan 6; spec §7): what the Town reads about a project, and what the person
sees of it, built once from what is already stored: the conversation, its checks and ending, the
notes, the snapshot, the needs and the drawing. The staff view (design 4) adds its notes to the same
packet, so the two can't disagree.

The person's own words are carried exactly as stored. Nothing here decides: "fits" is a check
against a number, and everything else goes to the Town with the reason the ending gives.
"""

import dataclasses

from sqlalchemy import Connection

from portal_api import projects as pj
from portal_api.guide import drawing, store
from portal_api.guide.checks import limit_for
from portal_api.guide.content import drafts_in, load_content
from portal_api.guide.engine import Lot, _Build, replay

DRAWN_LIMITS = {"front": "setback_front", "side": "setback_side_1", "rear": "setback_rear",
                "secondary": "setback_secondary"}

# A doesn't-fit turn's answers that the packet highlights (plan 3's choices).
_SUGGESTION_MARKS = {"nearest": "took_suggestion", "keep_mine": "kept"}


def drawing_payload(snapshot: dict, lot, state) -> dict:
    """The lot drawing (plan 4): the tax-map outline, each line's role once the front is chosen,
    and the setback limits for this lot from the rulesets."""
    outline = (snapshot.get("facts") or {}).get("outline")
    front = (state.facts.get("lot") or {}).get("front")
    content = load_content()
    limits = {}
    for role, turn_id in DRAWN_LIMITS.items():
        lim = limit_for(content.turn(turn_id), lot, state.facts)
        limits[role] = dataclasses.asdict(lim) if lim else None
    return {"outline": outline, "front": front if outline else None,
            "roles": drawing.roles(outline["lines"], front) if outline else None, "limits": limits}


def deciders_from(needs: dict) -> list[str]:
    """Who decides: the approved decision sentence of every review the project needs, in the order
    the reviews run (applications.yaml's clocks whose key names a decision)."""
    out: list[str] = []
    for permit in needs.get("permits") or []:
        for review in permit.get("reviews") or []:
            if review.get("certainty") != "needed":
                continue
            for clock in review.get("clocks") or []:
                plain = clock.get("plain")
                if "decision" in clock.get("key", "") and plain and plain not in out:
                    out.append(plain)
    return out


def _answer(shown, value) -> str | None:
    for a in shown.answers or ():
        if a["id"] == value:
            return a["label"]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        unit = (shown.input or {}).get("unit")
        return f"{value:,}" + (f" {unit}" if unit else "")
    return None if value is None else str(value)


def _marks(shown, value) -> list[str]:
    if shown.turn_id == "confirm" and value == "yes":
        return ["confirmed"]
    if value == "unsure":
        return ["unsure"]
    if shown.turn_id.startswith("doesnt_fit:") and value in _SUGGESTION_MARKS:
        return [_SUGGESTION_MARKS[value]]
    return []


def build(conn: Connection, row, lot, opening: str, state, needs: dict) -> dict:
    content = load_content()
    explain = _Build(content, opening, lot)
    snapshot = pj.snapshot(conn, row.id)
    asked = {s.turn_id: s.ask for s, _ in state.history}

    def ask(turn_id):
        if turn_id is None:
            return None
        turn = content.turn(turn_id)
        return asked.get(turn_id) or (turn.ask if turn else None)

    def why(turn_id):
        turn = content.turn(turn_id) if turn_id else None
        return explain.entry(turn.why) if turn and turn.why else None

    reading = next((s.ask for s, v in reversed(state.history) if s.turn_id == "confirm" and v == "yes"), None)
    checks = dict(state.checks)
    if state.ending is not None:
        town = [{"turn_id": u["turn_id"], "ask": ask(u["turn_id"]), "reason": u["reason"],
                 "check": checks.get(u["turn_id"]), "why": why(u["turn_id"])} for u in state.ending["unsettled"]]
        fits = [{"turn_id": s["turn_id"], "ask": ask(s["turn_id"]), "check": s["check"], "why": why(s["turn_id"])}
                for s in state.ending["settled"]]
    else:
        town = [{"turn_id": t, "ask": ask(t), "reason": "kept_past_the_limit" if c["result"] == "outside" else c["reason"],
                 "check": c, "why": why(t)} for t, c in checks.items() if c["result"] != "fits"]
        town += [{"turn_id": t, "ask": ask(t), "reason": "unsure", "check": None, "why": why(t)}
                 for t in state.unsure if t not in checks and not t.startswith("doesnt_fit:")]
        fits = [{"turn_id": t, "ask": ask(t), "check": c, "why": why(t)} for t, c in checks.items() if c["result"] == "fits"]

    disputed = bool(lot.disputed) or (state.facts.get("lot") or {}).get("confirmed") is False
    outline = (snapshot.get("facts") or {}).get("outline")
    return {
        "state": "now", "sent_at": None, "finished": state.ending is not None,
        "summary": {"own_words": store.notes(conn, row.id), "reading": reading, "deciders": deciders_from(needs),
                    "corrections": {"lot_disputed": disputed, "note": snapshot.get("note") or None}},
        "history": [{"turn_id": s.turn_id, "ask": s.ask, "answer": _answer(s, v), "marks": _marks(s, v)}
                    for s, v in state.history],
        "checklist": {"town": town, "fits": fits},
        "drawing": drawing_payload(snapshot, lot, state) if outline else None,
        "drafts": list(dict.fromkeys([*state.drafts, *drafts_in(content, opening=opening, turn_ids=[],
                                                                entry_ids=explain.entries, wording_keys=explain.wording)])),
    }


def build_for(conn: Connection, row, needs: dict) -> dict | None:
    """The packet as it stands now, or None when the project has no conversation."""
    convo = store.conversation(conn, row.id)
    if convo is None:
        return None
    lot = Lot.from_snapshot(pj.snapshot(conn, row.id))
    opening, actions = convo
    return build(conn, row, lot, opening, replay(load_content(), opening, lot, actions), needs)


def as_sent(conn: Connection, row) -> dict | None:
    """The packet as sent, once the project has been sent and one was kept."""
    if row.status == "draft":
        return None
    kept = store.sent_packet(conn, row.id)
    if kept is None:
        return None
    sent_at, body = kept
    return {**body, "state": "sent", "sent_at": sent_at.isoformat()}
