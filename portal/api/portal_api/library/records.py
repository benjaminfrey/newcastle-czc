"""The review page's records (design 2, §7–8).

A decision stays pending until the builder writes it into the library's files and the chair
commits them: the files are the Town's record, not this table. A pull is the one decision that
takes effect at once, before any commit, so the guide reads the pulls on every request.
"""

import json

from sqlalchemy import Connection, text

from portal_api.events import append_event

ACTIONS = frozenset({"approve", "edit", "send_back"})


def decide(conn: Connection, entry_id: str, version: int, action: str, by: str, body: dict | None,
           note: str | None) -> int:
    did = conn.execute(text(
        "INSERT INTO library_decision (entry_id, version, action, body, note, decided_by)"
        " VALUES (:e, :v, :a, CAST(:b AS jsonb), :n, :by) RETURNING id"),
        {"e": entry_id, "v": version, "a": action, "b": None if body is None else json.dumps(body),
         "n": note, "by": by}).scalar_one()
    append_event(conn, actor=by, kind="library.decide",
                 payload={"decision": did, "entry": entry_id, "version": version, "action": action})
    return did


def pending(conn: Connection) -> list[dict]:
    """The last unexported decision for each entry, oldest entry first, with who made it."""
    rows = conn.execute(text(
        "SELECT DISTINCT ON (d.entry_id) d.id, d.entry_id, d.version, d.action, d.body, d.note,"
        " d.decided_at, a.email AS decided_by_email"
        " FROM library_decision d JOIN applicant a ON a.id = d.decided_by"
        " WHERE d.exported_at IS NULL ORDER BY d.entry_id, d.id DESC")).mappings().all()
    return [{**r, "decided_at": r["decided_at"].isoformat()} for r in rows]


def superseded(conn: Connection) -> list[int]:
    """Unexported decisions a later one for the same entry replaced: exported with it."""
    return list(conn.execute(text(
        "SELECT id FROM library_decision d WHERE exported_at IS NULL AND id < "
        "(SELECT max(id) FROM library_decision x WHERE x.entry_id = d.entry_id AND x.exported_at IS NULL)")).scalars())


def pull(conn: Connection, entry_id: str, version: int, why: str, by: str) -> None:
    conn.execute(text(
        "INSERT INTO library_pull (entry_id, version, why, pulled_by) VALUES (:e, :v, :w, :by)"
        " ON CONFLICT (entry_id) DO UPDATE SET version = EXCLUDED.version, why = EXCLUDED.why,"
        " pulled_by = EXCLUDED.pulled_by, pulled_at = now(), exported_at = NULL"),
        {"e": entry_id, "v": version, "w": why, "by": by})
    append_event(conn, actor=by, kind="library.pull", payload={"entry": entry_id, "version": version})


def pulls(conn: Connection, *, unexported: bool = False) -> list[dict]:
    q = ("SELECT p.entry_id, p.version, p.why, p.pulled_at, a.email AS pulled_by_email FROM library_pull p"
         " JOIN applicant a ON a.id = p.pulled_by" + (" WHERE p.exported_at IS NULL" if unexported else "")
         + " ORDER BY p.entry_id")
    return [{**r, "pulled_at": r["pulled_at"].isoformat()} for r in conn.execute(text(q)).mappings().all()]


def pulled(conn: Connection) -> frozenset[str]:
    """Every pulled entry, recorded in the files yet or not: a pull stays until a fix replaces it."""
    return frozenset(conn.execute(text("SELECT entry_id FROM library_pull")).scalars())


def mark_exported(conn: Connection, decision_ids: list[int], pull_ids: list[str]) -> None:
    if decision_ids:
        conn.execute(text("UPDATE library_decision SET exported_at = now() WHERE id = ANY(:ids)"),
                     {"ids": decision_ids})
    if pull_ids:
        conn.execute(text("UPDATE library_pull SET exported_at = now() WHERE entry_id = ANY(:ids)"),
                     {"ids": pull_ids})
