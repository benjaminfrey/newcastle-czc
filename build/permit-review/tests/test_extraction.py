"""Tests the W4 "operator confirm UI":

    app/extraction.py            — pure business logic
    app/routes/extraction.py     — the HTTP/HTML layer over it

against CONTRACT.md §3.3 (the audit chain), §3.6 (field_candidates /
field_values), and the task brief's CENTRAL DESIGN PRINCIPLE: a candidate is
evidence, a field_values row is a human decision, and every decision writes
exactly one events row.

Offline, no network, no LLM, no PII — a throwaway temp-dir SQLite file per
test, seeded directly with SQL (field_defs/field_candidates are populated by
a separate, not-yet-built extraction pass; this module only ever READS
whatever landed there, so tests seed synthetic rows exactly the way
tests/test_documents.py seeds a synthetic case).
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit as audit_mod  # noqa: E402
from app import config, db, extraction as extraction_mod, security  # noqa: E402
from app.routes import extraction as extraction_routes  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


# --------------------------------------------------------------------------- #
# Seeding helpers
# --------------------------------------------------------------------------- #


def _seed_ruleset(conn, *, binding: int = 0) -> str:
    ruleset_id = uuid.uuid4().hex
    now = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, built_at,
             builder_version, manifest_path, source_sha_json, created_at)
        VALUES (?, ?, ?, ?, 'adopted', ?, 'test', 'rulesets/test/manifest.json', '{}', ?);
        """,
        (ruleset_id, f"test-{ruleset_id[:8]}", "Test Ruleset", binding, now, now),
    )
    return ruleset_id


def _seed_case(conn, ruleset_id: str, *, district_key: str = "d1") -> str:
    now = _utc_now_iso()
    case_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO cases
            (id, label, application_type, district_key, ruleset_id, is_scratch, created_at, updated_at)
        VALUES (?, ?, 'use', ?, ?, 1, ?, ?);
        """,
        (case_id, "M003, L059 (White Rd, Test Case)", district_key, ruleset_id, now, now),
    )
    return case_id


def _seed_document(conn, case_id: str, *, kind: str, priority: int, title: str) -> str:
    now = _utc_now_iso()
    doc_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO documents (id, case_id, kind, source_priority, title, created_at)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (doc_id, case_id, kind, priority, title, now),
    )
    return doc_id


def _seed_page(conn, document_id: str, *, page_number: int = 1) -> str:
    now = _utc_now_iso()
    page_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO pages (id, document_id, page_number, created_at) VALUES (?, ?, ?, ?);",
        (page_id, document_id, page_number, now),
    )
    return page_id


def _seed_field_def(
    conn, ruleset_id: str, *, district_key: str | None, field_key: str, label: str,
    panel_title: str = "PRIMARY BUILDING PLACEMENT",
) -> str:
    now = _utc_now_iso()
    field_def_id = uuid.uuid4().hex
    citation = {
        "ruleset_key": "adopted", "scheme": "adopted", "article": 2,
        "district_code": "D1", "district_name": "Rural",
        "panel_title": panel_title, "label": label,
    }
    conn.execute(
        """
        INSERT INTO field_defs
            (id, ruleset_id, district_key, field_key, panel_key, panel_title, label,
             value_kind, unit, applicability, unresolved, citation_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'dimension', 'ft', 'established', 0, ?, ?);
        """,
        (field_def_id, ruleset_id, district_key, field_key, "primary_building_placement",
         panel_title, label, json.dumps(citation), now),
    )
    return field_def_id


def _seed_candidate(
    conn, case_id: str, field_def_id: str, *, document_id: str | None, page_id: str | None,
    source_priority: int, value_num: float | None = None, value_text: str | None = None,
    raw_text: str = "", extractor: str = "regex", confidence: float | None = 0.9,
    subject_key: str | None = None,
) -> str:
    now = _utc_now_iso()
    cand_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO field_candidates
            (id, case_id, field_def_id, document_id, page_id, subject_key, source_priority,
             raw_text, value_num, value_text, unit, bbox_json, extractor, confidence,
             provenance_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ft', ?, ?, ?, '{}', ?);
        """,
        (cand_id, case_id, field_def_id, document_id, page_id, subject_key, source_priority,
         raw_text, value_num, value_text, json.dumps([10, 20, 100, 40]), extractor, confidence, now),
    )
    return cand_id


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    try:
        yield c
    finally:
        c.close()


