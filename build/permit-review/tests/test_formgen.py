"""Tests for ingest/formgen.py — form-generation + module-set detection.

Offline, no network, no LLM, no vision model. Exercises synthetic PDFs (both
a native-text path and an image-only "fake scan" path, built in-process with
PyMuPDF — see _make_native_pdf / _make_scanned_pdf) and all EIGHT real
fixture files named in this workflow's task brief (read-only, under docs/ —
never modified). The OCR-dependent tests additionally require the
`tesseract` binary on PATH; they skip (not fail) when it is absent, matching
this repo's own established convention for an optional external tool
(CONTRACT.md §1.1 S6 check 8's pandoc/typst SKIP pattern).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

import fitz  # noqa: E402

from ingest import formgen  # noqa: E402

REPO_ROOT = APP_ROOT.parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"

MORRISSEY = FIXTURES_DIR / "M011, L046-A (Morrissey, 53 Pleasant Street) SLZ Application, 2025 Submitted Documents.pdf"
PROFENNO = FIXTURES_DIR / "M003, L065-B (Profenno, Perkins Point Rd) Planning Board Application 2024.06.05.pdf"
STANTEC = FIXTURES_DIR / "M004, L087 (NT Land III, 684 US Route 1) (Stantec) application 2024.05.08.pdf"
BLOOD = FIXTURES_DIR / "5.A.2 M012, L004 (15 Hall St, Blood and Sons) Zoning Application.pdf"
ACADEMY = FIXTURES_DIR / "M012, L011 (Z38, 38 Academy Hill Rd) Application 2024.07.03 04 Zoning Permit App.pdf"
SHATTUCK = FIXTURES_DIR / "4.A.1. M003, L059 (White Rd, Shattuck) Subdivision Application 2025.10.07.pdf"
VERNEY = FIXTURES_DIR / "4.B1. M004, L036 (461 Sheepscot Rd, Verney) Use Application 2025.04.02.pdf"
DALTON = FIXTURES_DIR / "M002, L053 (976 US Rt 1, Dalton) 2025.09.09 Application.pdf"

ALL_FIXTURES = [MORRISSEY, PROFENNO, STANTEC, BLOOD, ACADEMY, SHATTUCK, VERNEY, DALTON]

requires_fixtures = pytest.mark.skipif(
    not all(p.exists() for p in ALL_FIXTURES),
    reason="real Findings of Fact fixture PDFs not present under docs/",
)
requires_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract binary not on PATH"
)


# --------------------------------------------------------------------------- #
# Synthetic PDF builders.
# --------------------------------------------------------------------------- #


def _make_native_pdf(tmp_path: Path, pages: list[str], name: str = "native.pdf") -> Path:
    """A PDF whose pages carry REAL, selectable text — each string in
    `pages` becomes one page's full text."""
    doc = fitz.open()
    for text in pages:
        page = doc.new_page(width=612, height=792)
        page.insert_textbox(fitz.Rect(20, 20, 592, 772), text, fontsize=11)
    out = tmp_path / name
    doc.save(str(out))
    doc.close()
    return out


def _make_scanned_pdf(
    tmp_path: Path, pages: list[str], name: str = "scanned.pdf", footer: str | None = None
) -> Path:
    """A PDF that LOOKS like `pages`' text when rendered but carries NO
    selectable text layer at all — each page is built by rendering the text
    to a pixmap and re-inserting that pixmap as a full-page IMAGE on a fresh
    blank page, exactly mirroring what a real flatbed-scanned application
    looks like to PyMuPDF (char_count == 0 everywhere; content only readable
    via OCR). Mirrors the real pure-scan fixtures' shape.

    `footer`, when given, is placed in its own rect pinned to the bottom
    ~10% of PAGE 1 specifically (mirroring where the real Gen-2 fixtures'
    footer version stamp actually sits — see ingest/formgen.py's
    _FOOTER_BAND_FRACTION) rather than relying on blank-line padding to push
    body text down, which insert_textbox does not lay out predictably
    enough to land in a specific fractional band."""
    out_doc = fitz.open()
    for i, text in enumerate(pages):
        src = fitz.open()
        src_page = src.new_page(width=612, height=792)
        src_page.insert_textbox(fitz.Rect(20, 20, 592, 500), text, fontsize=14)
        if i == 0 and footer:
            src_page.insert_textbox(fitz.Rect(20, 730, 592, 772), footer, fontsize=12)
        pix = src_page.get_pixmap(matrix=fitz.Matrix(2, 2))
        src.close()

        page = out_doc.new_page(width=612, height=792)
        page.insert_image(page.rect, pixmap=pix)
    out = tmp_path / name
    out_doc.save(str(out))
    out_doc.close()
    return out


