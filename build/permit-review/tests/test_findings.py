"""Tests engine/findings.py (the W6 "findings tree" model) against
CONTRACT.md §3.6 and 0013_findings_tree.sql.

Offline, no network, no LLM, no PII -- a throwaway temp-dir SQLite file per
test via the `conn` fixture (migrated, synthetic actor row, one binding
'adopted' ruleset, one seeded `rules` row, and one `cases` row via
app.cases.create_case -- the same fixture shape tests/test_cases.py already
established).
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit, cases, db, security  # noqa: E402
from app.citation import Citation  # noqa: E402
from engine import findings  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"

ADOPTED_ID = "r_adopted"
RULE_ID = "rule_flood_areas"


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


def _seed_rule(conn: sqlite3.Connection) -> None:
    now = "2026-08-22T00:00:00.000Z"
    citation_json = (
        '{"ruleset_key":"adopted","scheme":"adopted","article":7,"section":"12","subsection":"n"}'
    )
    code_text = (
        "All subdivision proposals shall be reasonably safe from flooding, and any "
        "proposal for a subdivision including the placement of manufactured homes "
        "greater than 5 lots or 5 acres, whichever is less, shall include base flood "
        "elevation data. All new or replacement water supply systems and/or sanitary "
        "sewage systems shall be designed to minimize or eliminate infiltration of "
        "flood waters into the systems and discharge from the systems into flood "
        "waters, and on-site waste disposal systems shall be located and constructed "
        "so as to avoid impairment to them or contamination from them during flooding."
    )
    conn.execute(
        """
        INSERT INTO rules
            (id, ruleset_id, rule_key, district_key, field_def_id, kind, title, code_text,
             test_json, citation_json, prompt_hint, unresolved, sort_order, created_at, actor_user_id)
        VALUES (?, ?, 'art7.12.f.1.n', NULL, NULL, 'procedural', 'Flood Areas', ?,
                NULL, ?, NULL, 0, 14, ?, NULL);
        """,
        (RULE_ID, ADOPTED_ID, code_text, citation_json, now),
    )


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    _seed_ruleset(c)
    _seed_rule(c)
    try:
        yield c
    finally:
        c.close()


ACTOR = security.SYNTHETIC_USER_ID


@pytest.fixture()
def case_id(conn: sqlite3.Connection) -> str:
    case = cases.create_case(
        conn,
        application_type="subdivision",
        map_lot="M003, L059",
        situs_address="White Rd",
        applicant_name="Shattuck",
        actor_user_id=ACTOR,
    )
    return case["id"]


CITATION = Citation(
    ruleset_key="adopted", scheme="adopted", article=7, section="12", subsection="n",
)

FLOOD_TEXT = (
    "All subdivision proposals shall be reasonably safe from flooding, and any proposal for "
    "a subdivision including the placement of manufactured homes greater than 5 lots or "
    "5 acres, whichever is less, shall include base flood elevation data."
)


def _engine_provenance(**extra):
    prov = {"rule_id": RULE_ID, "citation": {"article": 7, "section": "12", "subsection": "n"}}
    prov.update(extra)
    return prov


# --------------------------------------------------------------------------- #
# Schema -- the columns 0013_findings_tree.sql adds actually exist and are
# wired the way engine/findings.py assumes.
# --------------------------------------------------------------------------- #


def test_new_columns_exist(conn: sqlite3.Connection):
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(findings_nodes);").fetchall()}
    for expected in ("quoted_standard_text", "finding_source", "applicability_verdict", "citation_display"):
        assert expected in cols


def test_enum_columns_are_db_level_checked_independent_of_this_module(conn, case_id):
    """finding_source and applicability_verdict's enum CHECKs are real DDL
    (unlike the dropped provenance CHECK -- see 0013's header comment), so a
    raw SQL bypass of engine/findings.py entirely still can't write a bad
    value into either column."""
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("BEGIN;")
        conn.execute(
            """
            INSERT INTO findings_nodes
                (id, case_id, revision, sort_order, node_type, applicability_verdict,
                 unresolved, provenance_json, created_at)
            VALUES ('raw_bad_verdict', ?, 1, 0, 'finding', 'maybe', 1, '{}', '2026-01-01T00:00:00.000Z');
            """,
            (case_id,),
        )
        conn.execute("COMMIT;")
    conn.execute("ROLLBACK;")

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("BEGIN;")
        conn.execute(
            """
            INSERT INTO findings_nodes
                (id, case_id, revision, sort_order, node_type, finding_source,
                 unresolved, provenance_json, created_at)
            VALUES ('raw_bad_source', ?, 1, 0, 'finding', 'ai', 1, '{}', '2026-01-01T00:00:00.000Z');
            """,
            (case_id,),
        )
        conn.execute("COMMIT;")
    conn.execute("ROLLBACK;")


def test_conclusion_column_still_untouched(conn: sqlite3.Connection):
    """0013 must not have widened or renamed the banned met/not_met column."""
    cols = {row["name"]: row for row in conn.execute("PRAGMA table_info(findings_nodes);").fetchall()}
    assert "conclusion" in cols
    assert "not null" not in str(cols["conclusion"]).lower() or cols["conclusion"]["notnull"] == 0


# --------------------------------------------------------------------------- #
# create_node -- the framing rule, honest blanks, provenance shape
# --------------------------------------------------------------------------- #


def test_create_node_never_writes_a_conclusion(conn, case_id):
    node = findings.create_node(
        conn, case_id=case_id, node_type="finding",
        quoted_standard_text=FLOOD_TEXT,
        body=None, unresolved=True,
        board_question="Does the application include the required base flood elevation data?",
        rule_id=RULE_ID, citation=CITATION,
        provenance={"rule_id": RULE_ID},
        actor_user_id=ACTOR,
    )
    assert node["conclusion"] is None
    assert node["conclusion_by"] is None
    assert node["conclusion_at"] is None
    assert node["unresolved"] is True


def test_create_node_sets_root_id_to_own_id(conn, case_id):
    node = findings.create_node(
        conn, case_id=case_id, node_type="section", heading="II. Findings of Fact",
        actor_user_id=ACTOR,
    )
    assert node["root_id"] == node["id"]
    assert node["revision"] == 1
    assert node["superseded_by"] is None


def test_create_node_computes_citation_display_from_struct(conn, case_id):
    node = findings.create_node(
        conn, case_id=case_id, node_type="finding",
        quoted_standard_text=FLOOD_TEXT, citation=CITATION,
        provenance=_engine_provenance(), finding_source="engine", body="",
        actor_user_id=ACTOR,
    )
    # citation_display is a CACHE of app.citation.render() -- assert it is
    # exactly what render() produces for the same struct, not hand-typed.
    from app.citation import render as citation_render
    assert node["citation_display"] == citation_render(CITATION)
    assert node["citation_json"] == {
        "ruleset_key": "adopted", "scheme": "adopted", "article": 7,
        "section": "12", "subsection": "n", "district_key": None, "district_code": None,
        "district_name": None, "panel_title": None, "label": None, "use_label": None,
        "exhibit": None, "table": None, "section_title": None, "standard_letter": None,
        "standard_title": None, "table_title": None,
    }


def test_create_node_rejects_bad_node_type(conn, case_id):
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(conn, case_id=case_id, node_type="verdict", actor_user_id=ACTOR)
    assert any(d["field"] == "node_type" for d in exc.value.details)
    # writes nothing on failure
    assert conn.execute("SELECT COUNT(*) c FROM findings_nodes;").fetchone()["c"] == 0


def test_create_node_rejects_bad_applicability_verdict(conn, case_id):
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", applicability_verdict="maybe",
            actor_user_id=ACTOR,
        )
    assert any(d["field"] == "applicability_verdict" for d in exc.value.details)


def test_create_node_rejects_prose_with_empty_provenance(conn, case_id):
    """Python-level enforcement only (validate_provenance()) -- deliberately
    NOT a DB CHECK; see 0013_findings_tree.sql's header comment for why a
    cross-column CHECK to this effect was drafted and then dropped (it
    collided with a concurrently-built W6 workflow's own test fixtures,
    which default provenance_json to '{}'). A raw SQL insert bypassing this
    module entirely -- as that other workflow's fixtures do -- is
    deliberately still possible; only calls through engine.findings are
    guaranteed to carry this rule."""
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", body="Some drafted sentence.",
            finding_source="engine", provenance=None, actor_user_id=ACTOR,
        )
    assert any(d["field"] == "provenance_json" for d in exc.value.details)
    # writes nothing on failure
    assert conn.execute("SELECT COUNT(*) c FROM findings_nodes;").fetchone()["c"] == 0


def test_create_node_engine_source_requires_traceable_provenance(conn, case_id):
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", body="The proposed setback is 180 ft.",
            finding_source="engine", provenance={"note": "no trace at all"}, actor_user_id=ACTOR,
        )
    assert any(d["field"] == "provenance_json" for d in exc.value.details)


def test_create_node_model_source_requires_model_object_never_prompt_text(conn, case_id):
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", body="Drafted prose.",
            finding_source="model", provenance={"model": {"provider": "anthropic"}},
            actor_user_id=ACTOR,
        )
    fields = {d["field"] for d in exc.value.details}
    assert "provenance_json.model.model" in fields
    assert "provenance_json.model.prompt_sha256" in fields

    with pytest.raises(findings.ValidationError) as exc2:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", body="Drafted prose.",
            finding_source="model",
            provenance={"model": {
                "provider": "anthropic", "model": "claude-opus-5", "prompt_sha256": "ab" * 32,
                "prompt": "the actual prompt text, which must never be stored",
            }},
            actor_user_id=ACTOR,
        )
    assert any("raw prompt text" in d["message"] for d in exc2.value.details)


def test_create_node_model_source_accepts_well_formed_provenance(conn, case_id):
    node = findings.create_node(
        conn, case_id=case_id, node_type="finding", body="Drafted prose from the model.",
        finding_source="model",
        provenance={"model": {
            "provider": "anthropic", "model": "claude-opus-5",
            "prompt_sha256": "ab" * 32, "generation_id": "gen_1",
        }},
        actor_user_id=ACTOR,
    )
    assert node["finding_source"] == "model"
    assert node["provenance_json"]["model"]["prompt_sha256"] == "ab" * 32


def test_create_node_operator_source_requires_operator_object(conn, case_id):
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", body="A Board member's own note.",
            finding_source="operator", provenance={"note": "typed at the meeting"},
            actor_user_id=ACTOR,
        )
    assert any(d["field"] == "provenance_json.operator" for d in exc.value.details)

    node = findings.create_node(
        conn, case_id=case_id, node_type="finding", body="A Board member's own note.",
        finding_source="operator", provenance={"operator": {"user_id": ACTOR}},
        actor_user_id=ACTOR,
    )
    assert node["finding_source"] == "operator"


def test_create_node_finding_source_without_body_is_rejected(conn, case_id):
    with pytest.raises(findings.ValidationError) as exc:
        findings.create_node(
            conn, case_id=case_id, node_type="finding", finding_source="engine",
            provenance=_engine_provenance(), actor_user_id=ACTOR,
        )
    assert any(d["field"] == "finding_source" for d in exc.value.details)


def test_create_node_writes_exactly_one_events_row(conn, case_id):
    before = conn.execute("SELECT COUNT(*) c FROM events;").fetchone()["c"]
    node = findings.create_node(
        conn, case_id=case_id, node_type="section", heading="II. Findings of Fact",
        actor_user_id=ACTOR,
    )
    after = conn.execute("SELECT COUNT(*) c FROM events;").fetchone()["c"]
    assert after == before + 1
    row = conn.execute("SELECT * FROM events ORDER BY seq DESC LIMIT 1;").fetchone()
    assert row["kind"] == "findings_node.created"
    assert row["entity_table"] == "findings_nodes"
    assert row["entity_id"] == node["id"]
    ok, bad_seq = audit.verify_chain(conn)
    assert ok, f"chain broken at seq {bad_seq}"


# --------------------------------------------------------------------------- #
# amend_node -- THE core ask: three revisions survive, chain is walkable,
# one events row per amendment, current tree reflects only the latest.
# --------------------------------------------------------------------------- #


def test_amend_twice_all_three_revisions_survive_and_chain_walks(conn, case_id):
    rev1 = findings.create_node(
        conn, case_id=case_id, node_type="finding",
        quoted_standard_text=FLOOD_TEXT,
        applicability_verdict="unknown",
        unresolved=True,
        board_question="Does the application include the required base flood elevation data?",
        rule_id=RULE_ID, citation=CITATION,
        provenance=_engine_provenance(),
        finding_source=None, body=None,
        actor_user_id=ACTOR,
    )
    root_id = rev1["root_id"]
    assert rev1["revision"] == 1
    assert rev1["superseded_by"] is None

    rev2 = findings.amend_node(
        conn, node_id=rev1["id"], actor_user_id=ACTOR,
        reason="engine ran the check against the extracted application facts",
        applicability_verdict="true",
        body="The application's Sheet C-2 states finished floor elevation 3.2 ft above the "
             "base flood elevation shown on FIRM panel 23015C0210E.",
        finding_source="engine",
        provenance=_engine_provenance(document_id="doc_c2", page=2),
        unresolved=True,  # still a Board flag -- a numeric record is never a verdict
    )
    assert rev2["revision"] == 2
    assert rev2["root_id"] == root_id
    assert rev2["superseded_by"] is None
    # quoted_standard_text carried forward unchanged (not passed to amend_node)
    assert rev2["quoted_standard_text"] == FLOOD_TEXT
    # board_question carried forward unchanged too
    assert rev2["board_question"] == rev1["board_question"]

    rev1_reloaded = findings.get_node(conn, rev1["id"])
    assert rev1_reloaded["superseded_by"] == rev2["id"]
    assert rev1_reloaded["revision"] == 1  # the old row itself is untouched otherwise
    assert rev1_reloaded["quoted_standard_text"] == FLOOD_TEXT  # not overwritten in place

    rev3 = findings.amend_node(
        conn, node_id=rev2["id"], actor_user_id=ACTOR,
        reason="Board member corrected the FIRM panel citation at the meeting",
        provenance={"rule_id": RULE_ID, "citation": {"article": 7, "section": "12", "subsection": "n"},
                    "document_id": "doc_c2", "page": 2, "operator": {"user_id": ACTOR}},
        body="The application's Sheet C-2 states finished floor elevation 3.2 ft above the "
             "base flood elevation shown on FIRM panel 23015C0211E (corrected panel suffix).",
        finding_source="operator",
    )
    assert rev3["revision"] == 3
    assert rev3["root_id"] == root_id
    assert rev3["superseded_by"] is None

    rev2_reloaded = findings.get_node(conn, rev2["id"])
    assert rev2_reloaded["superseded_by"] == rev3["id"]
    assert rev2_reloaded["body"].endswith("FIRM panel 23015C0210E.")  # rev2's own text, unmutated

    # All three revisions survive under the stable root_id -- nothing deleted.
    chain = findings.get_revision_chain(conn, root_id)
    assert [n["revision"] for n in chain] == [1, 2, 3]
    assert [n["id"] for n in chain] == [rev1["id"], rev2["id"], rev3["id"]]

    # The chain is WALKABLE: follow superseded_by pointers from the first
    # revision forward and land on exactly the same sequence, ending at the
    # one row whose superseded_by is NULL.
    walked = [rev1["id"]]
    cursor = rev1_reloaded
    while cursor["superseded_by"] is not None:
        cursor = findings.get_node(conn, cursor["superseded_by"])
        walked.append(cursor["id"])
    assert walked == [rev1["id"], rev2["id"], rev3["id"]]
    assert cursor["superseded_by"] is None
    assert cursor["id"] == rev3["id"]

    # The "current tree" view surfaces ONLY the live revision.
    current = findings.get_current_node_for_root(conn, root_id)
    assert current["id"] == rev3["id"]
    live_nodes = findings.get_current_nodes_for_case(conn, case_id)
    live_ids = {n["id"] for n in live_nodes}
    assert rev3["id"] in live_ids
    assert rev1["id"] not in live_ids
    assert rev2["id"] not in live_ids

    # Exactly one events row per amendment (plus the one from creation).
    kinds = [r["kind"] for r in conn.execute(
        "SELECT kind FROM events WHERE entity_table = 'findings_nodes' ORDER BY seq;"
    ).fetchall()]
    assert kinds == ["findings_node.created", "findings_node.amended", "findings_node.amended"]

    ok, bad_seq = audit.verify_chain(conn)
    assert ok, f"chain broken at seq {bad_seq}"


def test_amend_node_on_a_superseded_revision_raises(conn, case_id):
    rev1 = findings.create_node(
        conn, case_id=case_id, node_type="section", heading="II. Findings of Fact",
        actor_user_id=ACTOR,
    )
    rev2 = findings.amend_node(conn, node_id=rev1["id"], actor_user_id=ACTOR, heading="II. Findings of Fact (Amended)")
    with pytest.raises(findings.NotCurrentRevision) as exc:
        findings.amend_node(conn, node_id=rev1["id"], actor_user_id=ACTOR, heading="stale amendment attempt")
    assert exc.value.current_id == rev2["id"]


def test_amend_node_unknown_id_raises_node_not_found(conn, case_id):
    with pytest.raises(findings.NodeNotFound):
        findings.amend_node(conn, node_id="does-not-exist", actor_user_id=ACTOR, heading="x")


def test_amend_node_failed_validation_writes_nothing_and_does_not_supersede(conn, case_id):
    rev1 = findings.create_node(
        conn, case_id=case_id, node_type="finding", body="Original text.",
        finding_source="operator", provenance={"operator": {"user_id": ACTOR}},
        actor_user_id=ACTOR,
    )
    before_count = conn.execute("SELECT COUNT(*) c FROM findings_nodes;").fetchone()["c"]
    before_events = conn.execute("SELECT COUNT(*) c FROM events;").fetchone()["c"]

    with pytest.raises(findings.ValidationError):
        findings.amend_node(
            conn, node_id=rev1["id"], actor_user_id=ACTOR,
            applicability_verdict="not-a-real-value",
        )

    after_count = conn.execute("SELECT COUNT(*) c FROM findings_nodes;").fetchone()["c"]
    after_events = conn.execute("SELECT COUNT(*) c FROM events;").fetchone()["c"]
    assert after_count == before_count
    assert after_events == before_events
    still_current = findings.get_node(conn, rev1["id"])
    assert still_current["superseded_by"] is None  # the failed amend must not have superseded it


# --------------------------------------------------------------------------- #
# The trg_findings_supersede_once trigger -- carried forward by 0013,
# proven still live (a direct-SQL attempt to re-point an already-superseded
# row must still raise, independent of engine/findings.py entirely).
# --------------------------------------------------------------------------- #


def test_supersede_once_trigger_survives_the_0013_rebuild(conn, case_id):
    rev1 = findings.create_node(conn, case_id=case_id, node_type="note", body=None, actor_user_id=ACTOR)
    rev2 = findings.amend_node(conn, node_id=rev1["id"], actor_user_id=ACTOR, heading="renamed")
    rev3 = findings.create_node(conn, case_id=case_id, node_type="note", body=None, actor_user_id=ACTOR)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("BEGIN;")
        conn.execute(
            "UPDATE findings_nodes SET superseded_by = ? WHERE id = ?;", (rev3["id"], rev1["id"])
        )
        conn.execute("COMMIT;")
    conn.execute("ROLLBACK;")
    # rev1 still points at its real successor, unchanged by the failed attempt.
    assert findings.get_node(conn, rev1["id"])["superseded_by"] == rev2["id"]
