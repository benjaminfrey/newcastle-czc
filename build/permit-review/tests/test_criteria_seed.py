"""Tests engine/criteria_seed.py -- loading the built subdivision criteria
artifact into `criteria_sets` / `rules` / `criteria_set_rules` DB rows.
Offline, throwaway temp-dir SQLite file per test, same `conn` fixture shape
tests/test_cases.py already established (migrated DB, synthetic actor,
one binding 'adopted' ruleset row).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit, db, security  # noqa: E402
from engine import criteria_seed  # noqa: E402
from ruleset_build import build_subdivision_criteria as bsc  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"
ADOPTED_ID = "r_adopted"


def _seed_ruleset(conn: sqlite3.Connection) -> None:
    now = "2026-08-21T00:00:00.000Z"
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
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def artifact_path(tmp_path):
    out = tmp_path / "criteria-subdivision.json"
    import unittest.mock as mock

    with mock.patch.object(bsc, "OUT_PATH", out):
        bsc.build(write=True)
    return out


ACTOR = security.SYNTHETIC_USER_ID


def test_sync_inserts_one_criteria_set_and_21_rules(conn, artifact_path):
    result = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=artifact_path
    )
    assert result["created"] is True
    assert len(result["rule_ids"]) == 21

    cs_row = conn.execute("SELECT * FROM criteria_sets WHERE id = ?;", (result["criteria_set_id"],)).fetchone()
    assert cs_row["set_key"] == "subdivision"
    assert cs_row["authority"] == "planning_board"
    assert cs_row["ruleset_id"] == ADOPTED_ID

    rule_count = conn.execute("SELECT COUNT(*) AS n FROM rules WHERE ruleset_id = ?;", (ADOPTED_ID,)).fetchone()["n"]
    assert rule_count == 21

    csr_count = conn.execute(
        "SELECT COUNT(*) AS n FROM criteria_set_rules WHERE criteria_set_id = ?;",
        (result["criteria_set_id"],),
    ).fetchone()["n"]
    assert csr_count == 21


def test_sync_is_idempotent(conn, artifact_path):
    first = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=artifact_path
    )
    second = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=artifact_path
    )
    assert second["created"] is False
    assert second["criteria_set_id"] == first["criteria_set_id"]
    assert second["rule_ids"] == first["rule_ids"]

    rule_count = conn.execute("SELECT COUNT(*) AS n FROM rules WHERE ruleset_id = ?;", (ADOPTED_ID,)).fetchone()["n"]
    assert rule_count == 21  # not 42 -- the second call wrote nothing


def test_rows_round_trip_kind_and_judgement_tells(conn, artifact_path):
    result = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=artifact_path
    )
    j_id = result["rule_ids"]["j"]  # Aesthetic, cultural, and Natural Values -- undue + adverse effect
    row = conn.execute("SELECT * FROM rules WHERE id = ?;", (j_id,)).fetchone()
    assert row["kind"] == "judgement"
    tells = json.loads(row["judgement_tells_json"])
    assert set(tells) == {"undue", "adverse effect"}

    o_id = result["rule_ids"]["o"]  # Freshwater Wetlands -- boolean, no tells
    row_o = conn.execute("SELECT * FROM rules WHERE id = ?;", (o_id,)).fetchone()
    assert row_o["kind"] == "boolean"
    assert json.loads(row_o["judgement_tells_json"]) == []


def test_row_n_carries_the_mandated_condition_verbatim(conn, artifact_path):
    result = criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=artifact_path
    )
    n_id = result["rule_ids"]["n"]
    row = conn.execute("SELECT * FROM rules WHERE id = ?;", (n_id,)).fetchone()
    mandate = json.loads(row["mandates_condition_json"])
    assert mandate["fires"] == "always"
    assert "three feet above the 100-year flood elevation" in mandate["text"]

    other_id = result["rule_ids"]["c"]
    row_other = conn.execute("SELECT * FROM rules WHERE id = ?;", (other_id,)).fetchone()
    assert row_other["mandates_condition_json"] is None


def test_sync_writes_exactly_one_audit_event_and_verifies(conn, artifact_path):
    before = conn.execute("SELECT COUNT(*) AS n FROM events;").fetchone()["n"]
    criteria_seed.sync_subdivision_criteria(
        conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=artifact_path
    )
    after = conn.execute("SELECT COUNT(*) AS n FROM events;").fetchone()["n"]
    assert after == before + 1

    ev = conn.execute("SELECT * FROM events ORDER BY seq DESC LIMIT 1;").fetchone()
    assert ev["kind"] == "criteria.subdivision.synced"
    payload = json.loads(ev["payload_json"])
    assert payload["rule_count"] == 21
    assert payload["by_kind"]["judgement"] == 14

    ok, _ = audit.verify_chain(conn)
    assert ok


def test_a_bad_artifact_writes_nothing(conn, tmp_path):
    bad = tmp_path / "bad-criteria-subdivision.json"
    bad.write_text(json.dumps({"schema": "wrong", "rules": [], "criteria_set": {}}), encoding="utf-8")

    with pytest.raises(criteria_seed.CriteriaSeedError):
        criteria_seed.sync_subdivision_criteria(
            conn, ruleset_id=ADOPTED_ID, actor_user_id=ACTOR, artifact_path=bad
        )

    assert conn.execute("SELECT COUNT(*) AS n FROM rules;").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM criteria_sets;").fetchone()["n"] == 0
