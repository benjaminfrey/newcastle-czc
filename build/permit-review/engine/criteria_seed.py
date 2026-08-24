"""Implements CONTRACT.md §3.6 (`rules`, `criteria_sets`, `criteria_set_rules`)
for the W6 task: "the criteria set + the applicability gate".

Loads the build artifact ruleset_build/build_subdivision_criteria.py writes
(rulesets/adopted/criteria-subdivision.json) into DB rows for one ruleset:
one `criteria_sets` row (Subdivision, Article 7 §12.f.1, Planning Board),
21 `rules` rows (one per standard a-u, kind/applicability/exceptions/
mandates_condition/judgement_tells all carried straight through, verbatim,
from the artifact -- this module classifies NOTHING itself; classification
already happened at ruleset-build time, per the task brief), and 21
`criteria_set_rules` membership rows in Code order.

CONTRACT.md §1.1 S1 (validate-all-then-write): every row is built and
validated in Python BEFORE any INSERT runs; a single BEGIN/COMMIT wraps the
whole sync, so a bad artifact writes nothing, not a partial criteria set.
S9 (append-only audit): one `events` row records the whole sync (counts,
ruleset_id, artifact source hash), inside the same transaction as the
INSERTs.

Idempotent by design, NOT by an upsert: if `criteria_sets` already has a
(ruleset_id, 'subdivision') row, sync_subdivision_criteria() is a no-op and
returns the existing ids -- this table is build output, not something a
later operator hand-edits and expects preserved across a re-sync in some
other shape. Call again after re-running the builder only once you have
confirmed nothing already depends on the prior rows (out of scope here;
no code depends on any of this yet).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.audit import append_event
from app.config import RULESETS_DIR

from engine import predicates

CRITERIA_SUBDIVISION_PATH = RULESETS_DIR / "adopted" / "criteria-subdivision.json"


class CriteriaSeedError(RuntimeError):
    """The artifact is missing, malformed, or fails validation. Nothing is
    written when this is raised -- S1, validate-all-then-write."""


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def load_artifact(path: Path = CRITERIA_SUBDIVISION_PATH) -> dict:
    if not path.exists():
        raise CriteriaSeedError(
            f"{path} does not exist -- build it first with "
            f"'python -m ruleset_build.build_subdivision_criteria'"
        )
    with path.open("r", encoding="utf-8") as f:
        artifact = json.load(f)
    _validate_artifact(artifact)
    return artifact


_ALLOWED_KINDS = {"numeric", "boolean", "narrative", "judgement", "procedural"}


def _validate_artifact(artifact: dict) -> None:
    """S1: validate the WHOLE artifact before any row is built, let alone
    written. Every failure is collected, not just the first."""
    errors: list[str] = []
    if artifact.get("schema") != "newcastle.criteria-subdivision/1.0.0":
        errors.append(f"unexpected schema {artifact.get('schema')!r}")

    rules = artifact.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("'rules' must be a non-empty list")
        rules = []

    seen_letters: set[str] = set()
    for r in rules:
        letter = r.get("standard_letter")
        if not letter:
            errors.append(f"rule missing standard_letter: {r.get('rule_key')!r}")
        elif letter in seen_letters:
            errors.append(f"duplicate standard_letter {letter!r}")
        else:
            seen_letters.add(letter)

        if r.get("kind") not in _ALLOWED_KINDS:
            errors.append(f"rule {r.get('rule_key')!r} has invalid kind {r.get('kind')!r}")
        if not r.get("source_text"):
            errors.append(f"rule {r.get('rule_key')!r} has empty source_text")
        if not isinstance(r.get("exceptions"), list):
            errors.append(f"rule {r.get('rule_key')!r} exceptions must be a list")
        if not isinstance(r.get("judgement_tells"), list):
            errors.append(f"rule {r.get('rule_key')!r} judgement_tells must be a list")
        if r.get("kind") == "judgement" and not r.get("judgement_tells"):
            errors.append(f"rule {r.get('rule_key')!r} is kind=judgement but judgement_tells is empty")
        if r.get("kind") != "judgement" and r.get("judgement_tells"):
            errors.append(
                f"rule {r.get('rule_key')!r} is kind={r.get('kind')!r} but carries judgement_tells "
                f"{r.get('judgement_tells')!r}"
            )

        # The applicability predicate must be well-formed against
        # engine/predicates.py's own grammar -- evaluate it against an empty
        # facts dict now so a malformed predicate fails at build/load time,
        # not silently the first time a real case hits it.
        try:
            predicates.evaluate(r.get("applicability"), {})
        except predicates.PredicateError as exc:
            errors.append(f"rule {r.get('rule_key')!r} has an invalid applicability predicate: {exc}")

    if len(seen_letters) != 21 or seen_letters != set("abcdefghijklmnopqrstu"):
        errors.append(f"expected exactly the 21 letters a-u, got {sorted(seen_letters)!r}")

    if not artifact.get("criteria_set", {}).get("set_key"):
        errors.append("criteria_set.set_key is required")

    if errors:
        raise CriteriaSeedError("criteria-subdivision.json failed validation:\n  - " + "\n  - ".join(errors))


def _existing_criteria_set(conn: sqlite3.Connection, ruleset_id: str, set_key: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM criteria_sets WHERE ruleset_id = ? AND set_key = ?;",
        (ruleset_id, set_key),
    ).fetchone()


def sync_subdivision_criteria(
    conn: sqlite3.Connection,
    *,
    ruleset_id: str,
    actor_user_id: str | None = None,
    artifact_path: Path = CRITERIA_SUBDIVISION_PATH,
) -> dict[str, Any]:
    """Load criteria-subdivision.json and, if `ruleset_id` does not already
    have a 'subdivision' criteria_sets row, insert the criteria_set + 21
    rules + 21 criteria_set_rules rows for it, all in one transaction.

    Returns {"created": bool, "criteria_set_id": str, "rule_ids": {letter: id}}.
    created=False means a prior sync already populated this ruleset_id; the
    existing ids are returned unchanged and nothing is written.
    """
    artifact = load_artifact(artifact_path)
    set_key = artifact["criteria_set"]["set_key"]

    existing = _existing_criteria_set(conn, ruleset_id, set_key)
    if existing is not None:
        rule_rows = conn.execute(
            """
            SELECT r.rule_key, r.id
            FROM rules r
            JOIN criteria_set_rules csr ON csr.rule_id = r.id
            WHERE csr.criteria_set_id = ?;
            """,
            (existing["id"],),
        ).fetchall()
        rule_ids = {row["rule_key"].rsplit(".", 1)[-1]: row["id"] for row in rule_rows}
        return {"created": False, "criteria_set_id": existing["id"], "rule_ids": rule_ids}

    cs = artifact["criteria_set"]
    criteria_set_id = _new_id()
    now = _utc_now_iso()
    rule_ids: dict[str, str] = {}

    conn.execute("BEGIN;")
    try:
        conn.execute(
            """
            INSERT INTO criteria_sets
                (id, ruleset_id, set_key, label, application_type, authority,
                 citation_json, sort_order, created_at, actor_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
            """,
            (
                criteria_set_id, ruleset_id, cs["set_key"], cs["label"], cs["application_type"],
                cs["authority"], _dumps(cs["citation"]), now, actor_user_id,
            ),
        )

        for r in artifact["rules"]:
            rule_id = _new_id()
            rule_ids[r["standard_letter"]] = rule_id
            conn.execute(
                """
                INSERT INTO rules
                    (id, ruleset_id, rule_key, district_key, field_def_id, kind, title,
                     code_text, test_json, citation_json, prompt_hint,
                     applicability_json, exceptions_json, mandates_condition_json,
                     judgement_tells_json, unresolved, sort_order, created_at, actor_user_id)
                VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, 0, ?, ?, ?);
                """,
                (
                    rule_id, ruleset_id, r["rule_key"], r["kind"], r["title"], r["source_text"],
                    _dumps(r["test_json"]) if r.get("test_json") is not None else None,
                    _dumps(r["citation"]),
                    _dumps(r["applicability"]),
                    _dumps(r["exceptions"]),
                    _dumps(r["mandates_condition"]) if r.get("mandates_condition") is not None else None,
                    _dumps(r["judgement_tells"]),
                    r["sort_order"], now, actor_user_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO criteria_set_rules
                    (id, criteria_set_id, rule_id, sort_order, heading, created_at, actor_user_id)
                VALUES (?, ?, ?, ?, NULL, ?, ?);
                """,
                (_new_id(), criteria_set_id, rule_id, r["sort_order"], now, actor_user_id),
            )

        append_event(
            conn,
            actor_user_id=actor_user_id,
            kind="criteria.subdivision.synced",
            payload={
                "ruleset_id": ruleset_id,
                "criteria_set_id": criteria_set_id,
                "set_key": set_key,
                "rule_count": len(artifact["rules"]),
                "by_kind": artifact["counts"]["by_kind"],
                "judgement_letters": artifact["counts"]["judgement_letters"],
                "source_sha256": artifact["source"]["sha256"],
            },
            entity_table="criteria_sets",
            entity_id=criteria_set_id,
        )
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise

    return {"created": True, "criteria_set_id": criteria_set_id, "rule_ids": rule_ids}


# rules.unresolved is written 0 for every seeded row here, matching how
# field_defs.unresolved is used elsewhere in this schema: it flags a rule
# DEFINITION that is itself ambiguous (an unqualified dimensional value, a
# missing footnote -- CONTRACT.md §4.2.3/§4.2.5's sense of the word). None
# of the 21 subdivision standards are ambiguous at that level -- every one
# has a definite kind, a definite (possibly {"op":"always"}) applicability
# predicate, and verbatim source_text. Whether a given CASE's finding under
# a rule is still a blank awaiting the Board is a property of that case's
# findings_nodes row (unresolved defaults to 1 there -- 0001_init.sql), not
# of this rule-definition row, and is out of scope for this task.
