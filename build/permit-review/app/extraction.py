"""Implements the W4 "operator confirm UI" task brief on top of
CONTRACT.md §3.6 (`field_defs` / `field_candidates` / `field_values`) and
§3.3 (the audit chain). app/routes/extraction.py is the thin HTTP
translation layer over this module — the same split app/cases.py <->
app/routes/cases.py already established.

THE CENTRAL DESIGN PRINCIPLE (restated from the task brief; everything
below exists to enforce it):

    A field_candidates row is EVIDENCE, never an answer. A field_values row
    is a DECISION a human made. This module never promotes a candidate to a
    value on its own — only confirm_field() / override_field() /
    mark_not_applicable() do that, each called by a human action in the UI,
    and each writes exactly one `events` row (actor + why) in the SAME
    transaction as the field_values write.

CONTESTED, computed on read, not stored as truth:
    "THE FORM IS WRONG, THE PLAN GOVERNS" (documents.source_priority: plan
    100 > survey 90 > deed 80 > form 40). When two candidates for the same
    (field_def, subject) disagree, list_case_fields() marks the field
    `contested=True` and returns every candidate, highest source_priority
    first, WITHOUT pre-selecting a winner — the operator picks. This is
    computed fresh from field_candidates every time, not read off a stored
    `field_values.state='contested'` flag, so a field is "contested" for as
    long as its evidence actually disagrees and a human has not yet decided
    it — never something this module has to remember to set or clear itself.

SCOPE, restated from the task brief that commissioned this file: this
module reads whatever field_candidates rows a separate, not-yet-built
Tier A/B extraction pass already wrote, and lets a human confirm / override
/ mark-not-applicable them. NO LLM, NO VISION, NO OCR call happens anywhere
in this file, and it never writes a field_candidates row itself.

INTEGRATION WITH THE REST OF W4 (this workflow builds several pieces of
Phase 4 concurrently; this module is the seam between them):
  - ingest/formgen.py detects, per DOCUMENT, which of the two known form
    layouts it is (or 'unknown'), persisting `documents.generation` (see
    0009_document_formgen.sql). That module's own docstring names
    case_form_generation() BELOW as the case-level rollup across a case's
    several documents it does not itself own — this is that rollup.
  - ingest/worklist.py owns the real absence-worklist logic: it seeds the
    ~23 case-level field_defs a real Findings draft needs (Applicant, Owner
    Deed Reference, Tax Lot, ...), groups by WHERE the value must come from
    (source_category), and materializes field_values(state=
    'not_in_application') for whichever ones this case's evidence never
    supplied — see that module's own docstring for why materializing an
    absence is a FACT, not a human judgment call, and therefore not a
    violation of this module's own "never promotes a candidate" principle.
    list_absence_worklist() below delegates to it (import guarded — see
    _worklist_mod), falling back to a simpler field_defs-only scan if it is
    ever unavailable, so this module still works standalone.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app import citation as citation_mod
from app.audit import append_event

try:
    from ingest import worklist as _worklist_mod
except Exception:  # noqa: BLE001 - degrade-gracefully boundary, matching app/main.py's own _try_import pattern
    _worklist_mod = None

# --------------------------------------------------------------------------- #
# Vocabulary — mirrors the field_values.state CHECK in 0001_init.sql.
# --------------------------------------------------------------------------- #

FIELD_VALUE_STATES: tuple[str, ...] = (
    "unconfirmed", "confirmed", "overridden",
    "not_in_application", "not_applicable", "contested",
)

GENERATION_LABELS: dict[str, str] = {
    "gen1": "Gen-1 — “Zoning Permit Application”",
    "gen2": "Gen-2 — “PLANNING APPLICATION” (modular)",
    "unknown": "Unknown form generation",
}


# --------------------------------------------------------------------------- #
# Errors — same shape as app/cases.py's CaseError family.
# --------------------------------------------------------------------------- #


class ExtractionError(Exception):
    """Base for every error this module raises."""


class CaseNotFound(ExtractionError, LookupError):
    def __init__(self, case_id: str):
        self.case_id = case_id
        super().__init__(f"no case with id {case_id!r}")


class CandidateNotFound(ExtractionError, LookupError):
    def __init__(self, candidate_id: str):
        self.candidate_id = candidate_id
        super().__init__(f"no matching field_candidates row for id {candidate_id!r} on this field")


class ValidationError(ExtractionError, ValueError):
    """`.details` is a list of {"field": ..., "message": ...} dicts, matching
    CONTRACT.md §6's envelope."""

    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        super().__init__(f"validation failed: {details}")