# --------------------------------------------------------------------------- #
# Native-text path — no OCR involved at all.
# --------------------------------------------------------------------------- #


def test_native_gen1_fingerprint_is_detected_high_confidence(tmp_path: Path):
    pdf = _make_native_pdf(
        tmp_path,
        [
            "Zoning Permit\nApplication\n\nTax Map / Lot\n\nCONTACT INFORMATION",
            "TOWN OF NEWCASTLE\nZONING PERMIT APPLICATION\nOFFICE ADMINSTRATION USE ONLY\n\n"
            "DEVELOPMENT REVIEW TYPE:",
        ],
    )
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "high"
    assert result["modules"] == []
    assert result["version_stamp"] is None
    assert any(e["signal"] == "gen1_fingerprint" for e in result["evidence"])


def test_native_gen1_fingerprint_found_deep_in_a_larger_packet(tmp_path: Path):
    # Mirrors the real Profenno fixture: several unrelated native-text pages
    # (a cover letter, narrative sections) before the actual form page — the
    # fingerprint is NOT on page 1-3, so this only passes if the whole
    # document's native text is searched, not just an early-page window.
    pages = ["Dear Planning Board,\n\nThis is a cover letter about a proposed subdivision." * 3] * 5
    pages.append(
        "TOWN OF NEWCASTLE\nZONING PERMIT APPLICATION\nOFFICE ADMINSTRATION USE ONLY\n\nPERMIT NUMBER:"
    )
    pdf = _make_native_pdf(tmp_path, pages)
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "high"
    assert result["evidence"][0]["page"] == 6


def test_native_gen1_secondary_title_only_is_medium_confidence(tmp_path: Path):
    # Mirrors the real Stantec fixture: the specific typo'd fingerprint is
    # never found in the text layer at all, but the form's own plain title
    # appears (e.g. a cover letter's own attachment list).
    pdf = _make_native_pdf(
        tmp_path,
        ["Dear Board,\n\nATTACHMENT A: ZONING PERMIT APPLICATION FORM\n\nSee attached."],
    )
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "medium"
    assert all(e["signal"] != "gen1_fingerprint" for e in result["evidence"])


def test_native_gen2_with_version_stamp_is_high_confidence_with_modules(tmp_path: Path):
    pdf = _make_native_pdf(
        tmp_path,
        [
            "PLANNING APPLICATION\nCover Sheet\n\nMap: 3 Lot: 59\n\nv.2024.09.26",
            "NEWCASTLE PLANNING APPLICATION\nSubdivision Form\n\nExisting Lot(s):",
        ],
    )
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen2"
    assert result["confidence"] == "high"
    assert result["version_stamp"] == "v.2024.09.26"
    assert set(result["modules"]) == {"cover", "subdivision_form"}


def test_native_gen2_without_version_stamp_is_medium_confidence(tmp_path: Path):
    pdf = _make_native_pdf(tmp_path, ["PLANNING APPLICATION\nCover Sheet\n\nMap: 4 Lot: 36"])
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen2"
    assert result["confidence"] == "medium"
    assert result["version_stamp"] is None


def test_neither_fingerprint_present_is_unknown_not_gen1(tmp_path: Path):
    # The task brief's own explicit requirement: an unseen/third generation
    # must resolve to 'unknown' and MUST NOT fall back to gen1.
    pdf = _make_native_pdf(
        tmp_path,
        ["GEN-3 SUPER APPLICATION FORM\n\nSome future layout nobody has designed yet.\n" * 3],
    )
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "unknown"
    assert result["confidence"] == "low"
    assert result["modules"] == []
    assert result["version_stamp"] is None


def test_empty_pdf_is_unknown(tmp_path: Path):
    doc = fitz.open()
    out = tmp_path / "truly-empty.pdf"
    doc.new_page(width=612, height=792)  # a page, but with no text at all
    doc.save(str(out))
    doc.close()
    result = formgen.detect_generation(out)
    assert result["generation"] == "unknown"