@pytest.fixture()
def seeded(conn):
    """One case with:
    - a plain field (one candidate, no disagreement)
    - a CONTESTED field: a plan (priority 100) and a form (priority 40)
      disagree on the same field_def
    """
    ruleset_id = _seed_ruleset(conn)
    case_id = _seed_case(conn, ruleset_id)

    plan_doc = _seed_document(conn, case_id, kind="plan", priority=100, title="Site Plan, Sheet C-2")
    form_doc = _seed_document(conn, case_id, kind="form", priority=40, title="Zoning Permit Application")
    plan_page = _seed_page(conn, plan_doc, page_number=2)
    form_page = _seed_page(conn, form_doc, page_number=1)

    setback_field = _seed_field_def(
        conn, ruleset_id, district_key="d1", field_key="primary_building_placement.side_setback",
        label="Side Setback",
    )
    frontage_field = _seed_field_def(
        conn, ruleset_id, district_key="d1", field_key="lot_dimensions.frontage",
        label="Lot Frontage", panel_title="LOT DIMENSIONS",
    )

    # Contested: plan says 12 ft, form says 10 ft.
    plan_candidate = _seed_candidate(
        conn, case_id, setback_field, document_id=plan_doc, page_id=plan_page,
        source_priority=100, value_num=12.0, raw_text="12'", extractor="table", confidence=0.95,
    )
    form_candidate = _seed_candidate(
        conn, case_id, setback_field, document_id=form_doc, page_id=form_page,
        source_priority=40, value_num=10.0, raw_text="Side Setback: 10", extractor="regex", confidence=0.6,
    )

    # Agreeing: only one candidate.
    frontage_candidate = _seed_candidate(
        conn, case_id, frontage_field, document_id=form_doc, page_id=form_page,
        source_priority=40, value_num=87.0, raw_text="Lot Frontage 87 ft", extractor="regex", confidence=0.8,
    )

    return {
        "case_id": case_id, "ruleset_id": ruleset_id,
        "setback_field": setback_field, "frontage_field": frontage_field,
        "plan_doc": plan_doc, "form_doc": form_doc,
        "plan_candidate": plan_candidate, "form_candidate": form_candidate,
        "frontage_candidate": frontage_candidate,
    }


# --------------------------------------------------------------------------- #
# app/extraction.py — list_case_fields / contested detection
# --------------------------------------------------------------------------- #


def test_list_case_fields_returns_both_fields(seeded, conn):
    rows = extraction_mod.list_case_fields(conn, seeded["case_id"])
    labels = {r["field_def"]["label"] for r in rows}
    assert labels == {"Side Setback", "Lot Frontage"}


def test_disagreeing_candidates_are_contested_with_no_winner_preselected(seeded, conn):
    rows = extraction_mod.list_case_fields(conn, seeded["case_id"])
    setback = next(r for r in rows if r["field_def"]["label"] == "Side Setback")

    assert setback["contested"] is True
    assert setback["display_state"] == "contested"
    assert len(setback["candidates"]) == 2
    # Highest source_priority (the plan) sorts first, but neither is chosen.
    assert setback["candidates"][0]["document_id"] == seeded["plan_doc"]
    assert setback["value"] is None


def test_agreeing_single_candidate_is_not_contested(seeded, conn):
    rows = extraction_mod.list_case_fields(conn, seeded["case_id"])
    frontage = next(r for r in rows if r["field_def"]["label"] == "Lot Frontage")
    assert frontage["contested"] is False
    assert frontage["display_state"] == "unconfirmed"


