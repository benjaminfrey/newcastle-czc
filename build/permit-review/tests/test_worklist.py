"""Tests for ingest/worklist.py — the W4 "absence worklist" task brief and
CONTRACT.md §3.6 (field_defs / field_candidates / field_values).

Offline, no network, no LLM, no PII — a throwaway temp-dir SQLite file per
test via the `conn` fixture (migrated, given the synthetic actor row, and
seeded with one binding ('adopted') ruleset row, matching the shape
tests/test_cases.py already established).
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import cases, db, security  # noqa: E402
from ingest import worklist  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
ADOPTED_ID = "r_adopted"


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _seed_adopted_ruleset(conn: sqlite3.Connection) -> None:
    now = _utc_now_iso()
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
    _seed_adopted_ruleset(c)
    try:
        yield c
    finally:
        c.close()


ACTOR = security.SYNTHETIC_USER_ID


def _make_case(conn: sqlite3.Connection, label: str, **overrides) -> dict:
    kwargs = dict(application_type="use", label=label, actor_user_id=ACTOR)
    kwargs.update(overrides)
    return cases.create_case(conn, **kwargs)


def _field_def_id(conn: sqlite3.Connection, ruleset_id: str, label: str) -> str:
    row = conn.execute(
        "SELECT id FROM field_defs WHERE ruleset_id = ? AND district_key IS NULL AND label = ?;",
        (ruleset_id, label),
    ).fetchone()
    assert row is not None, f"field_def {label!r} was not seeded"
    return row["id"]


def _insert_candidate(conn: sqlite3.Connection, case_id: str, field_def_id: str, *, value_text: str) -> None:
    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO field_candidates (
            id, case_id, field_def_id, document_id, page_id, subject_key, source_priority,
            raw_text, value_num, value_text, unit, bbox_json, extractor, confidence,
            provenance_json, created_at, actor_user_id
        ) VALUES (?, ?, ?, NULL, NULL, NULL, 40, ?, NULL, ?, NULL, NULL, 'manual', NULL, '{}', ?, ?);
        """,
        (uuid.uuid4().hex, case_id, field_def_id, value_text, value_text, now, ACTOR),
    )


# --------------------------------------------------------------------------- #
# seed_field_defs
# --------------------------------------------------------------------------- #


def test_seed_field_defs_inserts_the_full_canonical_set(conn):
    inserted = worklist.seed_field_defs(conn, ADOPTED_ID, actor_user_id=ACTOR)
    assert len(inserted) == len(worklist.FIELD_DEF_SEED)

    rows = conn.execute(
        "SELECT label, panel_title, source_category, typically_absent_gen1, typically_absent_gen2 "
        "FROM field_defs WHERE ruleset_id = ? AND district_key IS NULL;",
        (ADOPTED_ID,),
    ).fetchall()
    assert len(rows) == len(worklist.FIELD_DEF_SEED)

    by_label = {r["label"]: r for r in rows}
    assert "Owner Deed Reference" in by_label
    deed = by_label["Owner Deed Reference"]
    assert deed["panel_title"] == "Project Information"
    assert deed["source_category"] == "registry"
    assert deed["typically_absent_gen1"] == 1
    assert deed["typically_absent_gen2"] == 0

    every_source_category = {r["source_category"] for r in rows}
    assert every_source_category <= worklist.SOURCE_CATEGORIES
    assert "applicant" in every_source_category  # the majority of fields


def test_seed_field_defs_is_idempotent(conn):
    first = worklist.seed_field_defs(conn, ADOPTED_ID, actor_user_id=ACTOR)
    second = worklist.seed_field_defs(conn, ADOPTED_ID, actor_user_id=ACTOR)
    assert len(first) == len(worklist.FIELD_DEF_SEED)
    assert second == []

    count = conn.execute(
        "SELECT COUNT(*) AS n FROM field_defs WHERE ruleset_id = ? AND district_key IS NULL;",
        (ADOPTED_ID,),
    ).fetchone()["n"]
    assert count == len(worklist.FIELD_DEF_SEED)


def test_seed_field_defs_unknown_ruleset_raises(conn):
    with pytest.raises(worklist.WorklistError):
        worklist.seed_field_defs(conn, "no-such-ruleset", actor_user_id=ACTOR)


# --------------------------------------------------------------------------- #
# detect_form_generation — pure function
# --------------------------------------------------------------------------- #


