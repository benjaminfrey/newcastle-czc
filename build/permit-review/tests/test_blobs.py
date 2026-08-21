"""Tests for app/blobs.py — streamed, content-addressed blob storage.

Offline, no network. A throwaway temp-dir SQLite file + a monkeypatched
app.config.DATA_DIR per test, matching this repo's established "throwaway
temp-dir per test" convention (see tests/test_audit.py).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from app import blobs, config, db, security  # noqa: E402

MIGRATIONS_DIR = APP_ROOT / "app" / "migrations"

PDF_BYTES = b"%PDF-1.4\n%mock pdf content for blob tests\n" + b"x" * 4096


class _FakeUploadFile:
    """Minimal async stand-in for fastapi.UploadFile: async .read(n),
    .content_type, .filename -- exactly what consume_upload_file() uses."""

    def __init__(self, data: bytes, *, content_type: str, filename: str | None):
        self._data = data
        self._pos = 0
        self.content_type = content_type
        self.filename = filename

    async def read(self, n: int) -> bytes:
        chunk = self._data[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    conn = db.connect(tmp_path / "permit-review.db")
    db.migrate(conn, MIGRATIONS_DIR)
    security.ensure_synthetic_user(conn)
    try:
        yield conn
    finally:
        conn.close()


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# sanitize_original_name — path-traversal rejection.
# --------------------------------------------------------------------------- #


def test_sanitize_original_name_accepts_a_bare_filename():
    assert blobs.sanitize_original_name("application.pdf") == "application.pdf"


def test_sanitize_original_name_returns_none_for_none_or_empty():
    assert blobs.sanitize_original_name(None) is None
    assert blobs.sanitize_original_name("   ") is None


@pytest.mark.parametrize(
    "bad",
    [
        "../../etc/passwd",
        "..\\..\\windows\\system32",
        "foo/bar.pdf",
        "foo\\bar.pdf",
        "..",
        ".",
        "/etc/passwd",
    ],
)
def test_sanitize_original_name_rejects_traversal_attempts(bad: str):
    with pytest.raises(blobs.UnsafeFilename):
        blobs.sanitize_original_name(bad)


def test_sanitize_original_name_rejects_nul_byte():
    with pytest.raises(blobs.UnsafeFilename):
        blobs.sanitize_original_name("application.pdf\x00.exe")


# --------------------------------------------------------------------------- #
# stream() / consume_upload_file() — content-type allow-list, size cap,
# streaming (never buffering the whole payload).
# --------------------------------------------------------------------------- #


def test_stream_rejects_unsupported_content_type():
    with pytest.raises(blobs.UnsupportedMediaType):
        blobs.stream([b"hello"], media_type="image/png", original_name="x.png")


def test_stream_rejects_pdf_content_type_with_non_pdf_bytes():
    with pytest.raises(blobs.UnsupportedMediaType):
        blobs.stream([b"not a pdf at all"], media_type="application/pdf", original_name="x.pdf")


def test_stream_accepts_pdf_bytes_and_hashes_correctly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    import hashlib

    result = blobs.stream(
        [PDF_BYTES[:10], PDF_BYTES[10:]],  # multiple chunks
        media_type="application/pdf",
        original_name="application.pdf",
    )
    assert result.sha256 == hashlib.sha256(PDF_BYTES).hexdigest()
    assert result.byte_size == len(PDF_BYTES)
    assert result.tmp_path.exists()
    assert result.tmp_path.read_bytes() == PDF_BYTES


def test_stream_enforces_the_size_cap_mid_stream(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)

    def chunks():
        yield b"%PDF-1.4\n"
        yield b"a" * 1000

    with pytest.raises(blobs.UploadTooLarge):
        blobs.stream(chunks(), media_type="application/pdf", original_name="big.pdf", max_bytes=500)

    # Nothing left behind in data/tmp/ after an aborted upload.
    tmp_dir = tmp_path / "tmp"
    assert not any(tmp_dir.glob("upload.tmp-*")) if tmp_dir.exists() else True


def test_consume_upload_file_streams_without_holding_more_than_one_chunk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    file = _FakeUploadFile(PDF_BYTES, content_type="application/pdf", filename="application.pdf")
    result = _run(blobs.consume_upload_file(file, chunk_size=64))
    assert result.byte_size == len(PDF_BYTES)
    assert result.original_name == "application.pdf"


def test_consume_upload_file_rejects_traversal_filename(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    file = _FakeUploadFile(PDF_BYTES, content_type="application/pdf", filename="../../etc/passwd.pdf")
    with pytest.raises(blobs.UnsafeFilename):
        _run(blobs.consume_upload_file(file))


# --------------------------------------------------------------------------- #
# commit_blob() — content addressing + dedup.
# --------------------------------------------------------------------------- #


def test_commit_blob_writes_to_content_addressed_path(env, tmp_path: Path):
    streamed = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a.pdf")
    row, is_new = blobs.commit_blob(env, streamed, actor_user_id=None)
    assert is_new is True
    assert row["sha256"] == streamed.sha256
    assert row["rel_path"] == f"data/blobs/{streamed.sha256[:2]}/{streamed.sha256}"
    on_disk = tmp_path / "blobs" / streamed.sha256[:2] / streamed.sha256
    assert on_disk.exists()
    assert on_disk.read_bytes() == PDF_BYTES
    assert not streamed.tmp_path.exists()  # moved, not copied


def test_commit_blob_dedupes_identical_bytes(env, tmp_path: Path):
    s1 = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a.pdf")
    row1, new1 = blobs.commit_blob(env, s1, actor_user_id=None)

    s2 = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a-renamed-copy.pdf")
    row2, new2 = blobs.commit_blob(env, s2, actor_user_id=None)

    assert new1 is True
    assert new2 is False
    assert row1["id"] == row2["id"]
    assert not s2.tmp_path.exists()

    count = env.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"]
    assert count == 1


def test_commit_blob_different_bytes_produce_different_blobs(env):
    s1 = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a.pdf")
    s2 = blobs.stream([PDF_BYTES + b"more"], media_type="application/pdf", original_name="b.pdf")
    row1, _ = blobs.commit_blob(env, s1, actor_user_id=None)
    row2, _ = blobs.commit_blob(env, s2, actor_user_id=None)
    assert row1["id"] != row2["id"]
    count = env.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"]
    assert count == 2


def test_discard_removes_the_temp_file_without_committing(env):
    streamed = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a.pdf")
    assert streamed.tmp_path.exists()
    blobs.discard(streamed)
    assert not streamed.tmp_path.exists()
    count = env.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"]
    assert count == 0


# --------------------------------------------------------------------------- #
# F13a -- commit_blob() must never leave a file on disk with no `blobs` row
# pointing at it (a SQL ROLLBACK cannot undo the os.replace() that already
# happened), and discard_committed_file() is the compensating half a caller
# uses when a LATER statement in its own transaction fails instead.
# --------------------------------------------------------------------------- #


def test_discard_committed_file_removes_the_file_by_sha_alone(env, tmp_path: Path):
    streamed = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a.pdf")
    row, is_new = blobs.commit_blob(env, streamed, actor_user_id=None)
    assert is_new is True
    on_disk = tmp_path / "blobs" / streamed.sha256[:2] / streamed.sha256
    assert on_disk.exists()

    blobs.discard_committed_file(streamed.sha256)
    assert not on_disk.exists()


def test_discard_committed_file_is_a_safe_no_op_when_nothing_is_there():
    blobs.discard_committed_file("0" * 64)  # never raises


def test_commit_blob_self_heals_when_the_insert_fails_for_a_reason_other_than_dedup(env, tmp_path: Path):
    """F13a's own repro: an os.replace() already happened (the file is on
    disk) when the subsequent INSERT INTO blobs fails for a genuine reason
    OTHER than the dedup race (here: actor_user_id fails the
    `blobs.actor_user_id REFERENCES users(id)` foreign key, PRAGMA
    foreign_keys=ON per CONTRACT.md §3.1) -- before this fix, that file
    would be permanently orphaned; commit_blob() must remove it itself
    before propagating the error.
    """
    streamed = blobs.stream([PDF_BYTES], media_type="application/pdf", original_name="a.pdf")
    target = tmp_path / "blobs" / streamed.sha256[:2] / streamed.sha256

    with pytest.raises(Exception):  # sqlite3.IntegrityError
        blobs.commit_blob(env, streamed, actor_user_id="no-such-user-id")

    assert not target.exists(), "commit_blob() left an orphaned file after a non-dedup INSERT failure"
    assert env.execute("SELECT COUNT(*) AS n FROM blobs;").fetchone()["n"] == 0