def test_citation_text_is_rendered_from_the_struct(seeded, conn):
    rows = extraction_mod.list_case_fields(conn, seeded["case_id"])
    setback = next(r for r in rows if r["field_def"]["label"] == "Side Setback")
    assert setback["citation_text"] == "Article 2, D1-Rural District, Primary Building Placement: Side Setback"


def test_list_case_fields_unknown_case_raises(conn):
    with pytest.raises(extraction_mod.CaseNotFound):
        extraction_mod.list_case_fields(conn, "nope")


# --------------------------------------------------------------------------- #
# confirm_field / override_field / mark_not_applicable — one event each
# --------------------------------------------------------------------------- #


def _event_count(conn, case_id: str) -> int:
    return conn.execute("SELECT COUNT(*) FROM events WHERE case_id = ?;", (case_id,)).fetchone()[0]


def test_confirm_field_writes_exactly_one_event_and_chain_verifies(seeded, conn):
    before = _event_count(conn, seeded["case_id"])
    field = extraction_mod.confirm_field(
        conn, seeded["case_id"],
        field_def_id=seeded["setback_field"], subject_key=None,
        candidate_id=seeded["plan_candidate"],
        why="matches the recorded plan, sheet C-2", actor_user_id=security.SYNTHETIC_USER_ID,
    )
    after = _event_count(conn, seeded["case_id"])
    assert after == before + 1

    assert field["value"]["state"] == "confirmed"
    assert field["value"]["chosen_candidate_id"] == seeded["plan_candidate"]
    assert field["value"]["value_num"] == 12.0
    # Contested no longer presented as contested once decided.
    assert field["contested"] is False
    assert field["display_state"] == "confirmed"

    ok, bad_seq = audit_mod.verify_chain(conn)
    assert ok is True
    assert bad_seq is None

    ev = conn.execute(
        "SELECT * FROM events WHERE kind = 'field_value.confirmed' ORDER BY seq DESC LIMIT 1;"
    ).fetchone()
    payload = json.loads(ev["payload_json"])
    assert payload["candidate_id"] == seeded["plan_candidate"]
    assert payload["why"] == "matches the recorded plan, sheet C-2"
    assert ev["actor_user_id"] == security.SYNTHETIC_USER_ID


def test_confirm_field_requires_why(seeded, conn):
    with pytest.raises(extraction_mod.ValidationError):
        extraction_mod.confirm_field(
            conn, seeded["case_id"],
            field_def_id=seeded["setback_field"], subject_key=None,
            candidate_id=seeded["plan_candidate"],
            why="   ", actor_user_id=security.SYNTHETIC_USER_ID,
        )
    # Nothing written.
    assert conn.execute("SELECT COUNT(*) FROM field_values;").fetchone()[0] == 0


def test_confirm_field_rejects_a_candidate_from_a_different_field(seeded, conn):
    with pytest.raises(extraction_mod.CandidateNotFound):
        extraction_mod.confirm_field(
            conn, seeded["case_id"],
            field_def_id=seeded["frontage_field"], subject_key=None,
            candidate_id=seeded["plan_candidate"],  # belongs to setback_field
            why="oops", actor_user_id=security.SYNTHETIC_USER_ID,
        )


def test_override_field_writes_exactly_one_event_and_requires_reason(seeded, conn):
    before = _event_count(conn, seeded["case_id"])
    field = extraction_mod.override_field(
        conn, seeded["case_id"],
        field_def_id=seeded["setback_field"], subject_key=None,
        value_num=11.5, value_text=None, unit="ft",
        reason="surveyed on site, differs from both the plan and the form",
        actor_user_id=security.SYNTHETIC_USER_ID,
    )
    after = _event_count(conn, seeded["case_id"])
    assert after == before + 1
    assert field["value"]["state"] == "overridden"
    assert field["value"]["value_num"] == 11.5
    assert field["value"]["override_reason"]

    ok, _ = audit_mod.verify_chain(conn)
    assert ok is True

    with pytest.raises(extraction_mod.ValidationError):
        extraction_mod.override_field(
            conn, seeded["case_id"],
            field_def_id=seeded["setback_field"], subject_key=None,
            value_num=9.0, value_text=None, unit="ft", reason="",
            actor_user_id=security.SYNTHETIC_USER_ID,
        )