def test_detect_form_generation_gen1_fingerprint():
    text = "PLANNING APPLICATION\nSECTION 2\nOFFICE ADMINSTRATION USE ONLY\nDate Received:"
    assert worklist.detect_form_generation(text) == "gen1"


def test_detect_form_generation_gen1_is_whitespace_and_case_tolerant():
    text = "office   adminstration\nuse   only"
    assert worklist.detect_form_generation(text) == "gen1"


def test_detect_form_generation_gen2_needs_both_title_and_version_stamp():
    text = "PLANNING APPLICATION\nCover Sheet\n(required with all applications)\n\nv.2024.09.26"
    assert worklist.detect_form_generation(text) == "gen2"


def test_detect_form_generation_gen2_title_alone_is_not_enough():
    # "PLANNING APPLICATION" with no version stamp must not resolve to gen2 --
    # it is also just this app's generic English description of what a
    # permit application is.
    text = "This is a planning application for a new driveway."
    assert worklist.detect_form_generation(text) == "unknown"


def test_detect_form_generation_empty_text_is_unknown():
    assert worklist.detect_form_generation("") == "unknown"
    assert worklist.detect_form_generation("   \n  ") == "unknown"


def test_detect_form_generation_unrelated_text_is_unknown():
    assert worklist.detect_form_generation("Dear Newcastle Town Board, we are writing to state...") == "unknown"


def test_detect_form_generation_contradictory_signals_is_unknown():
    text = "OFFICE ADMINSTRATION USE ONLY ... PLANNING APPLICATION ... v.2024.09.26"
    assert worklist.detect_form_generation(text) == "unknown"


# --------------------------------------------------------------------------- #
# worklist() — the central behavior CONTRACT.md's design principle #1/#2 names
# --------------------------------------------------------------------------- #


def test_worklist_raises_on_unknown_case(conn):
    with pytest.raises(worklist.CaseNotFound):
        worklist.worklist(conn, "no-such-case")


def test_worklist_gen1_flags_deed_reference_as_structurally_absent(conn):
    case = _make_case(conn, "M012, L004 (15 Hall St, Blood and Sons)")
    result = worklist.worklist(conn, case["id"], form_generation="gen1")

    assert result["form_generation"] == "gen1"
    deed_items = [i for i in result["items"] if i["label"] == "Owner Deed Reference"]
    assert len(deed_items) == 1
    deed = deed_items[0]
    assert deed["structurally_absent"] is True
    assert deed["source_category"] == "registry"
    assert "Gen-1" in deed["reason"]

    # materialized as an honest blank, not silently resolved
    fv = conn.execute(
        "SELECT state FROM field_values WHERE case_id = ? AND field_def_id = ?;",
        (case["id"], deed["field_def_id"]),
    ).fetchone()
    assert fv["state"] == "not_in_application"


def test_worklist_gen2_does_not_flag_deed_reference_as_structurally_absent(conn):
    case = _make_case(conn, "M003, L059 (White Rd, Shattuck)")
    result = worklist.worklist(conn, case["id"], form_generation="gen2")

    assert result["form_generation"] == "gen2"
    deed_items = [i for i in result["items"] if i["label"] == "Owner Deed Reference"]
    # still needed (no candidate exists), but NOT reported as a structural gap
    assert len(deed_items) == 1
    assert deed_items[0]["structurally_absent"] is False
    assert "Gen-2" in deed_items[0]["reason"]


def test_worklist_unknown_generation_scores_nothing_as_structural(conn):
    case = _make_case(conn, "Unknown-generation case")
    result = worklist.worklist(conn, case["id"], form_generation="unknown")
    assert result["form_generation"] == "unknown"
    assert len(result["items"]) == len(worklist.FIELD_DEF_SEED)
    assert all(i["structurally_absent"] is None for i in result["items"])


def test_worklist_summary_headline(conn):
    case = _make_case(conn, "Headline test case")
    result = worklist.worklist(conn, case["id"], form_generation="gen1")
    total = len(worklist.FIELD_DEF_SEED)
    assert result["summary"]["total"] == total
    assert result["summary"]["needed"] == total  # nothing extracted yet
    assert result["summary"]["headline"] == f"{total} of {total} fields still needed"