# --------------------------------------------------------------------------- #
# Small internal helpers — mirror app/cases.py's own.
# --------------------------------------------------------------------------- #


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    """ISO-8601 UTC, 'Z' suffix, millisecond precision — CONTRACT.md §3.3."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _rollback_and_raise(conn: sqlite3.Connection, exc: BaseException) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK;")
    raise exc


def _get_case_row(conn: sqlite3.Connection, case_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM cases WHERE id = ?;", (case_id,)).fetchone()
    if row is None:
        raise CaseNotFound(case_id)
    return row


def case_form_generation(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    """The W4 banner's data: 'gen1' | 'gen2' | 'unknown' | None ('unknown' =
    detection ran and could not identify the generation; None = nothing to
    detect from yet / not attempted). Only 'unknown' renders the "extraction
    was not attempted, everything needs manual entry" banner — None is
    deliberately silent (see 0008_case_form_generation.sql's docstring for
    why those two are NOT the same fact).

    Resolution order, most-authoritative first:
      1. `cases.form_generation` — an explicit human pin (0008's own escape
         hatch), always wins outright.
      2. `documents.generation` — ingest/formgen.py's per-document, OCR-aware
         detection (0009_document_formgen.sql), rolled up across every live
         document on the case: any 'unknown', or any disagreement between
         documents, rolls the WHOLE case up to 'unknown' (CONTRACT.md §1 S7 —
         a genuine disagreement is exactly the kind of ambiguity that must be
         reported, never silently resolved by picking one document to trust).
      3. If the case has at least one document but none carries a persisted
         `generation` yet, fall back to ingest/worklist.py's lighter,
         text-only, on-the-fly detector (no OCR — see that module's own
         case_form_generation()) so the banner still works before
         ingest/formgen.py has been run over the upload.
      4. A case with NO documents at all has nothing to detect — silent
         None, not a loud 'unknown' (an empty intake is not a failed
         detection).
    """
    case = _get_case_row(conn, case_id)

    if case["form_generation"] is not None:
        gen = case["form_generation"]
        return {"generation": gen, "unknown": gen == "unknown", "label": GENERATION_LABELS.get(gen)}

    doc_gens = [
        r["generation"]
        for r in conn.execute(
            """
            SELECT generation FROM documents
            WHERE case_id = ? AND generation IS NOT NULL AND superseded_by IS NULL;
            """,
            (case_id,),
        ).fetchall()
    ]
    if doc_gens:
        distinct = set(doc_gens)
        gen = "unknown" if (len(distinct) > 1 or "unknown" in distinct) else next(iter(distinct))
        return {"generation": gen, "unknown": gen == "unknown", "label": GENERATION_LABELS.get(gen)}

    has_any_document = conn.execute(
        "SELECT 1 FROM documents WHERE case_id = ? LIMIT 1;", (case_id,)
    ).fetchone() is not None
    if has_any_document and _worklist_mod is not None:
        gen = _worklist_mod.case_form_generation(conn, case_id)
        return {"generation": gen, "unknown": gen == "unknown", "label": GENERATION_LABELS.get(gen)}

    return {"generation": None, "unknown": False, "label": None}


def _normalize_value(value_num: float | None, value_text: str | None) -> Any:
    """A comparable key for "do these two candidates actually disagree".
    Numbers compare numerically (rounded to tame float noise); text compares
    case/whitespace-insensitively. A candidate with neither is excluded from
    the disagreement check entirely (nothing to compare)."""
    if value_num is not None:
        return ("num", round(float(value_num), 6))
    if value_text is not None and value_text.strip():
        return ("text", value_text.strip().casefold())
    return None


def _field_def_public(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["unresolved"] = bool(d["unresolved"])
    try:
        d["required_json"] = json.loads(d["required_json"]) if d.get("required_json") else None
    except (TypeError, ValueError):
        d["required_json"] = None
    try:
        d["footnote_refs"] = json.loads(d["footnote_refs"]) if d.get("footnote_refs") else []
    except (TypeError, ValueError):
        d["footnote_refs"] = []
    return d


def _citation_text(field_def_row: sqlite3.Row, *, style: str = "long") -> str | None:
    """Renders field_defs.citation_json through app/citation.py — CONTRACT.md
    §5.1: NEVER a stored string, always re-rendered from the struct."""
    raw = field_def_row["citation_json"] if "citation_json" in field_def_row.keys() else None
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return citation_mod.render(citation_mod.Citation(**data), style=style)
    except (TypeError, ValueError, KeyError):
        # A malformed/legacy citation_json blob must never crash the review
        # screen (CONTRACT.md's "honest blanks beat confident guesses"
        # spirit) — the field still renders, just without a citation line.
        return None


def _candidate_public(
    row: sqlite3.Row,
    *,
    docs_by_id: dict[str, dict[str, Any]],
    pages_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    d = dict(row)
    doc = docs_by_id.get(d.get("document_id"))
    page = pages_by_id.get(d.get("page_id"))
    d["document_title"] = doc["title"] if doc else None
    d["document_kind"] = doc["kind"] if doc else None
    d["document_source_priority"] = doc["source_priority"] if doc else None
    d["document_blob_id"] = doc["blob_id"] if doc else None
    d["page_number"] = page["page_number"] if page else None
    d["thumb_blob_id"] = page.get("thumb_blob_id") if page else None
    try:
        d["bbox"] = json.loads(d["bbox_json"]) if d.get("bbox_json") else None
    except (TypeError, ValueError):
        d["bbox"] = None
    try:
        d["provenance"] = json.loads(d["provenance_json"]) if d.get("provenance_json") else {}
    except (TypeError, ValueError):
        d["provenance"] = {}
    return d


def _load_doc_and_page_lookups(
    conn: sqlite3.Connection, case_id: str,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    docs_by_id = {
        r["id"]: dict(r)
        for r in conn.execute(
            "SELECT id, title, kind, source_priority, blob_id FROM documents WHERE case_id = ?;", (case_id,)
        ).fetchall()
    }
    pages_by_id = {
        r["id"]: dict(r)
        for r in conn.execute(
            """
            SELECT p.id, p.document_id, p.page_number, p.thumb_blob_id
            FROM pages p JOIN documents d ON d.id = p.document_id
            WHERE d.case_id = ?;
            """,
            (case_id,),
        ).fetchall()
    }
    return docs_by_id, pages_by_id


# --------------------------------------------------------------------------- #
# list_case_fields — the review screen's primary read.
# --------------------------------------------------------------------------- #


def list_case_fields(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Every (field_def, subject_key) pair this case has EVIDENCE or a
    DECISION for, each with: the field_def (label/citation/unit), every
    candidate ordered by source_priority DESC (CONTRACT.md §3.6 — the
    highest-priority source sorts first, but is never auto-selected), the
    current field_values row if a human has already decided this field, and
    a computed `contested` flag (see module docstring).
    """
    _get_case_row(conn, case_id)

    pairs = conn.execute(
        """
        SELECT field_def_id, subject_key FROM field_candidates WHERE case_id = ?
        UNION
        SELECT field_def_id, subject_key FROM field_values WHERE case_id = ?
        ORDER BY 1, 2;
        """,
        (case_id, case_id),
    ).fetchall()

    docs_by_id, pages_by_id = _load_doc_and_page_lookups(conn, case_id)

    out: list[dict[str, Any]] = []
    for pr in pairs:
        field_def_id = pr["field_def_id"]
        subject_key = pr["subject_key"]

        fd_row = conn.execute("SELECT * FROM field_defs WHERE id = ?;", (field_def_id,)).fetchone()
        if fd_row is None:
            # Defensive only — field_candidates.field_def_id is ON DELETE
            # RESTRICT, so a dangling reference should not be reachable.
            continue

        cand_rows = conn.execute(
            """
            SELECT * FROM field_candidates
            WHERE case_id = ? AND field_def_id = ? AND subject_key IS ?
            ORDER BY source_priority DESC, (confidence IS NULL) ASC, confidence DESC, created_at ASC;
            """,
            (case_id, field_def_id, subject_key),
        ).fetchall()
        candidates = [
            _candidate_public(c, docs_by_id=docs_by_id, pages_by_id=pages_by_id) for c in cand_rows
        ]

        normalized = {_normalize_value(c["value_num"], c["value_text"]) for c in candidates}
        normalized.discard(None)
        disagreement = len(normalized) > 1

        value_row = conn.execute(
            "SELECT * FROM field_values WHERE case_id = ? AND field_def_id = ? AND subject_key IS ?;",
            (case_id, field_def_id, subject_key),
        ).fetchone()
        value = dict(value_row) if value_row is not None else None

        stored_state = value["state"] if value is not None else None
        # Undecided evidence that disagrees reads as "contested" even before
        # any field_values row exists (THE CENTRAL DESIGN PRINCIPLE: a
        # candidate is evidence, not an answer -- there is nothing to
        # "become unconfirmed" until a human looks). Once a human has
        # RECORDED a decision (any state other than 'contested'), the field
        # is no longer presented as contested, even if the evidence still
        # technically disagrees -- that disagreement was the Board's/
        # operator's to resolve, and they did.
        is_contested = disagreement if stored_state in (None, "contested") else False
        display_state = stored_state or ("contested" if is_contested else "unconfirmed")

        out.append({
            "field_def": _field_def_public(fd_row),
            "citation_text": _citation_text(fd_row),
            "subject_key": subject_key,
            "candidates": candidates,
            "value": value,
            "display_state": display_state,
            "contested": is_contested,
        })

    out.sort(
        key=lambda r: (
            r["field_def"].get("panel_title") or "",
            r["field_def"].get("sort_order") or 0,
            r["field_def"]["label"],
            r["subject_key"] or "",
        )
    )
    return out


