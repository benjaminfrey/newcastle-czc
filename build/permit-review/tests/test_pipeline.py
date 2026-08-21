"""Tests for ingest/pipeline.py -- the W4 formgen-detect + Tier A/B
extract + persist glue (CONTRACT.md §3.6).

Offline, no network, no LLM, no vision. A throwaway temp-dir SQLite file
per test (matching tests/test_worklist.py / tests/test_extraction.py's own
convention). The real-fixture tests are read-only against docs/Findings of
Fact and Conclusions of Law/ (never modified) and skip cleanly when that
folder isn't present.
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

import fitz  # noqa: E402

from app import db, security  # noqa: E402
from ingest import pipeline, worklist  # noqa: E402
from ingest.fields import FieldCandidate  # noqa: E402
from ingest import triage  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"
REPO_ROOT = APP_ROOT.parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"
STANTEC = FIXTURES_DIR / "M004, L087 (NT Land III, 684 US Route 1) (Stantec) application 2024.05.08.pdf"
PROFENNO = FIXTURES_DIR / "M003, L065-B (Profenno, Perkins Point Rd) Planning Board Application 2024.06.05.pdf"
requires_fixtures = pytest.mark.skipif(
    not (STANTEC.exists() and PROFENNO.exists()),
    reason="real Findings of Fact fixture PDFs not present under docs/",
)


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _cand(field_key: str, value_raw: str, *, page_no: int = 1, bbox=(0.0, 0.0, 10.0, 10.0),
          confidence: float = 0.9, method: str = "regex", document_id: str | None = None) -> FieldCandidate:
    return FieldCandidate(
        field_key=field_key, value_raw=value_raw, value_norm=value_raw, unit=None,
        document_id=document_id, page_no=page_no, bbox=bbox, method=method,
        confidence=confidence, rationale="test", source_priority=40,
    )


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    yield c
    c.close()


def _seed_ruleset_and_case(conn: sqlite3.Connection) -> tuple[str, str]:
    now = _utc_now_iso()
    ruleset_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, built_at,
             builder_version, manifest_path, source_sha_json, created_at)
        VALUES (?, ?, ?, 0, 'adopted', ?, 'test', 'rulesets/test/manifest.json', '{}', ?);
        """,
        (ruleset_id, f"test-{ruleset_id[:8]}", "Test Ruleset", now, now),
    )
    case_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO cases (id, label, application_type, ruleset_id, is_scratch, created_at, updated_at)
        VALUES (?, 'Test Case', 'use', ?, 1, ?, ?);
        """,
        (case_id, ruleset_id, now, now),
    )
    worklist.seed_field_defs(conn, ruleset_id)
    return ruleset_id, case_id


# --------------------------------------------------------------------------- #
# The crosswalk.
# --------------------------------------------------------------------------- #


def test_crosswalk_renames_direct_fields():
    result = pipeline.apply_crosswalk([_cand("applicant.name", "Jane Doe")])
    assert len(result.persistable) == 1
    assert result.persistable[0].field_key == "project_information.applicant"
    assert not result.unattached


def test_crosswalk_combines_tax_map_and_lot():
    result = pipeline.apply_crosswalk([
        _cand("parcel.tax_map", "4", bbox=(0, 0, 10, 10)),
        _cand("parcel.lot", "87", bbox=(20, 0, 30, 10)),
    ])
    combined = [c for c in result.persistable if c.field_key == "site_information.tax_lot"]
    assert len(combined) == 1
    assert combined[0].value_raw == "Map 4 / Lot 87"
    # bbox union
    assert combined[0].bbox == (0.0, 0.0, 30.0, 10.0)
    assert not result.unattached


def test_crosswalk_combine_handles_partial_evidence():
    """Only ONE half of a combine pair present -- still produces a single
    combined candidate (never left dangling as a phantom unattached field
    for the half that IS mapped by a combine rule)."""
    result = pipeline.apply_crosswalk([_cand("parcel.deed_book", "5637")])
    combined = [c for c in result.persistable if c.field_key == "project_information.owner_deed_reference"]
    assert len(combined) == 1
    assert combined[0].value_raw == "5637"


def test_crosswalk_reports_unattached_dimensional_fields():
    result = pipeline.apply_crosswalk([
        _cand("setback.front_ft", "25"),
        _cand("building.width_ft", "40"),
    ])
    assert not result.persistable
    assert {c.field_key for c in result.unattached} == {"setback.front_ft", "building.width_ft"}


def test_crosswalk_never_produces_a_false_disagreement_from_a_combine_pair():
    """A tax_map/lot pair must never independently reach ingest.fields'
    merge machinery as two competing values for one field_key -- that would
    read as a false 'contested' (see ingest/pipeline.py's own module
    docstring)."""
    from ingest.fields import merge_all
    result = pipeline.apply_crosswalk([
        _cand("parcel.tax_map", "4"),
        _cand("parcel.lot", "87"),
    ])
    merged = merge_all(result.persistable)
    assert all(m.state != "contested" for m in merged.values())


# --------------------------------------------------------------------------- #
# Persistence.
# --------------------------------------------------------------------------- #


def test_persist_candidates_writes_rows_and_resolves_field_def(conn):
    ruleset_id, case_id = _seed_ruleset_and_case(conn)
    candidates = [_cand("project_information.applicant", "Jane Doe")]
    report = pipeline.persist_candidates(conn, case_id=case_id, ruleset_id=ruleset_id, candidates=candidates)
    assert report["inserted"] == 1
    assert report["no_field_def"] == []

    row = conn.execute("SELECT * FROM field_candidates WHERE case_id = ?;", (case_id,)).fetchone()
    assert row["raw_text"] == "Jane Doe"
    assert row["case_id"] == case_id
    assert row["extractor"] == "regex"

    # Never writes field_values -- only a human confirm/override/not-applicable does.
    fv_count = conn.execute("SELECT COUNT(*) AS n FROM field_values WHERE case_id = ?;", (case_id,)).fetchone()["n"]
    assert fv_count == 0


def test_persist_candidates_skips_field_key_with_no_seeded_field_def(conn):
    ruleset_id, case_id = _seed_ruleset_and_case(conn)
    candidates = [_cand("not_a_real_field_key", "whatever")]
    report = pipeline.persist_candidates(conn, case_id=case_id, ruleset_id=ruleset_id, candidates=candidates)
    assert report["inserted"] == 0
    assert report["no_field_def"] == ["not_a_real_field_key"]
    n = conn.execute("SELECT COUNT(*) AS n FROM field_candidates WHERE case_id = ?;", (case_id,)).fetchone()["n"]
    assert n == 0


def test_persist_then_worklist_never_auto_confirms(conn):
    """End-to-end within one case: persisted evidence for SOME fields still
    leaves every OTHER seeded field_def on the worklist as
    'not_in_application' -- and nothing, anywhere, becomes 'confirmed'
    without an explicit human action (which this test never calls)."""
    ruleset_id, case_id = _seed_ruleset_and_case(conn)
    candidates = [_cand("project_information.applicant", "Jane Doe")]
    pipeline.persist_candidates(conn, case_id=case_id, ruleset_id=ruleset_id, candidates=candidates)

    result = worklist.worklist(conn, case_id, form_generation="gen1")
    # Applicant has evidence now -- must NOT appear on the worklist.
    assert "project_information.applicant" not in {i["field_key"] for i in result["items"]}
    assert result["summary"]["needed"] == 22  # 23 seeded - 1 with evidence

    states = {r["state"] for r in conn.execute(
        "SELECT DISTINCT state FROM field_values WHERE case_id = ?;", (case_id,)
    ).fetchall()}
    assert states == {"not_in_application"}


# --------------------------------------------------------------------------- #
# extract_document -- the rotation-gated positional pass (real fixtures).
# --------------------------------------------------------------------------- #


@requires_fixtures
def test_stantec_positional_pass_only_attempts_rotated_pages():
    pages = triage.triage_pdf(str(STANTEC))
    candidate_pages = [p.page_number for p in pages if p.tier in ("B", "D")]
    run = pipeline.extract_document(
        STANTEC, document_id="doc-1", source_priority=40,
        positional_candidate_pages=candidate_pages,
    )
    assert run.generation == "gen1"
    # Every attempted page must be rotated -- pp.29-42 (unrotated DEP
    # boilerplate) must never be attempted at all (the FIFTH drift fix).
    doc = fitz.open(str(STANTEC))
    try:
        for page_no in run.tier_b_pages_attempted:
            assert doc[page_no - 1].rotation != 0, f"page {page_no} was attempted but is not rotated"
    finally:
        doc.close()
    assert 9 in run.tier_b_pages_attempted
    assert 9 in run.tier_b_pages_parseable
    # None of the known false-positive prose pages contributed a candidate.
    assert all(c.page_no not in range(29, 43) for c in run.candidates)


@requires_fixtures
def test_stantec_page9_candidates_are_all_labeled_no_bare_numbers():
    pages = triage.triage_pdf(str(STANTEC))
    candidate_pages = [p.page_number for p in pages if p.tier in ("B", "D")]
    run = pipeline.extract_document(
        STANTEC, document_id="doc-1", source_priority=40,
        positional_candidate_pages=candidate_pages,
    )
    page9 = [c for c in run.candidates if c.page_no == 9]
    assert len(page9) == 17
    for c in page9:
        assert c.field_key and "." in c.field_key
        assert c.needs_confirmation is True
        assert c.rationale  # every candidate names WHY/WHERE it matched


@requires_fixtures
def test_profenno_native_form_page_suppresses_positional_pass():
    """Profenno's Tier A finds the real native form page (page 5) -- the
    positional pass must not also run over the packet's other Tier B/D
    pages (the false-positive source verified during this workflow's own
    integration run: unrelated prose pages coincidentally matching
    'applicant.name', etc.)."""
    pages = triage.triage_pdf(str(PROFENNO))
    candidate_pages = [p.page_number for p in pages if p.tier in ("B", "D")]
    run = pipeline.extract_document(
        PROFENNO, document_id="doc-1", source_priority=40,
        positional_candidate_pages=candidate_pages,
    )
    assert run.tier_a_page == 5
    assert run.tier_b_pages_attempted == []
    assert all(c.page_no == 5 for c in run.candidates)


@requires_fixtures
def test_every_extracted_candidate_across_real_fixtures_needs_confirmation():
    for path in (STANTEC, PROFENNO):
        pages = triage.triage_pdf(str(path))
        candidate_pages = [p.page_number for p in pages if p.tier in ("B", "D")]
        run = pipeline.extract_document(
            path, document_id="doc-1", source_priority=40,
            positional_candidate_pages=candidate_pages,
        )
        assert run.candidates, f"expected at least one candidate for {path.name}"
        for c in run.candidates:
            assert c.needs_confirmation is True
            assert c.field_key.strip() != ""
