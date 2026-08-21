"""Route-level tests for app/routes/documents.py — document upload, listing,
content-addressed blob dedup, and page census/tiering, end-to-end through a
real (mounted) FastAPI app + TestClient.

Offline, no network. A throwaway temp-dir SQLite file + a monkeypatched
app.config.DATA_DIR per test (see tests/test_blobs.py for the same
convention). Exercises the three REAL fixture PDFs named in this workflow's
task brief (read-only, under docs/ — never modified).
"""

from __future__ import annotations

import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import audit as audit_mod  # noqa: E402
from app import config, db, security  # noqa: E402
from app.routes import documents  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"

REPO_ROOT = APP_ROOT.parent.parent
FIXTURES_DIR = REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"
SHATTUCK = FIXTURES_DIR / "4.A.1. M003, L059 (White Rd, Shattuck) Subdivision Application 2025.10.07.pdf"
MORRISSEY = FIXTURES_DIR / "M011, L046-A (Morrissey, 53 Pleasant Street) SLZ Application, 2025 Submitted Documents.pdf"
STANTEC = FIXTURES_DIR / "M004, L087 (NT Land III, 684 US Route 1) (Stantec) application 2024.05.08.pdf"
requires_fixtures = pytest.mark.skipif(
    not (SHATTUCK.exists() and MORRISSEY.exists() and STANTEC.exists()),
    reason="real Findings of Fact fixture PDFs not present under docs/",
)


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _make_case(conn, *, is_scratch: int = 1, binding: int = 0) -> str:
    """Minimal, forward-compatible fixture: relies on column DEFAULTs for
    everything not load-bearing for these tests, so it keeps working as the
    `cases`/`rulesets` tables grow columns elsewhere in this workflow."""
    now = _utc_now_iso()
    ruleset_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO rulesets
            (id, ruleset_key, label, binding, article_scheme, built_at,
             builder_version, manifest_path, source_sha_json, created_at)
        VALUES (?, ?, ?, ?, 'adopted', ?, 'test', 'rulesets/test/manifest.json', '{}', ?);
        """,
        (ruleset_id, f"test-{ruleset_id[:8]}", "Test Ruleset", binding, now, now),
    )
    case_id = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO cases (id, label, application_type, ruleset_id, is_scratch, created_at, updated_at)
        VALUES (?, ?, 'use', ?, ?, ?, ?);
        """,
        (case_id, "M003, L059 (White Rd, Test Case)", ruleset_id, is_scratch, now, now),
    )
    return case_id


@pytest.fixture()
def app_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    case_id = _make_case(conn)

    app = FastAPI()
    app.include_router(documents.router)
    client = TestClient(app)

    try:
        yield client, conn, case_id
    finally:
        conn.close()


def _synthetic_pdf_bytes(tmp_path: Path, *, text: str = "Applicant: Jane Doe\n" * 20) -> bytes:
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(36, 36, 576, 756), text, fontsize=11)
    out = tmp_path / "synthetic-upload.pdf"
    doc.save(str(out))
    doc.close()
    return out.read_bytes()


# --------------------------------------------------------------------------- #
# Happy path.
# --------------------------------------------------------------------------- #


