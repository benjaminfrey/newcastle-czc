"""Applications in the database: drafts, their property snapshot, items, answers,
notes and attachments. Every function takes the connection of the caller's
transaction; routes check ownership with `owned` before anything else.

Each change bumps the application's revision with a compare-and-set, so a save from
a tab that was behind is refused instead of overwriting (spec §6).
"""

import json
import uuid
from dataclasses import dataclass

from sqlalchemy import Connection, text

from portal_api.forms.answers import Current
from portal_api.forms.formdefs import FormDef


@dataclass(frozen=True)
class AppRow:
    id: str
    applicant_id: str
    form_key: str
    form_version: int
    ruleset_key: str
    status: str
    revision: int


def parse_id(value: str) -> str | None:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError):
        return None


def owned(conn: Connection, app_id: str, applicant_id: str) -> AppRow | None:
    """The application if it exists and is the caller's; None otherwise (both are a 404)."""
    if parse_id(app_id) is None:
        return None
    r = conn.execute(text(
        "SELECT id, applicant_id, form_key, form_version, ruleset_key, status, revision"
        " FROM application WHERE id = :id AND applicant_id = :a"
    ), {"id": app_id, "a": applicant_id}).one_or_none()
    return AppRow(str(r.id), str(r.applicant_id), r.form_key, r.form_version, r.ruleset_key, r.status, r.revision) \
        if r else None


def create(conn: Connection, *, applicant_id: str, form: FormDef, snapshot: dict) -> str:
    app_id = str(conn.execute(text(
        "INSERT INTO application (applicant_id, form_key, form_version, ruleset_key)"
        " VALUES (:a, :k, :v, :r) RETURNING id"
    ), {"a": applicant_id, "k": form.key, "v": form.version, "r": form.ruleset_key}).scalar())
    conn.execute(text(
        "INSERT INTO property_snapshot (application_id, source, parcel_id, map_lot, facts, parcels_as_of, verified,"
        " disputed, note) VALUES (:id, :source, :parcel_id, :map_lot, CAST(:facts AS jsonb), :as_of, :verified,"
        " :disputed, :note)"
    ), {"id": app_id, **snapshot, "facts": json.dumps(snapshot["facts"])})
    kinds = {}
    for s in form.sections:
        if s.repeat is not None:
            kinds.setdefault(s.repeat.kind, s.repeat.min)
    # A question's default is written as an answer, marked as the form's, so the applicant
    # sees it set (a switch already on) and the record shows nobody typed it.
    defaults = [(f.id, f.default) for sec, f in form.fields() if sec.repeat is None and f.default is not None]
    save_answers(conn, app_id, [(fid, None, v) for fid, v in defaults], FORM_DEFAULT)
    for kind, n in kinds.items():
        for _ in range(n):
            new_item(conn, app_id, form, kind)
    return app_id


FORM_DEFAULT = "form-default"


def new_item(conn: Connection, app_id: str, form: FormDef, kind: str) -> str:
    """Add an item with its fields' defaults, saved as the form's."""
    item_id = add_item(conn, app_id, kind)
    defaults = [(f.id, item_id, f.default) for sec, f in form.fields()
                if sec.repeat and sec.repeat.kind == kind and f.default is not None]
    save_answers(conn, app_id, defaults, FORM_DEFAULT)
    return item_id


def bump(conn: Connection, app_id: str, base_revision: int) -> int | None:
    """Advance the revision if it is still `base_revision`; None if another save got there first."""
    return conn.execute(text(
        "UPDATE application SET revision = revision + 1, updated_at = now()"
        " WHERE id = :id AND revision = :base RETURNING revision"
    ), {"id": app_id, "base": base_revision}).scalar()


def revision(conn: Connection, app_id: str) -> int:
    return conn.execute(text("SELECT revision FROM application WHERE id = :id"), {"id": app_id}).scalar()


def items(conn: Connection, app_id: str) -> list[dict]:
    return [{"id": str(r.id), "kind": r.kind, "position": r.position} for r in conn.execute(text(
        "SELECT id, kind, position FROM application_item WHERE application_id = :a AND removed_at IS NULL"
        " ORDER BY kind, position"
    ), {"a": app_id})]


