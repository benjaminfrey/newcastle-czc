"""Tests engine/subdivision_review.py -- the W6 RECONCILIATION orchestrator
that wires the four independently-built W6 pieces (criteria set + gate,
review engine core, findings tree, draft renderer) into one real walk.

Offline, throwaway temp-dir SQLite, same `conn` fixture shape
tests/test_criteria_seed.py and tests/test_case_findings.py already
established.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import cases, db, security  # noqa: E402
from engine import criteria_seed, subdivision_review  # noqa: E402
from engine.review import FLOOD_CONDITION_TEXT  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
ACTOR = security.SYNTHETIC_USER_ID
ADOPTED_ID = "r_adopted"


def _seed_ruleset(conn: sqlite3.Connection) -> None:
    now = "2026-08-22T00:00:00.000Z"
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, adopted_on, built_at,
             builder_version, manifest_path, source_sha_json, is_current, superseded_by,
             created_at, actor_user_id)
        VALUES (?, 'adopted', 'Newcastle Core Zoning Code (adopted)', 1, 'adopted', NULL,
                ?, 'ruleset_build/1.0.0', 'rulesets/adopted/manifest.json', '{}', 1, NULL, ?, NULL);
        """,
        (ADOPTED_ID, now, now),
    )


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    _seed_ruleset(c)
    yield c
    c.close()


@pytest.fixture()
def seeded(conn):
    return criteria_seed.sync_subdivision_criteria(conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR)


@pytest.fixture()
def case(conn):
    return cases.create_case(
        conn, application_type="subdivision", map_lot="M-TEST", situs_address="Test Rd",
        applicant_name="Test Applicant", actor_user_id=ACTOR,
    )


def _walk(conn, seeded, case, facts):
    rules = subdivision_review.load_rules_for_criteria_set(conn, seeded["criteria_set_id"])
    return rules, subdivision_review.run_walk(
        conn, case_id=case["id"], criteria_set_id=seeded["criteria_set_id"], rules=rules,
        facts=facts, default_ruleset_key="adopted", actor_user_id=ACTOR,
        parent_citation={"article": 7, "section": "12", "subsection": "f.1"},
    )


# --------------------------------------------------------------------------- #
# THE DECISIVE INVARIANT: no facts -> 21 nodes, every one unresolved.
# --------------------------------------------------------------------------- #


def test_empty_facts_walks_all_21_and_every_node_is_unresolved(conn, seeded, case):
    rules, result = _walk(conn, seeded, case, {})
    assert len(rules) == 21
    assert result["total_count"] == 21
    assert result["unresolved_count"] == 21

    nodes = conn.execute(
        "SELECT node_type, applicability_verdict, unresolved, quoted_standard_text, conclusion "
        "FROM findings_nodes WHERE case_id = ? AND node_type = 'finding';",
        (case["id"],),
    ).fetchall()
    assert len(nodes) == 21
    for row in nodes:
        # Every standard is quoted verbatim -- never an empty quote.
        assert row["quoted_standard_text"]
        # unresolved=1 always: findings_nodes' own CHECK constraint forces
        # this for any 'finding' node the app writes (conclusion stays NULL
        # -- the framing rule, enforced structurally, not just in code).
        assert row["unresolved"] == 1
        assert row["conclusion"] is None
        # applicability_verdict is always one of the three values -- never
        # NULL, never silently dropped.
        assert row["applicability_verdict"] in ("true", "false", "unknown")


def test_empty_facts_gates_the_four_conditional_rules_unknown_not_dropped(conn, seeded, case):
    rules, result = _walk(conn, seeded, case, {})
    rows = conn.execute(
        "SELECT number_label, applicability_verdict, board_question FROM findings_nodes "
        "WHERE case_id = ? AND node_type = 'finding' ORDER BY sort_order;",
        (case["id"],),
    ).fetchall()
    by_letter = {r["number_label"].rstrip("."): r for r in rows}
    for letter in ("l", "n", "r", "t"):
        assert by_letter[letter]["applicability_verdict"] == "unknown"
        assert by_letter[letter]["board_question"]  # never silently dropped


def test_judgement_letters_render_as_board_questions_never_a_body(conn, seeded, case):
    rules, result = _walk(conn, seeded, case, {})
    rows = conn.execute(
        "SELECT number_label, body, board_question, finding_source FROM findings_nodes "
        "WHERE case_id = ? AND node_type = 'finding';",
        (case["id"],),
    ).fetchall()
    by_letter = {r["number_label"].rstrip("."): r for r in rows}
    judgement_letters = {"c", "d", "e", "f", "g", "h", "i", "j", "k", "m", "q", "s"}  # l, t are gated
    for letter in judgement_letters:
        row = by_letter[letter]
        assert row["body"] is None
        assert row["board_question"]
        assert row["finding_source"] is None  # nothing to claim authorship of


