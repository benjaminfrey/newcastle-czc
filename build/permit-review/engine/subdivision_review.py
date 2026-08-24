"""The W6 RECONCILIATION glue: the full subdivision criteria walk.

The four W6 workstreams (criteria set + gate, review engine core, findings
tree, draft renderer) were each built and tested in isolation, and each of
their own build reports says so explicitly -- e.g. render/case_findings.py's
own docstring: "It does not decide applicability, does not run the
deterministic engine ... Those are engine/'s job (W6 items 1-4)." No prior
session wrote the piece that actually calls engine.applicability +
engine.review for every one of the 21 subdivision standards and turns the
result into findings_nodes rows. This module is that piece.

THE FRAMING RULE governs this module exactly as it governs every other W6
piece: nothing here ever writes findings_nodes.conclusion (create_node() has
no parameter for it), and no code path here drops a criterion. `run_walk()`
always produces exactly one 'finding' node per rule in the criteria set,
regardless of applicability verdict or kind -- the same "same length in,
same length out" guarantee engine.applicability.gate_all() already makes
mechanically, carried one level up.

DISPATCH, per rule, in this order:
  1. Applicability gate (engine.applicability.gate_one). FALSE or UNKNOWN
     render immediately, using the gate's own finding_text/board_question --
     never reaching kind-specific dispatch. UNKNOWN never suppresses the
     node (W6 brief); the same is true of FALSE here -- CONTRACT.md's
     framing rule that "not applicable" is a stated fact, not a silent
     omission.
  2. TRUE -> dispatch by `kind`:
       - judgement  -> engine.review.evaluate_judgement_criterion() (always
         a first-person question; there is no fact to compute).
       - procedural -> a short cross-reference note (unresolved=False) --
         a. and b. are pointers to the rest of the Code / the RDEO, not
         independently testable; matches both real subdivision samples.
       - numeric / boolean -> if `facts` carries the specific value this
         standard needs, render a real fact/comparison; otherwise an honest
         blank -- a first-person question via
         engine.review.render_judgement_question() (the same guard-clean
         "ask, don't guess" primitive judgement criteria use; nothing about
         that helper is judgement-specific, it just asks).
  3. Independently of (1)/(2): a rule carrying `mandates_condition` (only
     n., Flood Areas) ALSO fires engine.review.fire_flood_condition()
     unconditionally and writes a `conditions` row -- CONTRACT.md's own
     framing ("a mandatory condition ... is not a merits verdict... it is
     boilerplate that rides along with every subdivision regardless of
     outcome") and ruleset_build/build_subdivision_criteria.py's own
     comment that this is "a SEPARATE, unconditional instruction ... not a
     substitute for" n's own applicability-gated finding.

Every node this module writes has finding_source='engine' and provenance
tracing to rule_id (engine.findings.validate_provenance()'s own
requirement for that finding_source).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from app.audit import append_event
from app.citation import Citation, render as citation_render

from engine import applicability, review
from engine.findings import create_node

_CITATION_FIELDS = (
    "ruleset_key", "scheme", "article", "section", "subsection",
    "district_key", "district_code", "district_name", "panel_title", "label",
    "use_label", "exhibit", "table", "section_title", "standard_letter",
    "standard_title", "table_title",
)


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def load_rules_for_criteria_set(conn: sqlite3.Connection, criteria_set_id: str) -> list[dict[str, Any]]:
    """DB `rules` rows for one criteria_set, in sort_order, reshaped into
    the same plain-dict shape ruleset_build/build_subdivision_criteria.py's
    artifact uses (standard_letter, kind, applicability, citation, ...) --
    so engine.applicability.gate_one() (built and tested against that
    artifact shape) works unchanged against real DB-seeded rules.
    """
    rows = conn.execute(
        """
        SELECT r.* FROM rules r
        JOIN criteria_set_rules csr ON csr.rule_id = r.id
        WHERE csr.criteria_set_id = ?
        ORDER BY csr.sort_order;
        """,
        (criteria_set_id,),
    ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        citation = json.loads(row["citation_json"]) if row["citation_json"] else {}
        out.append({
            "id": row["id"],
            "rule_key": row["rule_key"],
            "standard_letter": row["rule_key"].rsplit(".", 1)[-1],
            "kind": row["kind"],
            "title": row["title"],
            "code_text": row["code_text"],
            "citation": citation,
            "citation_display": None,
            "applicability": json.loads(row["applicability_json"]) if row["applicability_json"] else {"op": "always"},
            "mandates_condition": (
                json.loads(row["mandates_condition_json"]) if row["mandates_condition_json"] else None
            ),
            "sort_order": row["sort_order"],
        })
    return out


def _citation_struct(citation: dict[str, Any], *, default_ruleset_key: str) -> Citation | None:
    if not citation:
        return None
    filtered = {k: v for k, v in citation.items() if k in _CITATION_FIELDS}
    filtered.setdefault("ruleset_key", default_ruleset_key)
    filtered.setdefault("scheme", default_ruleset_key if default_ruleset_key in ("adopted", "draft") else "adopted")
    if "article" not in filtered:
        return None
    return Citation(**filtered)


def _citation_display_for(citation: dict[str, Any], *, default_ruleset_key: str) -> str | None:
    c = _citation_struct(citation, default_ruleset_key=default_ruleset_key)
    if c is None:
        return None
    # Mirrors render/case_findings.py's own fix (W6 reconciliation pass):
    # render() drops standard_letter/standard_title by design (app/citation.py's
    # own Citation docstring), so a lettered Article 7 standard needs
    # render_citation() to reproduce "Article 7, Section 12, Standard n.
    # (Flood Areas)". Same-scheme, so this can never raise NoCounterpart.
    from app import citation as citation_mod
    if c.standard_letter:
        return citation_mod.render_citation(c, scheme=default_ruleset_key, style="short")
    return citation_mod.render(c, style="short")


def _dispatch_true(rule: dict[str, Any], facts: dict[str, Any], citation_display: str | None) -> review.Finding:
    kind = rule["kind"]
    letter = rule["standard_letter"]
    title = rule["title"]
    code_text = rule["code_text"]

    if kind == "judgement":
        return review.evaluate_judgement_criterion(
            rule_category=letter, subject="the proposed subdivision",
            code_text=code_text, citation_display=citation_display,
        )

    if kind == "procedural":
        note = (
            f"Standard {letter}. ({title}) incorporates {title.rstrip('.')} by reference; "
            "it is not independently tested here."
        )
        return review.evaluate_procedural_reference(rule_category=letter, note=note)

    # numeric / boolean: only fires a real fact/comparison if `facts`
    # carries what this specific standard needs. Only rule r (Spaghetti-
    # Lots) is numeric among the 21, and it needs a case-specific ratio;
    # o/p/u are boolean record-completeness facts. Neither is ever
    # invented -- an absent fact is an honest blank, not a guess.
    known = facts.get(f"standard.{letter}.value")
    if kind == "numeric" and known is not None:
        test = known  # {"proposed": float, "required": float, "unit": str, "comparator": str}
        return review.evaluate_numeric_criterion(
            label=title, rule_category=letter,
            proposed=test["proposed"], required=test["required"],
            unit=test.get("unit", ""), comparator=test.get("comparator", "<="),
            citation=citation_display,
        )
    if kind == "boolean" and known is not None:
        stated = "established" if known else "not established"
        return review.Finding(
            rule_category=letter,
            disposition=review.Disposition.FACT_RECORDED,
            unresolved=True,
            body=f"The record has {stated} the fact standard {letter}. ({title}) asks about.",
            board_question=f"What is the Board's finding on standard {letter}. ({title})?",
        )

    # Honest blank -- the record does not yet establish the value this
    # standard needs. Same guard-clean "ask, don't guess" primitive as a
    # judgement question; nothing about it is judgement-specific.
    return review.Finding(
        rule_category=letter,
        disposition=review.Disposition.BOARD_QUESTION,
        unresolved=True,
        body=None,
        board_question=review.render_judgement_question(
            subject="the proposed subdivision", code_text=code_text, citation_display=citation_display,
        ),
    )


def _finding_for_rule(rule: dict[str, Any], facts: dict[str, Any], *, default_ruleset_key: str) -> tuple[review.Finding, str]:
    """Returns (Finding, applicability_verdict) for one rule -- steps 1-2 of
    the module docstring's dispatch. Always returns something; never raises
    for an ordinary absent fact."""
    citation_display = _citation_display_for(rule["citation"], default_ruleset_key=default_ruleset_key)
    gate_rule = {
        "rule_key": rule["rule_key"],
        "title": rule["title"],
        "citation_display": citation_display,
        "standard_letter": rule["standard_letter"],
        "applicability": rule["applicability"],
    }
    gate = applicability.gate_one(gate_rule, facts)

    if gate.verdict.value == "false":
        finding = review.evaluate_not_applicable(
            rule_category=rule["standard_letter"], subject=rule["title"], citation_display=citation_display,
        )
        # gate.finding_text is the applicability gate's own (differently
        # worded, equally legitimate -- see engine/applicability.py's
        # module docstring) phrasing; prefer it here since it names the
        # specific gating fact, not just the generic template.
        finding = review.Finding(
            rule_category=finding.rule_category, disposition=finding.disposition,
            unresolved=finding.unresolved, body=gate.finding_text or finding.body,
            board_question=None,
        )
        return finding, "false"

    if gate.verdict.value == "unknown":
        return (
            review.Finding(
                rule_category=rule["standard_letter"],
                disposition=review.Disposition.APPLICABILITY_UNKNOWN,
                unresolved=True,
                body=None,
                board_question=gate.board_question,
            ),
            "unknown",
        )

    return _dispatch_true(rule, facts, citation_display), "true"


def run_walk(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    criteria_set_id: str,
    rules: list[dict[str, Any]],
    facts: dict[str, Any],
    default_ruleset_key: str,
    actor_user_id: str,
    parent_heading: str = "Subdivision Standards (Article 7, Section 12.f.1)",
    parent_citation: dict[str, Any] | None = None,
    sort_start: int = 0,
) -> dict[str, Any]:
    """Walks every rule in `rules` (already sorted) and writes one 'finding'
    findings_nodes row per rule under a new 'section' parent, plus (for the
    one rule carrying mandates_condition) one `conditions` row. Returns a
    summary dict: {section_node_id, node_ids: [...], unresolved_count,
    total_count, condition_ids: [...]}.

    Never partial in spirit -- if any single create_node() call fails, it
    raises (each is its own transaction, per engine/findings.py's own
    design; a caller re-running this after fixing the cause simply creates
    the missing nodes, since findings_nodes are pure appends).
    """
    section = create_node(
        conn,
        case_id=case_id,
        node_type="section",
        sort_order=sort_start,
        heading=parent_heading,
        citation=_citation_struct(parent_citation or {}, default_ruleset_key=default_ruleset_key),
        finding_source=None,
        unresolved=False,
        actor_user_id=actor_user_id,
    )

    node_ids: list[str] = []
    unresolved_count = 0
    condition_ids: list[str] = []

    for i, rule in enumerate(rules):
        finding, verdict = _finding_for_rule(rule, facts, default_ruleset_key=default_ruleset_key)
        citation_struct = _citation_struct(rule["citation"], default_ruleset_key=default_ruleset_key)

        node = create_node(
            conn,
            case_id=case_id,
            node_type="finding",
            parent_id=section["id"],
            sort_order=sort_start + 1 + i,
            number_label=f"{rule['standard_letter']}.",
            heading=f"{rule['standard_letter']}. {rule['title']}",
            quoted_standard_text=rule["code_text"],
            body=finding.body,
            # finding_source claims authorship of `body` specifically
            # (engine/findings.py: "finding_source is not None and body is
            # None" is a validation error) -- a pure board_question node
            # (judgement criteria, an honest numeric/boolean blank, or
            # applicability-unknown) has no body to claim authorship of, so
            # finding_source stays None even though quoted_standard_text
            # (always present, verbatim) still carries the engine's own
            # rule_id/citation provenance below.
            finding_source="engine" if finding.body else None,
            rule_id=rule["id"],
            criteria_set_id=criteria_set_id,
            citation=citation_struct,
            applicability_verdict=verdict,
            # findings_nodes' own CHECK constraint (0001_init.sql, carried
            # forward by 0013_findings_tree.sql) enforces this structurally:
            # a 'finding' node must have unresolved=1 unless a HUMAN has set
            # `conclusion` -- which this module, per the framing rule, never
            # does. `finding.unresolved` (engine.review.Finding) encodes a
            # narrower idea ("does the substance still need the Board's
            # judgement") that does not control here; even a
            # NOT_APPLICABLE/PROCEDURAL_REFERENCE finding remains a
            # Board-adoptable item until a vote closes it, so it stays
            # unresolved=1 too -- exactly the schema's own comment: "A
            # resolved node has either a conclusion or an explicit reason to
            # be blank."
            unresolved=True,
            board_question=finding.board_question,
            provenance={
                "rule_id": rule["id"],
                "citation": rule["citation"],
                "engine": {"disposition": finding.disposition.value},
            },
            actor_user_id=actor_user_id,
        )
        node_ids.append(node["id"])
        if node["unresolved"]:
            unresolved_count += 1

        if rule.get("mandates_condition"):
            cond = review.fire_flood_condition(rule_id=rule["id"])
            condition_ids.append(
                _write_condition(
                    conn, case_id=case_id, findings_node_id=node["id"], rule_id=rule["id"],
                    text=cond.text, citation=rule["citation"], actor_user_id=actor_user_id,
                )
            )

    return {
        "section_node_id": section["id"],
        "node_ids": node_ids,
        "total_count": len(node_ids),
        "unresolved_count": unresolved_count,
        "condition_ids": condition_ids,
    }


def _write_condition(
    conn: sqlite3.Connection,
    *,
    case_id: str,
    findings_node_id: str,
    rule_id: str,
    text: str,
    citation: dict[str, Any],
    actor_user_id: str,
) -> str:
    """Writes one `conditions` row (source='draft' -- an engine-drafted
    condition the Board adopts/amends/strikes at the meeting, never
    self-adopting). No dedicated conditions.py module exists yet (W7
    territory); this is the minimal, audited insert this walk needs."""
    cond_id = _new_id()
    now = _utc_now_iso()
    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO conditions
                (id, case_id, findings_node_id, number_label, text, source, status,
                 rule_id, citation_json, revision, superseded_by, created_at, actor_user_id)
            VALUES (?, ?, ?, NULL, ?, 'draft', 'proposed', ?, ?, 1, NULL, ?, ?);
            """,
            (cond_id, case_id, findings_node_id, text, rule_id, json.dumps(citation, sort_keys=True), now, actor_user_id),
        )
        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="condition.drafted",
            payload={"condition_id": cond_id, "case_id": case_id, "rule_id": rule_id, "source": "engine"},
            case_id=case_id,
            entity_table="conditions",
            entity_id=cond_id,
        )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise
    return cond_id


__all__ = ["load_rules_for_criteria_set", "run_walk"]
