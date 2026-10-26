"""Projects in the database (projects brief §5): the project, its property snapshot,
parts, pinned forms, answers, notes, attachments, and what the Town locks. Every
function takes the connection of the caller's transaction; routes check ownership
with `owned` before anything else.

Each change bumps the project's revision with a compare-and-set, so a save from a tab
that was behind is refused instead of overwriting. The same compare-and-set refuses
every change once staff have locked the project.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

EDITABLE = ("draft", "submitted")


@dataclass(frozen=True)
class ProjectRow:
    id: str
    applicant_id: str
    title: str
    ruleset_key: str
    status: str
    revision: int


def parse_id(value: str) -> str | None:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError):
        return None


def owned(conn: Connection, project_id: str, applicant_id: str) -> ProjectRow | None:
    """The project if it exists and is the caller's; None otherwise (both are a 404)."""
    if parse_id(project_id) is None:
        return None
    r = conn.execute(text(
        "SELECT id, applicant_id, title, ruleset_key, status, revision FROM project WHERE id = :id AND applicant_id = :a"
    ), {"id": project_id, "a": applicant_id}).one_or_none()
    return ProjectRow(str(r.id), str(r.applicant_id), r.title, r.ruleset_key, r.status, r.revision) if r else None


def create(conn: Connection, *, applicant_id: str, ruleset_key: str, title: str, snapshot: dict) -> str:
    project_id = str(conn.execute(text(
        "INSERT INTO project (applicant_id, title, ruleset_key) VALUES (:a, :t, :r) RETURNING id"
    ), {"a": applicant_id, "t": title, "r": ruleset_key}).scalar())
    conn.execute(text(
        "INSERT INTO property_snapshot (project_id, source, parcel_id, map_lot, facts, parcels_as_of, verified,"
        " disputed, note) VALUES (:id, :source, :parcel_id, :map_lot, CAST(:facts AS jsonb), :as_of, :verified,"
        " :disputed, :note)"
    ), {"id": project_id, **snapshot, "facts": json.dumps(snapshot["facts"])})
    return project_id


def bump(conn: Connection, project_id: str, base_revision: int) -> int | None:
    """Advance the revision if it is still `base_revision` and the project is still editable;
    None otherwise (another save got there first, or staff have locked it)."""
    return conn.execute(text(
        "UPDATE project SET revision = revision + 1, updated_at = now()"
        " WHERE id = :id AND revision = :base AND status IN ('draft', 'submitted') RETURNING revision"
    ), {"id": project_id, "base": base_revision}).scalar()


def state(conn: Connection, project_id: str) -> tuple[str, int]:
    """(status, revision) now."""
    r = conn.execute(text("SELECT status, revision FROM project WHERE id = :id"), {"id": project_id}).one()
    return r.status, r.revision


def set_title(conn: Connection, project_id: str, title: str) -> None:
    conn.execute(text("UPDATE project SET title = :t WHERE id = :id"), {"t": title, "id": project_id})


def parts(conn: Connection, project_id: str) -> list[dict]:
    return [{"id": str(r.id), "kind": r.kind, "position": r.position} for r in conn.execute(text(
        "SELECT id, kind, position FROM project_part WHERE project_id = :p AND removed_at IS NULL"
        " ORDER BY kind, position"
    ), {"p": project_id})]


def add_part(conn: Connection, project_id: str, kind: str) -> str:
    return str(conn.execute(text(
        "INSERT INTO project_part (project_id, kind, position)"
        " SELECT :p, :k, coalesce(max(position) + 1, 0) FROM project_part WHERE project_id = :p AND kind = :k"
        " RETURNING id"
    ), {"p": project_id, "k": kind}).scalar())


def remove_part(conn: Connection, project_id: str, part_id: str) -> None:
    conn.execute(text("UPDATE project_part SET removed_at = now() WHERE id = :i AND project_id = :p"),
                 {"i": part_id, "p": project_id})


def answers(conn: Connection, project_id: str) -> dict:
    """Current answers keyed by (field_id, part_id or None); a cleared answer is absent, and so is
    an answer on a removed part."""
    rows = conn.execute(text(
        "SELECT DISTINCT ON (a.field_id, a.part_id) a.field_id, a.part_id, a.value FROM answer a"
        " LEFT JOIN project_part p ON p.id = a.part_id"
        " WHERE a.project_id = :p AND (a.part_id IS NULL OR p.removed_at IS NULL)"
        " ORDER BY a.field_id, a.part_id, a.seq DESC"
    ), {"p": project_id})
    return {(r.field_id, str(r.part_id) if r.part_id else None): r.value for r in rows if r.value is not None}


def save_answers(conn: Connection, project_id: str, changes: list[tuple], by: str) -> None:
    for field_id, part_id, value in changes:
        conn.execute(text(
            "INSERT INTO answer (project_id, field_id, part_id, value, set_by)"
            " VALUES (:p, :f, :i, CAST(:v AS jsonb), :by)"
        ), {"p": project_id, "f": field_id, "i": part_id, "v": None if value is None else json.dumps(value), "by": by})


COPIED = "copied"


def copy_part_answers(conn: Connection, project_id: str, fields: list[str], source_id: str, part_id: str) -> None:
    """"Copy Building 1": the source part's current answers to `fields`, unknowns included, blanks not."""
    have = answers(conn, project_id)
    save_answers(conn, project_id, [(f, part_id, have[(f, source_id)]) for f in fields if (f, source_id) in have],
                 COPIED)