def test_mark_not_applicable_writes_exactly_one_event(seeded, conn):
    before = _event_count(conn, seeded["case_id"])
    field = extraction_mod.mark_not_applicable(
        conn, seeded["case_id"],
        field_def_id=seeded["frontage_field"], subject_key=None,
        why="this lot is exempt under the frontage waiver",
        actor_user_id=security.SYNTHETIC_USER_ID,
    )
    after = _event_count(conn, seeded["case_id"])
    assert after == before + 1
    assert field["value"]["state"] == "not_applicable"

    ok, _ = audit_mod.verify_chain(conn)
    assert ok is True


def test_confirm_then_reconfirm_updates_the_same_field_values_row(seeded, conn):
    first = extraction_mod.confirm_field(
        conn, seeded["case_id"],
        field_def_id=seeded["setback_field"], subject_key=None,
        candidate_id=seeded["plan_candidate"], why="plan governs",
        actor_user_id=security.SYNTHETIC_USER_ID,
    )
    second = extraction_mod.confirm_field(
        conn, seeded["case_id"],
        field_def_id=seeded["setback_field"], subject_key=None,
        candidate_id=seeded["form_candidate"], why="corrected after re-reading the form",
        actor_user_id=security.SYNTHETIC_USER_ID,
    )
    assert first["value"]["id"] == second["value"]["id"]
    assert second["value"]["value_num"] == 10.0
    assert conn.execute("SELECT COUNT(*) FROM field_values;").fetchone()[0] == 1


# --------------------------------------------------------------------------- #
# Absence worklist + form generation
# --------------------------------------------------------------------------- #


def test_absence_worklist_lists_case_level_fields_with_no_evidence(seeded, conn):
    # ingest/worklist.py (the authoritative implementation this delegates to)
    # seeds its own canonical ~23 case-level fields (Applicant, Owner Deed
    # Reference, Tax Lot, ...) on first call -- none of them have any
    # field_candidates in this fixture, so every one of them is outstanding.
    worklist = extraction_mod.list_absence_worklist(conn, seeded["case_id"])
    labels = {item["label"] for group in worklist["groups"] for item in group["fields"]}
    assert "Owner Deed Reference" in labels
    assert worklist["count"] == len(labels) > 0
    # District-scoped Article-2 dimensional fields (Side Setback, Lot
    # Frontage) are a different lifecycle -- never part of THIS worklist,
    # evidence or not.
    assert "Side Setback" not in labels
    assert "Lot Frontage" not in labels


def test_absence_worklist_falls_back_when_ingest_worklist_unavailable(seeded, conn, monkeypatch):
    monkeypatch.setattr(extraction_mod, "_worklist_mod", None)
    extra_field = _seed_field_def(
        conn, seeded["ruleset_id"], district_key="d1", field_key="lot_dimensions.width",
        label="Lot Width", panel_title="LOT DIMENSIONS",
    )
    worklist = extraction_mod.list_absence_worklist(conn, seeded["case_id"])
    labels = {item["label"] for group in worklist["groups"] for item in group["fields"]}
    assert "Lot Width" in labels
    assert "Side Setback" not in labels  # has candidates
    assert "Lot Frontage" not in labels  # has a candidate
    assert worklist["count"] == len(labels)


def test_case_form_generation_unknown_renders_as_unknown(conn):
    ruleset_id = _seed_ruleset(conn)
    case_id = _seed_case(conn, ruleset_id)
    conn.execute("UPDATE cases SET form_generation = 'unknown' WHERE id = ?;", (case_id,))
    gen = extraction_mod.case_form_generation(conn, case_id)
    assert gen["unknown"] is True
    assert gen["generation"] == "unknown"