def test_upload_returns_document_blob_and_pages(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)

    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form", "title": "Application Form"},
        files={"file": ("application.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    doc = body["data"]["document"]
    assert doc["case_id"] == case_id
    assert doc["kind"] == "form"
    assert doc["source_priority"] == 40
    assert doc["doc_role"] == "application_form"
    assert doc["page_count"] == 1
    assert len(body["data"]["pages"]) == 1
    assert body["data"]["pages"][0]["tier"] == "A"
    assert body["data"]["blob"]["is_new"] is True
    assert body["data"]["tier_census"] == {"A": 1, "B": 0, "C": 0, "D": 0}

    # Actually landed in the DB.
    row = conn.execute("SELECT * FROM documents WHERE id = ?;", (doc["id"],)).fetchone()
    assert row is not None
    page_row = conn.execute("SELECT * FROM pages WHERE document_id = ?;", (doc["id"],)).fetchone()
    assert page_row["tier"] == "A"
    assert page_row["page_sha256"] is not None


def test_source_priority_mapping_matches_the_canonical_trigger_values(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)

    for doc_role, expected_kind, expected_priority in [
        ("plan_sheet", "plan", 100),
        ("survey", "survey", 90),
        ("deed", "deed", 80),
        ("application_form", "form", 40),
    ]:
        resp = client.post(
            f"/api/cases/{case_id}/documents",
            data={"doc_role": doc_role},
            files={"file": (f"{doc_role}.pdf", data, "application/pdf")},
        )
        assert resp.status_code == 200, resp.text
        doc = resp.json()["data"]["document"]
        assert doc["kind"] == expected_kind
        assert doc["source_priority"] == expected_priority
        assert doc["doc_role"] == doc_role


def test_unknown_doc_role_is_rejected(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "not_a_real_role"},
        files={"file": ("x.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["ok"] is False


def test_unknown_case_returns_404(app_env, tmp_path: Path):
    client, _conn, _case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    resp = client.post(
        "/api/cases/does-not-exist/documents",
        data={"doc_role": "application_form"},
        files={"file": ("x.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "unknown_case"


# --------------------------------------------------------------------------- #
# Content-type / size / traversal guards.
# --------------------------------------------------------------------------- #


def test_upload_rejects_non_pdf_content_type(app_env):
    client, _conn, case_id = app_env
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("x.png", b"\x89PNG\r\n", "image/png")},
    )
    assert resp.status_code == 415


def test_upload_rejects_pdf_content_type_with_wrong_magic_bytes(app_env):
    client, _conn, case_id = app_env
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("x.pdf", b"not really a pdf", "application/pdf")},
    )
    assert resp.status_code == 415


def test_upload_rejects_traversal_filename(app_env, tmp_path: Path):
    client, _conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("../../etc/passwd.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_filename"


def test_upload_rejects_a_corrupt_pdf_and_writes_nothing(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    # Passes the magic-byte sniff (starts with %PDF-) but is not a real,
    # openable PDF -- must be caught by triage, not by the sniff.
    bogus = b"%PDF-1.4\n" + b"garbage" * 50
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("bogus.pdf", bogus, "application/pdf")},
    )
    assert resp.status_code == 422
    assert resp.json()["error"] == "unreadable_pdf"

    # CONTRACT.md §1.1 S1: nothing reaches disk/DB on a validation failure.
    assert conn.execute("SELECT COUNT(*) AS n FROM documents;").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"] == 0
    tmp_dir = config.DATA_DIR / "tmp"
    assert not any(tmp_dir.glob("upload.tmp-*")) if tmp_dir.exists() else True


# --------------------------------------------------------------------------- #
# Blob dedup across two uploads with identical bytes.
# --------------------------------------------------------------------------- #


def test_reuploading_identical_bytes_dedupes_the_blob(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)

    r1 = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("first.pdf", data, "application/pdf")},
    )
    r2 = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "survey"},  # different doc_role/kind, same bytes
        files={"file": ("second-copy.pdf", data, "application/pdf")},
    )
    assert r1.status_code == 200 and r2.status_code == 200
    b1, b2 = r1.json()["data"]["blob"], r2.json()["data"]["blob"]
    assert b1["id"] == b2["id"]
    assert b1["is_new"] is True
    assert b2["is_new"] is False

    # Two DOCUMENT rows (different uploads), but exactly ONE blobs row.
    assert conn.execute("SELECT COUNT(*) AS n FROM documents;").fetchone()["n"] == 2
    assert conn.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"] == 1


# --------------------------------------------------------------------------- #
# The tier-D "plansheet forces source_priority 100" rule.
# --------------------------------------------------------------------------- #


def test_plansheet_page_forces_source_priority_100_even_for_a_form(app_env, tmp_path: Path):
    import fitz

    doc = fitz.open()
    page = doc.new_page(width=24 * 72, height=36 * 72)  # oversized -> tier D
    page.insert_textbox(fitz.Rect(36, 36, 24 * 72 - 36, 36 * 72 - 36), "Sheet C-2", fontsize=11)
    out = tmp_path / "mislabeled-plan.pdf"
    doc.save(str(out))
    doc.close()

    client, conn, case_id = app_env
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},  # submitter mis-labeled a plan set as a form
        files={"file": ("mislabeled-plan.pdf", out.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()["data"]["document"]
    assert result["doc_role"] == "application_form"  # preserved: what the submitter called it
    assert result["kind"] == "plan"  # reclassified: what triage found
    assert result["source_priority"] == 100
    assert resp.json()["data"]["tier_census"]["D"] == 1


# --------------------------------------------------------------------------- #
# Listing.
# --------------------------------------------------------------------------- #


def test_list_documents_returns_every_upload_with_tier_census(app_env, tmp_path: Path):
    client, _conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("a.pdf", data, "application/pdf")},
    )
    resp = client.get(f"/api/cases/{case_id}/documents")
    assert resp.status_code == 200
    docs = resp.json()["data"]["documents"]
    assert len(docs) == 1
    assert docs[0]["tier_census"] == {"A": 1, "B": 0, "C": 0, "D": 0}


