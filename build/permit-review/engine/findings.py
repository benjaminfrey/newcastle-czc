"""Implements CONTRACT.md §3.6 (findings_nodes) plus its 0013_findings_tree.sql
additions (quoted_standard_text, finding_source, applicability_verdict,
citation_display) -- the W6 "findings tree" task brief.

Pure business logic + DB access -- no FastAPI, no HTTP status codes, no JSON
envelope. Mirrors the split app/cases.py already established (business logic
in a plain module; a thin app/routes/*.py layer, not built in this task,
would translate to/from HTTP later). Lives in engine/, not app/, because
CONTRACT.md §2's directory layout names engine/ as the home for
"rules -> criteria sets -> findings_nodes" -- the same reasoning
engine/deadlines.py's own module docstring gives for where the real
statutory-clock logic lives.

THE FRAMING RULE, IN CODE, NOT JUST IN COMMENTS
------------------------------------------------
CONTRACT.md's framing rule: "The app MUST NEVER state, imply, or store that a
standard *is met* or *is not met* -- that is the Board acting." create_node()
and amend_node() below have NO parameter for `conclusion` -- not "a parameter
that defaults to None", no parameter at all. There is no call shape in this
module that can set findings_nodes.conclusion to anything but the NULL every
INSERT already gives it. A future human-facing "the Board voted" endpoint
sets it directly with UPDATE, never through this module.

THE AMENDMENT MODEL
--------------------
CONTRACT.md §3.6: "An amendment INSERTs a new revision and points the old
row's superseded_by at it. Nothing is ever overwritten and nothing is ever
deleted." amend_node() below does exactly that, inside one transaction, and
appends exactly ONE `events` row for the whole amendment (one logical
mutation, matching the "one INSERT + one events row" shape app/cases.py's
create_case() already established for a single-row mutation) even though it
performs two writes (INSERT the new revision, UPDATE the old row's
superseded_by). findings_nodes' own trg_findings_supersede_once trigger
(0001_init.sql, unchanged by 0013) is the DB-level backstop: it raises if
anything ever tries to point an already-superseded row's superseded_by
somewhere else, so a bug here that tried to re-amend a stale revision would
fail loudly rather than silently rewriting history.

root_id is set to the node's OWN id at first creation (create_node()) and
copied forward unchanged by every amend_node() call -- "stable identity
across revisions" (0001_init.sql's own comment). get_revision_chain(root_id)
walks every revision that has ever existed under that identity, current or
superseded, oldest first; the chain is provably walkable because each row's
superseded_by literally IS the next row's id (asserted in
tests/test_findings.py by following the pointers, not just by querying
root_id).

PROVENANCE
----------
provenance_json is NOT a free-form bag. validate_provenance() below enforces
CONTRACT.md §3.6's own list of what a well-formed provenance object contains
("document_id + page, field_value_id, rule_id, citation, and for LLM-assisted
text the model, prompt hash and generation id") PLUS the W6 brief's
finding_source requirement layered on top:

    - finding_source == 'engine'   -> provenance must trace to at least one
      of rule_id / citation / a document+page pair -- deterministic engine
      output that cites nothing is a bug, not a finding.
    - finding_source == 'model'    -> provenance must carry a `model` object
      with provider, model id and prompt_sha256 (never prompt text -- same
      discipline as llm/events.py's record_llm_call(), CONTRACT.md §9.5).
    - finding_source == 'operator' -> provenance must carry an `operator`
      object naming who typed it.

And regardless of finding_source: any node carrying `body` or
quoted_standard_text must carry a NON-TRIVIAL provenance_json --
0013_findings_tree.sql enforces the trivial-`{}` half of that as a DB CHECK;
validate_provenance() enforces the shape half, so a caller gets a clear
ValidationError instead of a bare SQLite IntegrityError.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.audit import append_event
from app.citation import Citation
from app.citation import render as citation_render

# --------------------------------------------------------------------------- #
# Vocabulary -- single source of truth for this module; the CHECK constraints
# in 0001_init.sql / 0013_findings_tree.sql are the DB-level mirror, kept in
# sync by hand the same way app/cases.py's own vocabulary block says its
# lists are (small, stable, reviewed-together-with-a-migration).
# --------------------------------------------------------------------------- #

NODE_TYPES: frozenset[str] = frozenset({
    "section", "required_review", "finding", "conclusion",
    "condition_ref", "question", "note",
})

APPLICABILITY_VERDICTS: frozenset[str] = frozenset({"true", "false", "unknown"})

FINDING_SOURCES: frozenset[str] = frozenset({"engine", "model", "operator"})

#: Sentinel distinguishing "caller did not pass this" (carry the prior
#: revision's value forward on amend_node()) from "caller passed None"
#: (clear the field in the new revision). A bare `None` default can't do
#: this job because None is itself a legal value for almost every column
#: here.
_UNSET: Any = object()


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class ValidationError(ValueError):
    def __init__(self, details: list[dict[str, str]]):
        self.details = details
        super().__init__(f"findings validation failed: {details!r}")


class NodeNotFound(KeyError):
    def __init__(self, node_id: str):
        self.node_id = node_id
        super().__init__(f"findings_nodes row {node_id!r} not found")


class NotCurrentRevision(ValueError):
    """Raised by amend_node() when the target node is not the live tip of
    its revision chain (its superseded_by is already set) -- amending a
    stale revision would race the trg_findings_supersede_once trigger and,
    worse, silently orphan whatever amendment already superseded it."""

    def __init__(self, node_id: str, current_id: str):
        self.node_id = node_id
        self.current_id = current_id
        super().__init__(
            f"findings_nodes row {node_id!r} is not the current revision "
            f"(superseded by {current_id!r}); amend the current revision instead"
        )


# --------------------------------------------------------------------------- #
# Small internal helpers -- mirrors app/cases.py's own _new_id/_utc_now_iso/
# _rollback_and_raise exactly.
# --------------------------------------------------------------------------- #


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    """ISO-8601 UTC, 'Z' suffix, millisecond precision -- CONTRACT.md §3.3/§3.4."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _rollback_and_raise(conn: sqlite3.Connection, exc: BaseException) -> None:
    if conn.in_transaction:
        conn.execute("ROLLBACK;")
    raise exc