def test_result_is_json_serializable(tmp_path: Path):
    import json

    pdf = _make_native_pdf(tmp_path, ["PLANNING APPLICATION\nCover Sheet\n\nv.2024.09.26"])
    result = formgen.detect_generation(pdf)
    json.dumps(result)  # must not raise


# --------------------------------------------------------------------------- #
# OCR (pure-scan) path — synthetic image-only PDFs.
# --------------------------------------------------------------------------- #


@requires_tesseract
def test_scanned_gen1_fingerprint_detected_via_header_ocr(tmp_path: Path):
    pdf = _make_scanned_pdf(
        tmp_path,
        [
            "Zoning Permit\nApplication\n\nTax Map / Lot\nCONTACT INFORMATION",
            "TOWN OF NEWCASTLE\nZONING PERMIT APPLICATION\nOFFICE ADMINSTRATION USE ONLY\n\n"
            "DEVELOPMENT REVIEW TYPE",
        ],
    )
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "high"
    assert any(e["source"] == "ocr_header_band" for e in result["evidence"])


@requires_tesseract
def test_scanned_gen2_with_footer_version_stamp_detected(tmp_path: Path):
    pdf = _make_scanned_pdf(
        tmp_path,
        ["PLANNING APPLICATION\nCover Sheet\n\nMap: 3 Lot: 59"],
        footer="Date Received: v.2024.09.26",
    )
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "gen2"
    assert result["version_stamp"] == "v.2024.09.26"
    assert result["confidence"] == "high"


@requires_tesseract
def test_scanned_neither_fingerprint_is_unknown(tmp_path: Path):
    pdf = _make_scanned_pdf(tmp_path, ["Just a random cover letter with no form title at all."])
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "unknown"


def test_ocr_unavailable_returns_unknown_not_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(formgen, "_tesseract_available", lambda: False)
    pdf = _make_scanned_pdf(tmp_path, ["TOWN OF NEWCASTLE\nOFFICE ADMINSTRATION USE ONLY"])
    result = formgen.detect_generation(pdf)
    assert result["generation"] == "unknown"
    assert result["confidence"] == "low"


def test_ocr_band_raises_ocr_unavailable_when_tesseract_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(formgen, "_tesseract_available", lambda: False)
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    with pytest.raises(formgen.OcrUnavailable):
        formgen._ocr_band(page, top=0.0, bottom=0.2)
    doc.close()


# --------------------------------------------------------------------------- #
# Real fixture files — the task brief's own ground truth, all EIGHT.
# --------------------------------------------------------------------------- #


@requires_fixtures
def test_morrissey_gen2_native_modules():
    result = formgen.detect_generation(MORRISSEY)
    assert result["generation"] == "gen2"
    assert result["confidence"] == "high"
    assert result["version_stamp"] == "v.2024.09.26"
    assert set(result["modules"]) == {"cover", "shoreland_form", "other_structures"}


@requires_fixtures
def test_profenno_gen1_mixed_fingerprint_native():
    result = formgen.detect_generation(PROFENNO)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "high"
    assert result["modules"] == []
    assert any(e["signal"] == "gen1_fingerprint" and e["source"] == "native_text" for e in result["evidence"])


@requires_fixtures
def test_stantec_gen1_trap_resolved_without_reading_the_trap_page():
    result = formgen.detect_generation(STANTEC)
    assert result["generation"] == "gen1"
    # The literal fingerprint lives only inside a scanned image on page 10
    # (the task brief's own "Tier B trap" page) — this must resolve WITHOUT
    # ever reading that page's image content (no OCR needed/used at all,
    # since substantial native text exists elsewhere in the packet).
    assert all(e["source"] == "native_text" for e in result["evidence"])
    assert all(e["page"] != 10 for e in result["evidence"])


@requires_fixtures
@requires_tesseract
def test_blood_and_sons_gen1_pure_scan():
    result = formgen.detect_generation(BLOOD)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "high"
    assert result["modules"] == []


@requires_fixtures
@requires_tesseract
def test_academy_hill_gen1_pure_scan():
    result = formgen.detect_generation(ACADEMY)
    assert result["generation"] == "gen1"
    assert result["confidence"] == "high"
    assert result["modules"] == []