def test_case_form_generation_with_no_documents_is_silently_none(conn):
    # A case with NO documents at all has nothing to detect from -- silent
    # None (nothing has been tried), never a loud 'unknown' (an empty
    # intake is not a failed detection).
    ruleset_id = _seed_ruleset(conn)
    case_id = _seed_case(conn, ruleset_id)
    gen = extraction_mod.case_form_generation(conn, case_id)
    assert gen["generation"] is None
    assert gen["unknown"] is False


def test_case_form_generation_falls_back_to_the_text_only_detector(seeded, conn):
    # The `seeded` fixture's documents carry no page text at all (a case
    # with documents on file, but no persisted documents.generation yet and
    # no readable text) -- ingest/worklist.py's own lighter, on-the-fly,
    # text-only detector is consulted and honestly reports 'unknown' rather
    # than staying silent, because there IS something (a form document) that
    # detection was actually attempted against.
    gen = extraction_mod.case_form_generation(conn, seeded["case_id"])
    assert gen["generation"] == "unknown"
    assert gen["unknown"] is True


def test_case_form_generation_prefers_persisted_document_generation(seeded, conn):
    # ingest/formgen.py's richer, OCR-aware per-document detection
    # (documents.generation) outranks the text-only fallback once it has run.
    conn.execute("UPDATE documents SET generation = 'gen1' WHERE id = ?;", (seeded["form_doc"],))
    gen = extraction_mod.case_form_generation(conn, seeded["case_id"])
    assert gen["generation"] == "gen1"
    assert gen["unknown"] is False


# --------------------------------------------------------------------------- #
# HTTP layer — app/routes/extraction.py
# --------------------------------------------------------------------------- #


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)

    ruleset_id = _seed_ruleset(conn)
    case_id = _seed_case(conn, ruleset_id)
    plan_doc = _seed_document(conn, case_id, kind="plan", priority=100, title="Site Plan, Sheet C-2")
    form_doc = _seed_document(conn, case_id, kind="form", priority=40, title="Zoning Permit Application")
    plan_page = _seed_page(conn, plan_doc, page_number=2)
    form_page = _seed_page(conn, form_doc, page_number=1)
    setback_field = _seed_field_def(
        conn, ruleset_id, district_key="d1", field_key="primary_building_placement.side_setback",
        label="Side Setback",
    )
    plan_candidate = _seed_candidate(
        conn, case_id, setback_field, document_id=plan_doc, page_id=plan_page,
        source_priority=100, value_num=12.0, raw_text="12'", extractor="table", confidence=0.95,
    )
    form_candidate = _seed_candidate(
        conn, case_id, setback_field, document_id=form_doc, page_id=form_page,
        source_priority=40, value_num=10.0, raw_text="Side Setback: 10", extractor="regex", confidence=0.6,
    )
    conn.close()

    app = FastAPI()
    app.include_router(extraction_routes.router)
    with TestClient(app) as c:
        yield {
            "client": c, "case_id": case_id, "setback_field": setback_field,
            "plan_candidate": plan_candidate, "form_candidate": form_candidate,
            "db_path": tmp_path / "permit-review.db",
        }


def test_review_page_renders_for_a_seeded_case_with_candidates(client):
    resp = client["client"].get(f"/cases/{client['case_id']}/extraction")
    assert resp.status_code == 200
    body = resp.text
    assert "Side Setback" in body
    assert "Site Plan, Sheet C-2" in body
    assert "Zoning Permit Application" in body


def test_contested_field_renders_both_values_side_by_side(client):
    resp = client["client"].get(f"/cases/{client['case_id']}/extraction")
    body = resp.text
    assert "field-card-contested" in body
    assert "Sources disagree" in body
    # both candidate values appear
    assert "12.0" in body or "12" in body
    assert "10.0" in body or "10" in body