def add_item(conn: Connection, app_id: str, kind: str) -> str:
    return str(conn.execute(text(
        "INSERT INTO application_item (application_id, kind, position)"
        " SELECT :a, :k, coalesce(max(position) + 1, 0) FROM application_item WHERE application_id = :a AND kind = :k"
        " RETURNING id"
    ), {"a": app_id, "k": kind}).scalar())


def remove_item(conn: Connection, app_id: str, item_id: str) -> None:
    conn.execute(text("UPDATE application_item SET removed_at = now() WHERE id = :i AND application_id = :a"),
                 {"i": item_id, "a": app_id})


def answers(conn: Connection, app_id: str) -> dict:
    """Current answers keyed by (field_id, item_id or None); a cleared answer is absent."""
    rows = conn.execute(text(
        "SELECT DISTINCT ON (field_id, item_id) field_id, item_id, value FROM answer"
        " WHERE application_id = :a ORDER BY field_id, item_id, seq DESC"
    ), {"a": app_id})
    return {(r.field_id, str(r.item_id) if r.item_id else None): r.value for r in rows if r.value is not None}


def save_answers(conn: Connection, app_id: str, changes: list[tuple], by: str) -> None:
    for field_id, item_id, value in changes:
        conn.execute(text(
            "INSERT INTO answer (application_id, field_id, item_id, value, set_by)"
            " VALUES (:a, :f, :i, CAST(:v AS jsonb), :by)"
        ), {"a": app_id, "f": field_id, "i": item_id, "v": None if value is None else json.dumps(value), "by": by})


def notes(conn: Connection, app_id: str) -> list[dict]:
    rows = conn.execute(text(
        "SELECT DISTINCT ON (section_id, item_id) section_id, item_id, text FROM section_note"
        " WHERE application_id = :a ORDER BY section_id, item_id, seq DESC"
    ), {"a": app_id})
    return [{"section_id": r.section_id, "item_id": str(r.item_id) if r.item_id else None, "text": r.text}
            for r in rows if r.text]


def save_note(conn: Connection, app_id: str, section_id: str, item_id: str | None, body: str, by: str) -> None:
    conn.execute(text(
        "INSERT INTO section_note (application_id, section_id, item_id, text, set_by) VALUES (:a, :s, :i, :t, :by)"
    ), {"a": app_id, "s": section_id, "i": item_id, "t": body, "by": by})


def snapshot(conn: Connection, app_id: str) -> dict:
    r = conn.execute(text(
        "SELECT source, parcel_id, map_lot, facts, parcels_as_of, verified, disputed, note"
        " FROM property_snapshot WHERE application_id = :a"
    ), {"a": app_id}).one()
    return {"source": r.source, "parcel_id": r.parcel_id, "map_lot": r.map_lot, "facts": r.facts,
            "parcels_as_of": r.parcels_as_of.isoformat() if r.parcels_as_of else None,
            "verified": r.verified, "disputed": r.disputed, "note": r.note}


def attachments(conn: Connection, app_id: str) -> list[dict]:
    return [{"id": str(r.id), "field_id": r.field_id, "item_id": str(r.item_id) if r.item_id else None,
             "filename": r.filename, "content_type": r.content_type, "size_bytes": r.size_bytes}
            for r in conn.execute(text(
                "SELECT id, field_id, item_id, filename, content_type, size_bytes FROM attachment"
                " WHERE application_id = :a AND removed_at IS NULL ORDER BY created_at"
            ), {"a": app_id})]


def current(conn: Connection, app_id: str, email: str) -> Current:
    snap = snapshot(conn, app_id)
    return Current(answers=answers(conn, app_id),
                   items=[(i["id"], i["kind"], i["position"]) for i in items(conn, app_id)],
                   property=snap["facts"], account={"email": email})


def mine(conn: Connection, applicant_id: str) -> list:
    return conn.execute(text(
        "SELECT a.id, a.form_key, a.form_version, a.status, a.updated_at, p.map_lot FROM application a"
        " JOIN property_snapshot p ON p.application_id = a.id WHERE a.applicant_id = :a ORDER BY a.updated_at DESC"
    ), {"a": applicant_id}).all()