@requires_fixtures
@requires_tesseract
def test_shattuck_gen2_pure_scan_subdivision_modules():
    result = formgen.detect_generation(SHATTUCK)
    assert result["generation"] == "gen2"
    assert set(result["modules"]) == {"cover", "subdivision_form"}


@requires_fixtures
@requires_tesseract
def test_verney_gen2_pure_scan_use_form_module():
    result = formgen.detect_generation(VERNEY)
    assert result["generation"] == "gen2"
    assert set(result["modules"]) == {"cover", "use_form"}


@requires_fixtures
@requires_tesseract
def test_dalton_gen2_pure_scan_four_modules():
    result = formgen.detect_generation(DALTON)
    assert result["generation"] == "gen2"
    assert set(result["modules"]) == {"cover", "shoreland_form", "building_form", "components"}


@requires_fixtures
@requires_tesseract
def test_all_eight_real_applications_never_produce_a_false_gen1_fallback():
    """UNKNOWN GENERATION MUST FAIL LOUDLY, never silently default to gen1 --
    a blanket sanity sweep over all eight real fixtures: whatever each one
    resolves to, it must be a real, evidenced verdict (every 'gen1' result
    carries at least one gen1_fingerprint or gen1_title piece of evidence;
    every 'gen2' carries a gen2_title)."""
    for path in ALL_FIXTURES:
        result = formgen.detect_generation(path)
        assert result["generation"] in ("gen1", "gen2", "unknown")
        if result["generation"] == "gen1":
            assert any(e["signal"] in ("gen1_fingerprint", "gen1_title") for e in result["evidence"])
        elif result["generation"] == "gen2":
            assert any(e["signal"] == "gen2_title" for e in result["evidence"])


# --------------------------------------------------------------------------- #
# derive_review_type() / cross_check_review_type().
# --------------------------------------------------------------------------- #


def test_subdivision_module_set_resolves_planning_board_outright():
    hint = formgen.derive_review_type("gen2", ["cover", "subdivision_form"])
    assert hint["application_type"] == "subdivision"
    assert hint["authority"] == "Planning Board"
    assert hint["needs_use_matrix_check"] is False


def test_use_module_set_is_unresolved_pending_use_matrix():
    hint = formgen.derive_review_type("gen2", ["cover", "use_form"])
    assert hint["application_type"] == "use"
    assert hint["authority"] is None
    assert hint["needs_use_matrix_check"] is True


def test_shoreland_module_set_is_unresolved_with_supplementary_modules_named():
    hint = formgen.derive_review_type("gen2", ["cover", "shoreland_form", "other_structures"])
    assert hint["application_type"] == "shoreland"
    assert hint["authority"] is None
    assert hint["needs_use_matrix_check"] is True
    assert "other_structures" in hint["supplementary_modules"]


def test_gen1_has_no_module_derived_hint():
    hint = formgen.derive_review_type("gen1", [])
    assert hint["application_type"] is None
    assert hint["needs_use_matrix_check"] is False


def test_module_set_with_no_primary_driver_is_unresolved():
    hint = formgen.derive_review_type("gen2", ["cover", "building_form", "components"])
    assert hint["application_type"] is None
    assert hint["needs_use_matrix_check"] is True


def test_cross_check_supplies_authority_when_module_hint_had_none():
    hint = formgen.derive_review_type("gen2", ["cover", "use_form"])
    result = formgen.cross_check_review_type(hint, district_key="d1", use_key="residence")
    assert result["status"] == "insufficient_data"
    assert result["use_matrix_derivation"]["authority"] == "CEO"


def test_cross_check_agrees_when_authorities_match():
    hint = {"application_type": "use", "authority": "CEO", "needs_use_matrix_check": False, "basis": "test"}
    result = formgen.cross_check_review_type(hint, district_key="d1", use_key="residence")
    assert result["status"] == "agree"


def test_cross_check_disagrees_and_records_both_derivations_never_picking_one():
    hint = {
        "application_type": "use",
        "authority": "Planning Board",  # deliberately wrong vs. the real use-matrix
        "needs_use_matrix_check": False,
        "basis": "test",
    }
    result = formgen.cross_check_review_type(hint, district_key="d1", use_key="residence")
    assert result["status"] == "disagree"
    assert result["needs_operator_resolution"] is True
    assert result["module_derivation"]["authority"] == "Planning Board"
    assert result["use_matrix_derivation"]["authority"] == "CEO"