def forms(conn: Connection, project_id: str) -> dict[str, int]:
    return dict(conn.execute(text(
        "SELECT form_key, form_version FROM project_form WHERE project_id = :p ORDER BY form_key"
    ), {"p": project_id}).all())


def pin_forms(conn: Connection, project_id: str, wanted: dict[str, int]) -> None:
    """Pin each wanted form not yet pinned, at the version given; a form already pinned keeps its
    version; a form no longer wanted unpins (its answers stay in the history)."""
    have = forms(conn, project_id)
    for key in have.keys() - wanted.keys():
        conn.execute(text("DELETE FROM project_form WHERE project_id = :p AND form_key = :k"),
                     {"p": project_id, "k": key})
    for key in wanted.keys() - have.keys():
        conn.execute(text("INSERT INTO project_form (project_id, form_key, form_version) VALUES (:p, :k, :v)"),
                     {"p": project_id, "k": key, "v": wanted[key]})


def notes(conn: Connection, project_id: str) -> list[dict]:
    rows = conn.execute(text(
        "SELECT DISTINCT ON (section_id, part_id) section_id, part_id, text FROM section_note"
        " WHERE project_id = :p ORDER BY section_id, part_id, seq DESC"
    ), {"p": project_id})
    return [{"section_id": r.section_id, "part_id": str(r.part_id) if r.part_id else None, "text": r.text}
            for r in rows if r.text]


def save_note(conn: Connection, project_id: str, section_id: str, part_id: str | None, body: str, by: str) -> None:
    conn.execute(text(
        "INSERT INTO section_note (project_id, section_id, part_id, text, set_by) VALUES (:p, :s, :i, :t, :by)"
    ), {"p": project_id, "s": section_id, "i": part_id, "t": body, "by": by})


def snapshot(conn: Connection, project_id: str) -> dict:
    r = conn.execute(text(
        "SELECT source, parcel_id, map_lot, facts, parcels_as_of, verified, disputed, note"
        " FROM property_snapshot WHERE project_id = :p"
    ), {"p": project_id}).one()
    return {"source": r.source, "parcel_id": r.parcel_id, "map_lot": r.map_lot, "facts": r.facts,
            "parcels_as_of": r.parcels_as_of.isoformat() if r.parcels_as_of else None,
            "verified": r.verified, "disputed": r.disputed, "note": r.note}


def attachments(conn: Connection, project_id: str) -> list[dict]:
    return [{"id": str(r.id), "field_id": r.field_id, "part_id": str(r.part_id) if r.part_id else None,
             "filename": r.filename, "content_type": r.content_type, "size_bytes": r.size_bytes}
            for r in conn.execute(text(
                "SELECT id, field_id, part_id, filename, content_type, size_bytes FROM attachment"
                " WHERE project_id = :p AND removed_at IS NULL ORDER BY created_at"
            ), {"p": project_id})]


def account(conn: Connection, project_id: str) -> dict:
    """The applicant's account facts, for fields whose source is the account."""
    r = conn.execute(text("SELECT a.email, a.name, a.phone, a.mailing_address FROM project p"
                          " JOIN applicant a ON a.id = p.applicant_id WHERE p.id = :p"), {"p": project_id}).one()
    return {"email": r.email, "name": r.name, "phone": r.phone, "mailing_address": r.mailing_address}


def mine(conn: Connection, applicant_id: str) -> list:
    return conn.execute(text(
        "SELECT p.id, p.title, p.status, p.updated_at, p.submitted_at, s.map_lot FROM project p"
        " JOIN property_snapshot s ON s.project_id = p.id WHERE p.applicant_id = :a ORDER BY p.updated_at DESC"
    ), {"a": applicant_id}).all()


def submit(conn: Connection, project_id: str) -> None:
    """Sent: the first send stamps the time; the project stays editable until the lock."""
    conn.execute(text("UPDATE project SET status = 'submitted', submitted_at = coalesce(submitted_at, now())"
                      " WHERE id = :p AND status IN ('draft', 'submitted')"), {"p": project_id})


def lock(conn: Connection, project_id: str, base_revision: int, staff_id: str | None, snapshot: dict) -> int | None:
    """Staff lock a sent project at `base_revision`: the project stops taking changes and the
    snapshot (exactly the answers at that revision) is kept as the next submission. Returns the
    submission's seq, or None when the revision is stale or the project wasn't sent."""
    r = conn.execute(text(
        "UPDATE project SET status = 'locked', locked_at = now(), locked_by = :s, revision = revision + 1,"
        " updated_at = now() WHERE id = :p AND revision = :base AND status = 'submitted' RETURNING locked_at"
    ), {"p": project_id, "base": base_revision, "s": staff_id}).one_or_none()
    if r is None:
        return None
    body = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return conn.execute(text(
        "INSERT INTO submission (project_id, seq, locked_at, locked_by, snapshot, sha256)"
        " SELECT :p, coalesce(max(seq), 0) + 1, :at, :s, CAST(:b AS jsonb), :h FROM submission WHERE project_id = :p"
        " RETURNING seq"
    ), {"p": project_id, "at": r.locked_at, "s": staff_id, "b": body,
        "h": hashlib.sha256(body.encode()).hexdigest()}).scalar()