def test_review_page_unknown_case_returns_404(client):
    resp = client["client"].get("/cases/does-not-exist/extraction")
    assert resp.status_code == 404
    assert resp.json()["ok"] is False


def _conn_for(client):
    import sqlite3
    c = sqlite3.connect(str(client["db_path"]))
    c.row_factory = sqlite3.Row
    return c


def test_confirm_route_writes_one_event_and_chain_verifies(client):
    resp = client["client"].post(
        f"/api/cases/{client['case_id']}/fields/confirm",
        json={
            "field_def_id": client["setback_field"], "subject_key": None,
            "candidate_id": client["plan_candidate"], "why": "matches the plan",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["data"]["field"]["value"]["state"] == "confirmed"

    conn = _conn_for(client)
    try:
        n_events = conn.execute(
            "SELECT COUNT(*) FROM events WHERE case_id = ? AND kind = 'field_value.confirmed';",
            (client["case_id"],),
        ).fetchone()[0]
        assert n_events == 1
        ok, _ = audit_mod.verify_chain(conn)
        assert ok is True
    finally:
        conn.close()


def test_confirm_route_missing_why_is_validation_failed(client):
    resp = client["client"].post(
        f"/api/cases/{client['case_id']}/fields/confirm",
        json={
            "field_def_id": client["setback_field"], "subject_key": None,
            "candidate_id": client["plan_candidate"], "why": "",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "validation_failed"


def test_override_route_writes_one_event(client):
    resp = client["client"].post(
        f"/api/cases/{client['case_id']}/fields/override",
        json={
            "field_def_id": client["setback_field"], "subject_key": None,
            "value_num": 11.5, "value_text": None, "unit": "ft",
            "reason": "surveyed on site",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["field"]["value"]["state"] == "overridden"

    conn = _conn_for(client)
    try:
        n_events = conn.execute(
            "SELECT COUNT(*) FROM events WHERE case_id = ? AND kind = 'field_value.overridden';",
            (client["case_id"],),
        ).fetchone()[0]
        assert n_events == 1
        ok, _ = audit_mod.verify_chain(conn)
        assert ok is True
    finally:
        conn.close()


def test_not_applicable_route_writes_one_event(client):
    resp = client["client"].post(
        f"/api/cases/{client['case_id']}/fields/not-applicable",
        json={"field_def_id": client["setback_field"], "subject_key": None, "why": "waived"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["field"]["value"]["state"] == "not_applicable"

    conn = _conn_for(client)
    try:
        n_events = conn.execute(
            "SELECT COUNT(*) FROM events WHERE case_id = ? AND kind = 'field_value.marked_not_applicable';",
            (client["case_id"],),
        ).fetchone()[0]
        assert n_events == 1
        ok, _ = audit_mod.verify_chain(conn)
        assert ok is True
    finally:
        conn.close()


def test_blob_route_serves_bytes_inline(client, tmp_path: Path):
    conn = _conn_for(client)
    try:
        blobs_dir = tmp_path / "blobs" / "ab"
        blobs_dir.mkdir(parents=True, exist_ok=True)
        (blobs_dir / "abc123").write_bytes(b"%PDF-1.4 fake")
        now = _utc_now_iso()
        conn.execute(
            """
            INSERT INTO blobs (id, sha256, byte_size, media_type, original_name, rel_path, created_at)
            VALUES ('blob1', 'abc123', 13, 'application/pdf', 'test.pdf', 'data/blobs/ab/abc123', ?);
            """,
            (now,),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client["client"].get("/api/blobs/blob1")
    assert resp.status_code == 200
    assert resp.content == b"%PDF-1.4 fake"
    assert resp.headers["content-type"] == "application/pdf"


def test_blob_route_unknown_id_returns_404(client):
    resp = client["client"].get("/api/blobs/does-not-exist")
    assert resp.status_code == 404