def test_cross_check_insufficient_data_when_district_or_use_missing():
    hint = formgen.derive_review_type("gen2", ["cover", "use_form"])
    result = formgen.cross_check_review_type(hint, district_key=None, use_key=None)
    assert result["status"] == "insufficient_data"
    assert result["use_matrix_derivation"] is None


def test_cross_check_propagates_unknown_use_from_reviews_module():
    from app import reviews

    hint = {"application_type": "use", "authority": "CEO", "needs_use_matrix_check": False, "basis": "test"}
    with pytest.raises(reviews.UnknownUse):
        formgen.cross_check_review_type(hint, district_key="d1", use_key="not-a-real-use")


# --------------------------------------------------------------------------- #
# persist_formgen_result() — DB write + audit event.
# --------------------------------------------------------------------------- #


@pytest.fixture()
def db_conn(tmp_path: Path):
    from app import db, security

    conn = db.connect(tmp_path / "formgen-test.db")
    db.migrate(conn, APP_ROOT / "app" / "migrations")
    security.ensure_synthetic_user(conn)
    yield conn
    conn.close()


def _make_case_and_document(conn) -> tuple[str, str]:
    import uuid
    from datetime import datetime, timezone

    def now_iso() -> str:
        now = datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

    now = now_iso()
    ruleset_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, built_at,
             builder_version, manifest_path, source_sha_json, created_at)
        VALUES (?, 'test-ruleset', 'Test Ruleset', 0, 'adopted', ?, 'test',
                'rulesets/test/manifest.json', '{}', ?);
        """,
        (ruleset_id, now, now),
    )
    case_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO cases (id, label, application_type, ruleset_id, is_scratch, created_at, updated_at)
        VALUES (?, 'Test Case', 'use', ?, 1, ?, ?);
        """,
        (case_id, ruleset_id, now, now),
    )
    doc_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO documents
            (id, case_id, kind, source_priority, title, created_at)
        VALUES (?, ?, 'form', 40, 'Test Form', ?);
        """,
        (doc_id, case_id, now),
    )
    return case_id, doc_id


def test_persist_formgen_result_writes_columns_and_audit_event(db_conn):
    case_id, doc_id = _make_case_and_document(db_conn)
    result = {
        "generation": "gen2",
        "confidence": "high",
        "version_stamp": "v.2024.09.26",
        "modules": ["subdivision_form", "cover"],
        "evidence": [{"page": 1, "signal": "gen2_title", "matched": "PLANNING APPLICATION", "source": "native_text"}],
    }
    db_conn.execute("BEGIN;")
    formgen.persist_formgen_result(
        db_conn, document_id=doc_id, case_id=case_id, result=result, actor_user_id="u_local_operator"
    )
    db_conn.execute("COMMIT;")

    row = dict(db_conn.execute("SELECT * FROM documents WHERE id = ?;", (doc_id,)).fetchone())
    assert row["generation"] == "gen2"
    assert row["version_stamp"] == "v.2024.09.26"

    import json

    assert json.loads(row["module_set"]) == ["cover", "subdivision_form"]  # sorted
    assert row["formgen_confidence"] == "high"
    assert json.loads(row["formgen_evidence_json"]) == result["evidence"]

    event = db_conn.execute(
        "SELECT * FROM events WHERE kind = 'document.formgen_detected' AND entity_id = ?;", (doc_id,)
    ).fetchone()
    assert event is not None

    from app import audit

    ok, bad_seq = audit.verify_chain(db_conn)
    assert ok, f"audit chain broke at seq {bad_seq}"


def test_persist_formgen_result_unknown_generation_writes_empty_modules(db_conn):
    case_id, doc_id = _make_case_and_document(db_conn)
    result = {"generation": "unknown", "confidence": "low", "version_stamp": None, "modules": [], "evidence": []}
    db_conn.execute("BEGIN;")
    formgen.persist_formgen_result(
        db_conn, document_id=doc_id, case_id=case_id, result=result, actor_user_id="u_local_operator"
    )
    db_conn.execute("COMMIT;")

    row = dict(db_conn.execute("SELECT * FROM documents WHERE id = ?;", (doc_id,)).fetchone())
    assert row["generation"] == "unknown"
    assert row["module_set"] == "[]"