def _citation_to_struct(citation: Citation | dict | None) -> Citation | None:
    if citation is None:
        return None
    if isinstance(citation, Citation):
        return citation
    return Citation(**citation)


def _citation_json(citation: Citation | None) -> str | None:
    if citation is None:
        return None
    return json.dumps(dataclasses.asdict(citation), sort_keys=True, ensure_ascii=False)


def _provenance_json(provenance: dict | None) -> str:
    # Same reproducible serialization discipline as app/audit.py's events
    # payload (CONTRACT.md §3.3) -- not hashed here, but consistency of
    # form matters for anyone diffing two revisions' provenance by eye.
    return json.dumps(provenance or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------- #
# Provenance validation
# --------------------------------------------------------------------------- #


def validate_provenance(
    provenance: dict | None,
    *,
    finding_source: str | None,
    has_prose: bool,
) -> list[dict[str, str]]:
    """Returns a list of {"field": ..., "message": ...} validation problems
    (empty list = valid). Never raises itself -- callers turn a non-empty
    result into ValidationError so every problem is reported at once
    (mirrors app/cases.py's create_case() details[] pattern).

    CONTRACT.md §3.6's own provenance_json comment lists what belongs in it:
    document_id + page, field_value_id, rule_id, citation, and for
    LLM-assisted text the model, prompt hash and generation id. This checks
    the SHAPE of whichever of those a given node claims, not that every
    field is always present -- a pure Code-quote node with no field_value at
    all is legitimate; a node with no traceable source at all is not.
    """
    details: list[dict[str, str]] = []
    prov = provenance or {}

    if has_prose and not prov:
        details.append({
            "field": "provenance_json",
            "message": "a node with quoted_standard_text or body must carry non-empty provenance "
                       "(CONTRACT.md §3.6: 'a node with prose and an empty provenance object is a bug')",
        })
        return details  # nothing further to check against an empty object

    if finding_source == "engine":
        if not (prov.get("rule_id") or prov.get("citation") or prov.get("document_id")):
            details.append({
                "field": "provenance_json",
                "message": "finding_source='engine' requires provenance to trace to at least one "
                           "of rule_id, citation, or document_id -- deterministic output that cites "
                           "nothing is a bug, not a finding",
            })

    elif finding_source == "model":
        model = prov.get("model")
        if not isinstance(model, dict):
            details.append({
                "field": "provenance_json.model",
                "message": "finding_source='model' requires a provenance.model object "
                           "({provider, model, prompt_sha256[, generation_id]})",
            })
        else:
            for key in ("provider", "model", "prompt_sha256"):
                if not model.get(key):
                    details.append({
                        "field": f"provenance_json.model.{key}",
                        "message": f"required for finding_source='model' (never the prompt text itself "
                                   f"-- CONTRACT.md §9.5's same discipline)",
                    })
            if "prompt_text" in model or "prompt" in model:
                details.append({
                    "field": "provenance_json.model",
                    "message": "must never carry raw prompt text (CONTRACT.md §9.5) -- store prompt_sha256 only",
                })

    elif finding_source == "operator":
        operator = prov.get("operator")
        if not isinstance(operator, dict) or not operator.get("user_id"):
            details.append({
                "field": "provenance_json.operator",
                "message": "finding_source='operator' requires a provenance.operator object "
                           "with at least {user_id}",
            })

    if "page" in prov and prov["page"] is not None and not isinstance(prov["page"], int):
        details.append({
            "field": "provenance_json.page",
            "message": "page, if present, must be an integer page number",
        })

    return details


# --------------------------------------------------------------------------- #
# Row shaping
# --------------------------------------------------------------------------- #

_JSON_COLUMNS = ("citation_json", "provenance_json")


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["unresolved"] = bool(d["unresolved"])
    for col in _JSON_COLUMNS:
        if d.get(col) is not None:
            d[col] = json.loads(d[col])
    return d


def get_node(conn: sqlite3.Connection, node_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM findings_nodes WHERE id = ?;", (node_id,)).fetchone()
    return _row_to_dict(row) if row is not None else None


def get_current_nodes_for_case(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """The live tree for a case -- every node WHERE superseded_by IS NULL,
    in print order (CONTRACT.md §3.6: "The current tree is
    WHERE superseded_by IS NULL")."""
    rows = conn.execute(
        "SELECT * FROM findings_nodes WHERE case_id = ? AND superseded_by IS NULL ORDER BY sort_order;",
        (case_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_revision_chain(conn: sqlite3.Connection, root_id: str) -> list[dict[str, Any]]:
    """Every revision ever recorded under one stable root_id, oldest first
    (current AND superseded). Nothing filters superseded rows here -- this
    is the audit view, not the print view (use get_current_nodes_for_case()
    or get_current_node_for_root() for that)."""
    rows = conn.execute(
        "SELECT * FROM findings_nodes WHERE root_id = ? ORDER BY revision ASC;",
        (root_id,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_current_node_for_root(conn: sqlite3.Connection, root_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM findings_nodes WHERE root_id = ? AND superseded_by IS NULL;", (root_id,)
    ).fetchone()
    return _row_to_dict(row) if row is not None else None


# --------------------------------------------------------------------------- #
# create_node
# --------------------------------------------------------------------------- #


def create_node(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    node_type: str,
    case_review_id: str | None = None,
    parent_id: str | None = None,
    sort_order: int = 0,
    number_label: str | None = None,
    heading: str | None = None,
    quoted_standard_text: str | None = None,
    body: str | None = None,
    finding_source: str | None = None,
    rule_id: str | None = None,
    criteria_set_id: str | None = None,
    field_value_id: str | None = None,
    citation: Citation | dict | None = None,
    applicability_verdict: str | None = None,
    unresolved: bool = True,
    board_question: str | None = None,
    placeholder: str | None = None,
    provenance: dict | None = None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    """Insert a brand-new finding, revision 1, as its own root_id (stable
    identity for every future amend_node() call against it). Writes exactly
    one `events` row (kind='findings_node.created') in the same transaction
    as the INSERT; a raised exception writes nothing.

    No `conclusion` parameter exists -- see this module's docstring. The row
    always inserts with conclusion/conclusion_by/conclusion_at NULL.
    """
    details: list[dict[str, str]] = []

    if node_type not in NODE_TYPES:
        details.append({"field": "node_type", "message": f"must be one of {sorted(NODE_TYPES)}"})
    if finding_source is not None and finding_source not in FINDING_SOURCES:
        details.append({"field": "finding_source", "message": f"must be one of {sorted(FINDING_SOURCES)} or None"})
    if applicability_verdict is not None and applicability_verdict not in APPLICABILITY_VERDICTS:
        details.append({
            "field": "applicability_verdict",
            "message": f"must be one of {sorted(APPLICABILITY_VERDICTS)} or None",
        })
    if finding_source is not None and body is None:
        details.append({
            "field": "finding_source",
            "message": "finding_source claims authorship of `body`, but body is empty",
        })

    has_prose = bool(body) or bool(quoted_standard_text)
    details.extend(validate_provenance(provenance, finding_source=finding_source, has_prose=has_prose))

    if details:
        raise ValidationError(details)

    citation_struct = _citation_to_struct(citation)
    citation_json = _citation_json(citation_struct)
    citation_display = citation_render(citation_struct) if citation_struct is not None else None

    node_id = _new_id()
    now = _utc_now_iso()
    provenance_json = _provenance_json(provenance)

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO findings_nodes (
                id, case_id, case_review_id, parent_id, root_id, revision, superseded_by,
                sort_order, node_type, number_label, heading, quoted_standard_text, body,
                finding_source, rule_id, criteria_set_id, field_value_id, citation_json,
                citation_display, applicability_verdict, conclusion, conclusion_by, conclusion_at,
                unresolved, board_question, placeholder, provenance_json, created_at, actor_user_id
            ) VALUES (
                ?, ?, ?, ?, ?, 1, NULL,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, NULL, NULL, NULL,
                ?, ?, ?, ?, ?, ?
            );
            """,
            (
                node_id, case_id, case_review_id, parent_id, node_id,
                sort_order, node_type, number_label, heading, quoted_standard_text, body,
                finding_source, rule_id, criteria_set_id, field_value_id, citation_json,
                citation_display, applicability_verdict,
                int(unresolved), board_question, placeholder, provenance_json, now, actor_user_id,
            ),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="findings_node.created",
            payload={
                "node_id": node_id,
                "root_id": node_id,
                "revision": 1,
                "case_id": case_id,
                "node_type": node_type,
                "finding_source": finding_source,
                "applicability_verdict": applicability_verdict,
                "unresolved": bool(unresolved),
            },
            case_id=case_id,
            entity_table="findings_nodes",
            entity_id=node_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: roll back, then re-raise unchanged
        _rollback_and_raise(conn, exc)

    return get_node(conn, node_id)  # type: ignore[return-value]  -- just inserted, always found


# --------------------------------------------------------------------------- #
# amend_node
# --------------------------------------------------------------------------- #


def amend_node(
    conn: sqlite3.Connection,
    *,
    node_id: str,
    actor_user_id: str | None,
    reason: str | None = None,
    sort_order: Any = _UNSET,
    number_label: Any = _UNSET,
    heading: Any = _UNSET,
    quoted_standard_text: Any = _UNSET,
    body: Any = _UNSET,
    finding_source: Any = _UNSET,
    rule_id: Any = _UNSET,
    criteria_set_id: Any = _UNSET,
    field_value_id: Any = _UNSET,
    citation: Any = _UNSET,
    applicability_verdict: Any = _UNSET,
    unresolved: Any = _UNSET,
    board_question: Any = _UNSET,
    placeholder: Any = _UNSET,
    provenance: Any = _UNSET,
) -> dict[str, Any]:
    """Amend `node_id` (which MUST be the current revision -- superseded_by
    IS NULL -- else NotCurrentRevision). INSERTs a new row with
    revision = old.revision + 1, sharing the same root_id/case_id/
    case_review_id/parent_id/node_type as the row it amends (those identify
    WHAT this node is, not its content, and are not amendable through this
    function), then UPDATEs the old row's superseded_by to point at the new
    row's id. Nothing is ever overwritten and nothing is ever deleted
    (CONTRACT.md §3.6).

    Any content parameter left unpassed carries the prior revision's value
    forward unchanged (see _UNSET above); pass a field explicitly (including
    `None`) to change or clear it in the new revision.

    Writes exactly ONE `events` row (kind='findings_node.amended') for the
    whole amendment, in the same transaction as both writes -- one logical
    mutation, matching CONTRACT.md §3.3 ("every mutation appends an events
    row in the same transaction").
    """
    old = get_node(conn, node_id)
    if old is None:
        raise NodeNotFound(node_id)
    if old["superseded_by"] is not None:
        raise NotCurrentRevision(node_id, old["superseded_by"])

    def _resolve(new_value: Any, old_key: str) -> Any:
        return old[old_key] if new_value is _UNSET else new_value

    node_type = old["node_type"]  # identity, not amendable here
    new_sort_order = _resolve(sort_order, "sort_order")
    new_number_label = _resolve(number_label, "number_label")
    new_heading = _resolve(heading, "heading")
    new_quoted_standard_text = _resolve(quoted_standard_text, "quoted_standard_text")
    new_body = _resolve(body, "body")
    new_finding_source = _resolve(finding_source, "finding_source")
    new_rule_id = _resolve(rule_id, "rule_id")
    new_criteria_set_id = _resolve(criteria_set_id, "criteria_set_id")
    new_field_value_id = _resolve(field_value_id, "field_value_id")
    new_applicability_verdict = _resolve(applicability_verdict, "applicability_verdict")
    new_unresolved = _resolve(unresolved, "unresolved")
    new_board_question = _resolve(board_question, "board_question")
    new_placeholder = _resolve(placeholder, "placeholder")

    if citation is _UNSET:
        # old["citation_json"] is already the deserialized dict (_row_to_dict);
        # round-trip it back into a Citation so render() can recompute the
        # cache the same way create_node() does, rather than trusting the
        # OLD citation_display cache forward unchanged.
        citation_struct = Citation(**old["citation_json"]) if old["citation_json"] is not None else None
    else:
        citation_struct = _citation_to_struct(citation)

    if provenance is _UNSET:
        new_provenance = old["provenance_json"]
    else:
        new_provenance = provenance

    details: list[dict[str, str]] = []
    if new_finding_source is not None and new_finding_source not in FINDING_SOURCES:
        details.append({"field": "finding_source", "message": f"must be one of {sorted(FINDING_SOURCES)} or None"})
    if new_applicability_verdict is not None and new_applicability_verdict not in APPLICABILITY_VERDICTS:
        details.append({
            "field": "applicability_verdict",
            "message": f"must be one of {sorted(APPLICABILITY_VERDICTS)} or None",
        })
    if new_finding_source is not None and new_body is None:
        details.append({
            "field": "finding_source",
            "message": "finding_source claims authorship of `body`, but body is empty",
        })

    has_prose = bool(new_body) or bool(new_quoted_standard_text)
    details.extend(validate_provenance(new_provenance, finding_source=new_finding_source, has_prose=has_prose))

    if details:
        raise ValidationError(details)

    citation_json = _citation_json(citation_struct)
    citation_display = citation_render(citation_struct) if citation_struct is not None else None

    new_id = _new_id()
    now = _utc_now_iso()
    new_revision = old["revision"] + 1
    provenance_json = _provenance_json(new_provenance)

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO findings_nodes (
                id, case_id, case_review_id, parent_id, root_id, revision, superseded_by,
                sort_order, node_type, number_label, heading, quoted_standard_text, body,
                finding_source, rule_id, criteria_set_id, field_value_id, citation_json,
                citation_display, applicability_verdict, conclusion, conclusion_by, conclusion_at,
                unresolved, board_question, placeholder, provenance_json, created_at, actor_user_id
            ) VALUES (
                ?, ?, ?, ?, ?, ?, NULL,
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, NULL, NULL, NULL,
                ?, ?, ?, ?, ?, ?
            );
            """,
            (
                new_id, old["case_id"], old["case_review_id"], old["parent_id"], old["root_id"],
                new_revision,
                new_sort_order, node_type, new_number_label, new_heading,
                new_quoted_standard_text, new_body,
                new_finding_source, new_rule_id, new_criteria_set_id, new_field_value_id, citation_json,
                citation_display, new_applicability_verdict,
                int(bool(new_unresolved)), new_board_question, new_placeholder, provenance_json,
                now, actor_user_id,
            ),
        )
        conn.execute(
            "UPDATE findings_nodes SET superseded_by = ? WHERE id = ?;",
            (new_id, node_id),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="findings_node.amended",
            payload={
                "root_id": old["root_id"],
                "old_node_id": node_id,
                "new_node_id": new_id,
                "old_revision": old["revision"],
                "new_revision": new_revision,
                "reason": reason,
                "finding_source": new_finding_source,
                "applicability_verdict": new_applicability_verdict,
                "unresolved": bool(new_unresolved),
            },
            case_id=old["case_id"],
            entity_table="findings_nodes",
            entity_id=new_id,
        )
        conn.execute("COMMIT;")
    except Exception as exc:  # noqa: BLE001 -- deliberately broad: roll back, then re-raise unchanged
        _rollback_and_raise(conn, exc)

    return get_node(conn, new_id)  # type: ignore[return-value]  -- just inserted, always found