def get_case_field(
    conn: sqlite3.Connection, case_id: str, field_def_id: str, subject_key: str | None,
) -> dict[str, Any] | None:
    """One field's full review-screen row (same shape as a list_case_fields()
    entry) — used by the action endpoints to return the fresh state of the
    field they just acted on, without the caller re-fetching the whole
    case."""
    for row in list_case_fields(conn, case_id):
        if row["field_def"]["id"] == field_def_id and row["subject_key"] == subject_key:
            return row
    return None


def _find_field_value_row(
    conn: sqlite3.Connection, case_id: str, field_def_id: str, subject_key: str | None,
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM field_values WHERE case_id = ? AND field_def_id = ? AND subject_key IS ?;",
        (case_id, field_def_id, subject_key),
    ).fetchone()


def _require_why(why: str | None) -> str:
    if not why or not why.strip():
        raise ValidationError([{"field": "why", "message": "required (non-empty) -- every decision records why"}])
    return why.strip()


# --------------------------------------------------------------------------- #
# confirm_field — a human picks ONE candidate as the value, as-is.
# --------------------------------------------------------------------------- #


def confirm_field(
    conn: sqlite3.Connection,
    case_id: str,
    *,
    field_def_id: str | None,
    subject_key: str | None,
    candidate_id: str | None,
    why: str | None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """A human confirms ONE candidate, verbatim, as the surviving value.
    Never silently promotes a candidate — this function only runs because a
    human clicked "confirm this" on a specific candidate_id. Writes exactly
    one `field_value.confirmed` events row (actor + why) in the same
    transaction as the field_values write; raises and writes nothing on any
    validation failure (CONTRACT.md §1 S1)."""
    _get_case_row(conn, case_id)

    details: list[dict[str, str]] = []
    if not field_def_id:
        details.append({"field": "field_def_id", "message": "required"})
    if not candidate_id:
        details.append({"field": "candidate_id", "message": "required"})
    if details:
        raise ValidationError(details)
    why_clean = _require_why(why)

    cand = conn.execute(
        "SELECT * FROM field_candidates WHERE id = ? AND case_id = ? AND field_def_id = ? AND subject_key IS ?;",
        (candidate_id, case_id, field_def_id, subject_key),
    ).fetchone()
    if cand is None:
        raise CandidateNotFound(candidate_id)

    now = _utc_now_iso()
    existing = _find_field_value_row(conn, case_id, field_def_id, subject_key)

    conn.execute("BEGIN;")
    try:
        if existing is None:
            value_id = _new_id()
            conn.execute(
                """
                INSERT INTO field_values
                    (id, case_id, field_def_id, subject_key, chosen_candidate_id,
                     value_num, value_text, unit, state, override_reason, contested_with_json,
                     confirmed_by, confirmed_at, created_at, updated_at, actor_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'confirmed', NULL, NULL, ?, ?, ?, ?, ?);
                """,
                (value_id, case_id, field_def_id, subject_key, candidate_id,
                 cand["value_num"], cand["value_text"], cand["unit"],
                 actor_user_id, now, now, now, actor_user_id),
            )
        else:
            value_id = existing["id"]
            conn.execute(
                """
                UPDATE field_values SET
                    chosen_candidate_id = ?, value_num = ?, value_text = ?, unit = ?,
                    state = 'confirmed', override_reason = NULL, contested_with_json = NULL,
                    confirmed_by = ?, confirmed_at = ?, updated_at = ?, actor_user_id = ?
                WHERE id = ?;
                """,
                (candidate_id, cand["value_num"], cand["value_text"], cand["unit"],
                 actor_user_id, now, now, actor_user_id, value_id),
            )

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="field_value.confirmed",
            case_id=case_id,
            entity_table="field_values",
            entity_id=value_id,
            payload={
                "case_id": case_id, "field_def_id": field_def_id, "subject_key": subject_key,
                "field_value_id": value_id, "candidate_id": candidate_id, "why": why_clean,
            },
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return get_case_field(conn, case_id, field_def_id, subject_key)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# override_field — a human types a value that differs from every candidate.
# --------------------------------------------------------------------------- #


def override_field(
    conn: sqlite3.Connection,
    case_id: str,
    *,
    field_def_id: str | None,
    subject_key: str | None,
    value_num: float | None,
    value_text: str | None,
    unit: str | None,
    reason: str | None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """A human replaces whatever the evidence showed with a value they typed
    in — "THE FORM IS WRONG, THE PLAN GOVERNS" in the general case: a real
    surveyed dimension, or a corrected reading of a document, that no single
    candidate stated exactly. `reason` is REQUIRED (field_values' own CHECK
    constraint enforces this at the DB layer too: state='overridden' demands
    a non-NULL override_reason AND confirmed_by). Writes exactly one
    `field_value.overridden` events row in the same transaction."""
    _get_case_row(conn, case_id)

    details: list[dict[str, str]] = []
    if not field_def_id:
        details.append({"field": "field_def_id", "message": "required"})
    if value_num is None and (value_text is None or not str(value_text).strip()):
        details.append({"field": "value", "message": "provide value_num or a non-empty value_text"})
    if not reason or not reason.strip():
        details.append({"field": "reason", "message": "required (non-empty) -- an override must say why"})
    if details:
        raise ValidationError(details)

    reason_clean = reason.strip()  # type: ignore[union-attr]
    value_text_clean = value_text.strip() if isinstance(value_text, str) and value_text.strip() else None

    now = _utc_now_iso()
    existing = _find_field_value_row(conn, case_id, field_def_id, subject_key)

    conn.execute("BEGIN;")
    try:
        if existing is None:
            value_id = _new_id()
            conn.execute(
                """
                INSERT INTO field_values
                    (id, case_id, field_def_id, subject_key, chosen_candidate_id,
                     value_num, value_text, unit, state, override_reason, contested_with_json,
                     confirmed_by, confirmed_at, created_at, updated_at, actor_user_id)
                VALUES (?, ?, ?, ?, NULL, ?, ?, ?, 'overridden', ?, NULL, ?, ?, ?, ?, ?);
                """,
                (value_id, case_id, field_def_id, subject_key,
                 value_num, value_text_clean, unit, reason_clean,
                 actor_user_id, now, now, now, actor_user_id),
            )
        else:
            value_id = existing["id"]
            conn.execute(
                """
                UPDATE field_values SET
                    chosen_candidate_id = NULL, value_num = ?, value_text = ?, unit = ?,
                    state = 'overridden', override_reason = ?, contested_with_json = NULL,
                    confirmed_by = ?, confirmed_at = ?, updated_at = ?, actor_user_id = ?
                WHERE id = ?;
                """,
                (value_num, value_text_clean, unit, reason_clean,
                 actor_user_id, now, now, actor_user_id, value_id),
            )

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="field_value.overridden",
            case_id=case_id,
            entity_table="field_values",
            entity_id=value_id,
            payload={
                "case_id": case_id, "field_def_id": field_def_id, "subject_key": subject_key,
                "field_value_id": value_id, "value_num": value_num, "value_text": value_text_clean,
                "unit": unit, "reason": reason_clean,
            },
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return get_case_field(conn, case_id, field_def_id, subject_key)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# mark_not_applicable — a human decides the standard does not reach this
# proposal at all (distinct from "not_in_application": that is the
# application being SILENT on a field; this is the Code's standard not
# applying here in the first place).
# --------------------------------------------------------------------------- #


def mark_not_applicable(
    conn: sqlite3.Connection,
    case_id: str,
    *,
    field_def_id: str | None,
    subject_key: str | None,
    why: str | None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Writes exactly one `field_value.marked_not_applicable` events row in
    the same transaction as the field_values write. `why` is required at
    this module's boundary (not by the DB CHECK, which only demands a reason
    for 'overridden') because a not-applicable call is still a human
    judgment call the record should be able to explain later."""
    _get_case_row(conn, case_id)

    if not field_def_id:
        raise ValidationError([{"field": "field_def_id", "message": "required"}])
    why_clean = _require_why(why)

    now = _utc_now_iso()
    existing = _find_field_value_row(conn, case_id, field_def_id, subject_key)

    conn.execute("BEGIN;")
    try:
        if existing is None:
            value_id = _new_id()
            conn.execute(
                """
                INSERT INTO field_values
                    (id, case_id, field_def_id, subject_key, chosen_candidate_id,
                     value_num, value_text, unit, state, override_reason, contested_with_json,
                     confirmed_by, confirmed_at, created_at, updated_at, actor_user_id)
                VALUES (?, ?, ?, ?, NULL, NULL, NULL, NULL, 'not_applicable', ?, NULL, ?, ?, ?, ?, ?);
                """,
                (value_id, case_id, field_def_id, subject_key, why_clean,
                 actor_user_id, now, now, now, actor_user_id),
            )
        else:
            value_id = existing["id"]
            conn.execute(
                """
                UPDATE field_values SET
                    chosen_candidate_id = NULL, value_num = NULL, value_text = NULL, unit = NULL,
                    state = 'not_applicable', override_reason = ?, contested_with_json = NULL,
                    confirmed_by = ?, confirmed_at = ?, updated_at = ?, actor_user_id = ?
                WHERE id = ?;
                """,
                (why_clean, actor_user_id, now, now, actor_user_id, value_id),
            )

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="field_value.marked_not_applicable",
            case_id=case_id,
            entity_table="field_values",
            entity_id=value_id,
            payload={
                "case_id": case_id, "field_def_id": field_def_id, "subject_key": subject_key,
                "field_value_id": value_id, "why": why_clean,
            },
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001
        _rollback_and_raise(conn, exc)

    return get_case_field(conn, case_id, field_def_id, subject_key)  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# list_absence_worklist — "~30% of the fields in a real decision are not in
# the application at all." A PEER SURFACE, not a footnote (task brief).
# --------------------------------------------------------------------------- #


#: Display order for ingest/worklist.py's fixed SOURCE_CATEGORIES — matches
#: SOURCE_CATEGORY_LABELS' own definition order; kept here (not derived from
#: the frozenset, which has no order) so the rendered group order is stable.
_SOURCE_CATEGORY_ORDER: tuple[str, ...] = (
    "applicant", "registry", "gis", "plan_survey", "staff", "post_submittal",
)


def list_absence_worklist(conn: sqlite3.Connection, case_id: str, *, actor_user_id: str | None = None) -> dict[str, Any]:
    """"~30% of the fields in a real decision are not in the application at
    all" (task brief) — a PEER SURFACE, not a footnote. Delegates to
    ingest/worklist.py when available (the authoritative implementation:
    seeds the real ~23 case-level fields a Findings draft needs, groups by
    WHERE the value must come from, and materializes
    field_values(state='not_in_application') — see that module's own
    docstring for why that write is a FACT, not a promoted candidate).
    Falls back to a simpler field_defs-only scan, grouped by panel_title,
    if ingest.worklist is ever unavailable — this module still works
    standalone either way, never erroring for a missing sibling.

    Every group's `fields` items share ONE shape regardless of which path
    produced them: {label, citation_text, note, materialized} — see
    _normalize_worklist_group().
    """
    if _worklist_mod is not None:
        try:
            generation = case_form_generation(conn, case_id)["generation"]
            result = _worklist_mod.worklist(
                conn, case_id, actor_user_id=actor_user_id, form_generation=generation,
            )
        except _worklist_mod.CaseNotFound as exc:
            raise CaseNotFound(case_id) from exc

        groups = []
        for cat in _SOURCE_CATEGORY_ORDER:
            cat_items = result["grouped"].get(cat) or []
            if not cat_items:
                continue
            groups.append({
                "source": _worklist_mod.SOURCE_CATEGORY_LABELS.get(cat, cat),
                "fields": [
                    {
                        "label": it["label"],
                        "citation_text": None,  # case-level admin fields carry no Article-2 citation
                        "note": it["reason"],
                        "materialized": True,  # worklist() always materializes what it returns
                    }
                    for it in cat_items
                ],
            })
        return {
            "groups": groups,
            "count": result["summary"]["needed"],
            "headline": result["summary"]["headline"],
        }

    return _list_absence_worklist_fallback(conn, case_id)


def _list_absence_worklist_fallback(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    """Used only when ingest.worklist could not be imported. Every field_def
    this case's ruleset/district scope has that has NO evidence at all (no
    field_candidates, no field_values) — plus any field already explicitly
    decided state='not_in_application' — grouped by `panel_title` (the
    nearest existing schema concept to "source" without ingest.worklist's
    richer source_category). NULL/blank panel_title groups under "General".
    """
    case = _get_case_row(conn, case_id)

    catalogue = conn.execute(
        """
        SELECT * FROM field_defs
        WHERE ruleset_id = ? AND (district_key IS NULL OR district_key = ?)
        ORDER BY panel_title, sort_order, label;
        """,
        (case["ruleset_id"], case["district_key"]),
    ).fetchall()

    present_ids: set[str] = set()
    for r in conn.execute("SELECT DISTINCT field_def_id FROM field_candidates WHERE case_id = ?;", (case_id,)):
        present_ids.add(r["field_def_id"])
    for r in conn.execute("SELECT DISTINCT field_def_id FROM field_values WHERE case_id = ?;", (case_id,)):
        present_ids.add(r["field_def_id"])

    not_in_app_by_field: dict[str, dict[str, Any]] = {
        r["field_def_id"]: dict(r)
        for r in conn.execute(
            "SELECT * FROM field_values WHERE case_id = ? AND state = 'not_in_application';", (case_id,)
        ).fetchall()
    }

    groups: dict[str, list[dict[str, Any]]] = {}
    for fd in catalogue:
        materialized = fd["id"] in not_in_app_by_field
        if fd["id"] in present_ids and not materialized:
            continue  # some evidence or decision already exists for it
        source = fd["panel_title"] or "General"
        fv = not_in_app_by_field.get(fd["id"])
        note = (
            f"recorded not-in-application — {fv['override_reason']}" if (materialized and fv and fv.get("override_reason"))
            else "recorded not-in-application" if materialized
            else "no candidate from any source"
        )
        groups.setdefault(source, []).append({
            "label": fd["label"],
            "citation_text": _citation_text(fd),
            "note": note,
            "materialized": materialized,
        })

    # NOTE: the per-group key is deliberately "fields", not "items" -- a
    # dict with a key literally named "items" collides with Python's own
    # dict.items() in Jinja2's attribute-then-subscript lookup (`group.items`
    # silently resolves to the bound METHOD, not this list, and only fails
    # loudly at render time with a cryptic "no len()" TypeError). Named this
    # way from the start rather than patched around it in the template.
    ordered = [{"source": k, "fields": v} for k, v in sorted(groups.items())]
    return {"groups": ordered, "count": sum(len(g["fields"]) for g in ordered), "headline": None}