# --------------------------------------------------------------------------- #
# THE FLOOD CONDITION: fires unconditionally, verbatim, regardless of the
# gate's own (unknown, with no facts) verdict on standard n.
# --------------------------------------------------------------------------- #


def test_flood_condition_fires_unconditionally_and_verbatim(conn, seeded, case):
    rules, result = _walk(conn, seeded, case, {})
    assert len(result["condition_ids"]) == 1
    row = conn.execute(
        "SELECT text, source, rule_id, findings_node_id FROM conditions WHERE id = ?;",
        (result["condition_ids"][0],),
    ).fetchone()
    assert row["text"] == FLOOD_CONDITION_TEXT
    assert row["source"] == "draft"
    n_node = next(
        r for r in conn.execute(
            "SELECT id, number_label FROM findings_nodes WHERE case_id = ? AND node_type='finding';",
            (case["id"],),
        ).fetchall() if r["number_label"] == "n."
    )
    assert row["rule_id"] is not None
    assert row["findings_node_id"] == n_node["id"]


def test_flood_condition_still_fires_when_gate_says_true(conn, seeded, case):
    # site.in_fema_flood_zone = True -> n's own applicability gate reads
    # TRUE, not unknown -- the condition still fires (it is unconditional,
    # per ruleset_build/build_subdivision_criteria.py's own "SEPARATE,
    # unconditional instruction" comment), and it fires exactly once.
    rules, result = _walk(conn, seeded, case, {"site.in_fema_flood_zone": True})
    assert len(result["condition_ids"]) == 1
    n_row = next(
        r for r in conn.execute(
            "SELECT number_label, applicability_verdict FROM findings_nodes "
            "WHERE case_id = ? AND node_type='finding';", (case["id"],),
        ).fetchall() if r["number_label"] == "n."
    )
    assert n_row["applicability_verdict"] == "true"


def test_flood_condition_does_not_fire_for_any_other_rule(conn, seeded, case):
    rules, result = _walk(conn, seeded, case, {})
    assert len(result["condition_ids"]) == 1  # not 21, not 0


# --------------------------------------------------------------------------- #
# Citation form -- the reconciliation fix: a lettered Article 7 standard
# must render with its letter, not just "Article 7, Section 12".
# --------------------------------------------------------------------------- #


def test_citation_display_carries_the_standard_letter(conn, seeded, case):
    rules, result = _walk(conn, seeded, case, {})
    from render.case_findings import _citation_display

    row = next(
        r for r in conn.execute(
            "SELECT citation_json FROM findings_nodes WHERE case_id = ? AND node_type='finding';",
            (case["id"],),
        ).fetchall()
    )
    # Spot check via the actual render path used by the PDF: pick node n.
    n_row = conn.execute(
        "SELECT citation_json FROM findings_nodes WHERE case_id = ? AND number_label = 'n.';",
        (case["id"],),
    ).fetchone()
    displayed = _citation_display(n_row["citation_json"], default_ruleset_key="adopted")
    # render_citation()'s "short" style only abbreviates the section word
    # ("Section" -> "Sec."); "Article" is unabbreviated either way -- see
    # app/citation.py:render_citation()'s own docstring.
    assert displayed == "Article 7, Sec. 12, Standard n. (Flood Areas)"


# --------------------------------------------------------------------------- #
# Not-applicable stays a stated fact, never silently dropped either.
# --------------------------------------------------------------------------- #


def test_gated_rule_false_verdict_states_a_fact_never_drops_the_node(conn, seeded, case):
    rules, result = _walk(
        conn, seeded, case,
        {
            "subdivision.has_shore_frontage_lots": False,
            "subdivision.crosses_municipal_boundary": False,
            "site.within_watershed_of_pond_or_lake": False,
            "site.distance_to_protected_water_ft": 5000,
        },
    )
    rows = conn.execute(
        "SELECT number_label, applicability_verdict, body FROM findings_nodes "
        "WHERE case_id = ? AND node_type='finding';", (case["id"],),
    ).fetchall()
    by_letter = {r["number_label"].rstrip("."): r for r in rows}
    for letter in ("r", "t", "l"):
        assert by_letter[letter]["applicability_verdict"] == "false"
        assert by_letter[letter]["body"]  # a stated fact, not a blank
    assert len(rows) == 21  # still all 21 -- FALSE never drops a node