def test_list_documents_unknown_case_returns_404(app_env):
    client, _conn, _case_id = app_env
    resp = client.get("/api/cases/does-not-exist/documents")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Real fixture files, end-to-end through the HTTP route.
# --------------------------------------------------------------------------- #


@requires_fixtures
def test_upload_the_real_shattuck_file_is_18_pages_all_tier_c(app_env):
    client, _conn, case_id = app_env
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "plan_sheet", "title": "Shattuck Subdivision Application"},
        files={"file": (SHATTUCK.name, SHATTUCK.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["document"]["page_count"] == 18
    assert data["tier_census"] == {"A": 0, "B": 0, "C": 18, "D": 0}


@requires_fixtures
def test_upload_the_real_morrissey_file_is_4_pages_all_tier_a(app_env):
    client, _conn, case_id = app_env
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "applicant_narrative", "title": "Morrissey SLZ Application"},
        files={"file": (MORRISSEY.name, MORRISSEY.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["document"]["page_count"] == 4
    assert data["tier_census"] == {"A": 4, "B": 0, "C": 0, "D": 0}


@requires_fixtures
def test_upload_the_real_stantec_file_is_56_pages_mixed(app_env):
    client, _conn, case_id = app_env
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "plan_sheet", "title": "Stantec Application"},
        files={"file": (STANTEC.name, STANTEC.read_bytes(), "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["document"]["page_count"] == 56
    non_native = sum(v for k, v in data["tier_census"].items() if k != "A")
    assert non_native >= 15


# --------------------------------------------------------------------------- #
# F13b -- a rejected-upload error body must never leak an absolute
# server-side filesystem path (previously: ingest.triage.UnreadablePdf's own
# message, which embeds the data/tmp/... temp path, went straight into the
# HTTP response via str(exc)).
# --------------------------------------------------------------------------- #


def test_unreadable_pdf_error_does_not_leak_the_absolute_temp_path(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    bogus = b"%PDF-1.4\n" + b"garbage" * 50
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},
        files={"file": ("bogus.pdf", bogus, "application/pdf")},
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "unreadable_pdf"
    # The absolute data/tmp path (this test's own tmp_path, which
    # config.DATA_DIR is monkeypatched to) must not appear anywhere in the
    # response body.
    assert str(config.DATA_DIR) not in resp.text
    assert "/tmp/" not in resp.text or str(config.DATA_DIR / "tmp") not in resp.text
    # Still useful to the client: the filename it uploaded (sanitized, no
    # path component -- see blobs.sanitize_original_name) is echoed back.
    assert "bogus.pdf" in body["message"]


# --------------------------------------------------------------------------- #
# F13c -- doc_date must be a real ISO date; a long title/filename must not
# become an equally long documents.title row.
# --------------------------------------------------------------------------- #


def test_upload_rejects_a_malformed_doc_date_and_writes_nothing(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form", "doc_date": "not-a-date"},
        files={"file": ("x.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["ok"] is False
    assert body["details"][0]["field"] == "doc_date"
    # CONTRACT.md §1.1 S1: validate-all-then-write -- rejected before any I/O.
    assert conn.execute("SELECT COUNT(*) AS n FROM documents;").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"] == 0


def test_upload_accepts_a_valid_doc_date(app_env, tmp_path: Path):
    client, _conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form", "doc_date": "2025-10-07"},
        files={"file": ("x.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["document"]["doc_date"] == "2025-10-07"


def test_a_pathologically_long_filename_does_not_become_an_equally_long_title(app_env, tmp_path: Path):
    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    # The adversarial review's own example was a 5000-char filename; that
    # length alone trips python-multipart's OWN per-header-line size cap
    # (DEFAULT_MAX_HEADER_SIZE, ~4.2KB, an unrelated limit in the multipart
    # parser itself, well upstream of this app's code) before this app ever
    # sees it. 1000 chars clears that limit while still being far longer
    # than _MAX_TITLE_LEN (300) -- comfortably proving the bound.
    long_name = ("A" * 1000) + ".pdf"
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form"},  # no explicit title -- derived from the filename
        files={"file": (long_name, data, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text  # a long filename must not fail the upload
    title = resp.json()["data"]["document"]["title"]
    assert len(title) <= documents._MAX_TITLE_LEN + 1  # +1 for the truncation marker
    row = conn.execute("SELECT title FROM documents WHERE id = ?;",
                        (resp.json()["data"]["document"]["id"],)).fetchone()
    assert len(row["title"]) <= documents._MAX_TITLE_LEN + 1


def test_an_explicit_long_title_is_also_bounded(app_env, tmp_path: Path):
    client, _conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    resp = client.post(
        f"/api/cases/{case_id}/documents",
        data={"doc_role": "application_form", "title": "B" * 5000},
        files={"file": ("x.pdf", data, "application/pdf")},
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["data"]["document"]["title"]) <= documents._MAX_TITLE_LEN + 1


# --------------------------------------------------------------------------- #
# F13a -- fault injection: a failure AFTER blobs.commit_blob() has already
# moved a brand-new blob's bytes into data/blobs/ (a SQL ROLLBACK cannot
# undo that rename) must not leave an orphaned file with no `blobs` row
# pointing at it. Forces the failure at the last possible moment inside the
# transaction (the audit event, right before COMMIT) so the blob row AND the
# documents/pages rows all really did exist, uncommitted, first -- the exact
# shape of the gap the adversarial review flagged as "latent, no naturally
# reachable trigger found".
# --------------------------------------------------------------------------- #


def test_a_failure_after_commit_blob_does_not_orphan_the_file(app_env, tmp_path: Path, monkeypatch):
    import hashlib

    client, conn, case_id = app_env
    data = _synthetic_pdf_bytes(tmp_path)
    sha = hashlib.sha256(data).hexdigest()
    blob_path = config.DATA_DIR / "blobs" / sha[:2] / sha

    def boom(*args, **kwargs):
        raise RuntimeError("injected failure -- F13a fault injection")

    monkeypatch.setattr(audit_mod, "append_event", boom)

    with pytest.raises(RuntimeError, match="injected failure"):
        client.post(
            f"/api/cases/{case_id}/documents",
            data={"doc_role": "application_form"},
            files={"file": ("orphan-repro.pdf", data, "application/pdf")},
        )

    # The ROLLBACK undid the SQL rows...
    assert conn.execute("SELECT COUNT(*) AS n FROM documents;").fetchone()["n"] == 0
    assert conn.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"] == 0
    # ...and the fix's compensating cleanup means the file blobs.commit_blob()
    # had already moved into place is ALSO gone -- not an orphan.
    assert not blob_path.exists(), (
        f"{blob_path} still exists with no `blobs` row pointing at it -- F13a regression"
    )
    tmp_dir = config.DATA_DIR / "tmp"
    assert not any(tmp_dir.glob("upload.tmp-*"))


def test_commit_blob_itself_self_heals_on_a_non_dedup_insert_failure(app_env, tmp_path: Path):
    """The narrower unit-level repro: forces the failure INSIDE
    blobs.commit_blob()'s own INSERT (not a later statement in the caller's
    transaction) -- a genuine, easily-reachable non-dedup IntegrityError (an
    actor_user_id that fails the `blobs.actor_user_id REFERENCES users(id)`
    foreign key, PRAGMA foreign_keys=ON per CONTRACT.md §3.1) -- proving
    that half of F13a independently of app/routes/documents.py's own
    compensating cleanup for the OUTER-transaction-failure case above.
    """
    import hashlib

    from app import blobs as blobs_module

    data = _synthetic_pdf_bytes(tmp_path)
    sha = hashlib.sha256(data).hexdigest()
    blob_path = config.DATA_DIR / "blobs" / sha[:2] / sha

    conn = db.connect(config.DATA_DIR / "permit-review.db")
    try:
        tmp_upload_path = config.DATA_DIR / "tmp" / "fault-injection-upload"
        tmp_upload_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_upload_path.write_bytes(data)
        streamed = blobs_module.StreamedUpload(
            tmp_path=tmp_upload_path, sha256=sha, byte_size=len(data),
            media_type="application/pdf", original_name="fault.pdf",
        )

        with pytest.raises(sqlite3.IntegrityError):
            blobs_module.commit_blob(conn, streamed, actor_user_id="no-such-user-id")

        assert conn.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"] == 0
        assert not blob_path.exists(), (
            f"{blob_path} was left behind by commit_blob() itself after a non-dedup INSERT failure"
        )
        assert not tmp_upload_path.exists()  # os.replace() already consumed it
    finally:
        conn.close()
