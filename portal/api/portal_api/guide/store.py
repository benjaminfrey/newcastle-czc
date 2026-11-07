"""The guide's record in the database: the opening, each action with the turn as shown, and the
person's own words. Every function takes the caller's connection. Actions and notes are
insert-only (migration 0009); a restart is an action too, so nothing said is ever lost.
"""

import json

from sqlalchemy import Connection, text

from portal_api.guide.engine import Action


def start(conn: Connection, project_id: str, opening: str, digest: str) -> None:
    conn.execute(text(
        "INSERT INTO guide_conversation (project_id, opening, content_digest) VALUES (:p, :o, :d)"
    ), {"p": project_id, "o": opening, "d": digest})


def _insert(conn: Connection, project_id: str, kind: str, turn_id, value, shown: dict, digest: str, by: str) -> int:
    return conn.execute(text(
        "INSERT INTO guide_action (project_id, seq, kind, turn_id, value, shown, content_digest, by)"
        " SELECT :p, coalesce(max(seq), 0) + 1, :k, :t, CAST(:v AS jsonb), CAST(:s AS jsonb), :d, :b"
        " FROM guide_action WHERE project_id = :p RETURNING seq"
    ), {"p": project_id, "k": kind, "t": turn_id, "v": json.dumps(value), "s": json.dumps(shown),
        "d": digest, "b": by}).scalar()


def record(conn: Connection, project_id: str, action: Action, shown: dict, digest: str, by: str) -> int:
    """Append one answer or Back; the new seq."""
    return _insert(conn, project_id, action.kind, action.turn_id, action.value, shown, digest, by)


def restart(conn: Connection, project_id: str, opening: str, shown: dict, digest: str, by: str) -> int:
    """Start over from another picture, after "No" on "So you mean…"."""
    return _insert(conn, project_id, "restart", None, opening, shown, digest, by)


def conversation(conn: Connection, project_id: str) -> tuple[str, list[Action]] | None:
    """The opening in force and the actions since it, in order; None if the guide never started."""
    opening = conn.execute(text("SELECT opening FROM guide_conversation WHERE project_id = :p"),
                           {"p": project_id}).scalar()
    if opening is None:
        return None
    actions: list[Action] = []
    for r in conn.execute(text(
        "SELECT kind, turn_id, value FROM guide_action WHERE project_id = :p ORDER BY seq"
    ), {"p": project_id}):
        if r.kind == "restart":
            opening, actions = r.value, []
        else:
            actions.append(Action(r.kind, r.turn_id, r.value))
    return opening, actions


def add_note(conn: Connection, project_id: str, body: str, by: str) -> None:
    conn.execute(text("INSERT INTO guide_note (project_id, body, by) VALUES (:p, :b, :by)"),
                 {"p": project_id, "b": body, "by": by})


def notes(conn: Connection, project_id: str) -> list[dict]:
    return [{"body": r.body, "at": r.at.isoformat()} for r in conn.execute(text(
        "SELECT body, at FROM guide_note WHERE project_id = :p ORDER BY n"
    ), {"p": project_id})]


def save_packet(conn: Connection, project_id: str, body: dict) -> None:
    """The packet as sent (plan 6): sending again replaces it."""
    conn.execute(text(
        "INSERT INTO guide_packet (project_id, sent_at, body) VALUES (:p, now(), CAST(:b AS jsonb))"
        " ON CONFLICT (project_id) DO UPDATE SET sent_at = now(), body = excluded.body"
    ), {"p": project_id, "b": json.dumps(body)})


def sent_packet(conn: Connection, project_id: str):
    """(sent_at, body) of the packet as sent, or None."""
    r = conn.execute(text("SELECT sent_at, body FROM guide_packet WHERE project_id = :p"), {"p": project_id}).first()
    return (r.sent_at, r.body) if r else None