def test_worklist_excludes_fields_with_a_candidate(conn):
    case = _make_case(conn, "Has a candidate")
    ruleset_id = case["ruleset_id"]
    worklist.seed_field_defs(conn, ruleset_id, actor_user_id=ACTOR)
    applicant_fd = _field_def_id(conn, ruleset_id, "Applicant")
    _insert_candidate(conn, case["id"], applicant_fd, value_text="Jane Doe")

    result = worklist.worklist(conn, case["id"], form_generation="gen1")
    labels = {i["label"] for i in result["items"]}
    assert "Applicant" not in labels
    assert result["summary"]["needed"] == len(worklist.FIELD_DEF_SEED) - 1

    # worklist() must not have materialized a not_in_application row for a
    # field that has a real candidate sitting behind it.
    fv = conn.execute(
        "SELECT state FROM field_values WHERE case_id = ? AND field_def_id = ?;",
        (case["id"], applicant_fd),
    ).fetchone()
    assert fv is None


def test_worklist_respects_a_prior_human_resolution(conn):
    case = _make_case(conn, "Shoreland not applicable")
    ruleset_id = case["ruleset_id"]
    worklist.seed_field_defs(conn, ruleset_id, actor_user_id=ACTOR)
    shoreland_fd = _field_def_id(conn, ruleset_id, "Shoreland Zoning")

    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO field_values (
            id, case_id, field_def_id, subject_key, chosen_candidate_id, value_num, value_text,
            unit, state, override_reason, contested_with_json, confirmed_by, confirmed_at,
            created_at, updated_at, actor_user_id
        ) VALUES (?, ?, ?, NULL, NULL, NULL, NULL, NULL, 'not_applicable', NULL, NULL, ?, ?,
                  ?, ?, ?);
        """,
        (uuid.uuid4().hex, case["id"], shoreland_fd, ACTOR, now, now, now, ACTOR),
    )

    result = worklist.worklist(conn, case["id"], form_generation="gen1")
    labels = {i["label"] for i in result["items"]}
    assert "Shoreland Zoning" not in labels

    # the human's row is untouched
    fv = conn.execute(
        "SELECT state FROM field_values WHERE case_id = ? AND field_def_id = ?;",
        (case["id"], shoreland_fd),
    ).fetchone()
    assert fv["state"] == "not_applicable"


def test_worklist_is_idempotent_across_repeated_calls(conn):
    case = _make_case(conn, "Idempotency check")
    first = worklist.worklist(conn, case["id"], form_generation="gen1")
    second = worklist.worklist(conn, case["id"], form_generation="gen1")
    assert first["summary"] == second["summary"]

    count = conn.execute(
        "SELECT COUNT(*) AS n FROM field_values WHERE case_id = ?;", (case["id"],)
    ).fetchone()["n"]
    assert count == len(worklist.FIELD_DEF_SEED)


def test_worklist_grouping_covers_every_populated_category(conn):
    case = _make_case(conn, "Grouping check")
    result = worklist.worklist(conn, case["id"], form_generation="gen1")
    grouped = result["grouped"]
    assert set(grouped.keys()) == worklist.SOURCE_CATEGORIES
    assert len(grouped["registry"]) == 1  # Owner Deed Reference
    assert any(i["label"] == "Proposed Use" for i in grouped["staff"])
    total_grouped = sum(len(v) for v in grouped.values())
    assert total_grouped == result["summary"]["needed"]


# --------------------------------------------------------------------------- #
# The 8 real applications named in this workflow's task brief — the worklist
# must never come back vacuously empty for any of them.
# --------------------------------------------------------------------------- #

REAL_CASES = [
    ("M011, L046-A (Morrissey, 53 Pleasant Street)", "gen2"),
    ("M003, L065-B (Profenno, Perkins Point Rd)", "gen1"),
    ("M004, L087 (NT Land III, 684 US Route 1) (Stantec)", "gen1"),
    ("M012, L004 (15 Hall St, Blood and Sons)", "gen1"),
    ("M012, L011 (Z38, 38 Academy Hill Rd)", "gen1"),
    ("M003, L059 (White Rd, Shattuck)", "gen2"),
    ("M004, L036 (461 Sheepscot Rd, Verney)", "gen2"),
    ("M002, L053 (976 US Rt 1, Dalton)", "gen2"),
]


@pytest.mark.parametrize("label,generation", REAL_CASES, ids=[c[0] for c in REAL_CASES])
def test_worklist_nonempty_for_every_real_application(conn, label, generation):
    case = _make_case(conn, label)
    result = worklist.worklist(conn, case["id"], form_generation=generation)
    assert len(result["items"]) > 0, f"worklist came back empty for {label!r} -- that would be a bug"
    assert result["summary"]["needed"] > 0
    assert result["summary"]["needed"] <= result["summary"]["total"]
