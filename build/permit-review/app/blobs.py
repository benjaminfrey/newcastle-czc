"""Content-addressed blob storage. Implements the `blobs` table contract
documented in app/migrations/0001_init.sql (CONTRACT.md §3.6): "content-
addressed bytes ... Stored at APP/data/blobs/<sha256[0:2]>/<sha256>.
Deduplicated by sha256. Bytes are never mutated; a corrected upload is a
new blob."

This module owns ONLY the bytes-to-disk + `blobs` row concern:

    1. stream()      — consume an upload in fixed-size chunks, NEVER
                        buffering the whole payload in memory, hashing and
                        size-checking as it goes, into a temp file under
                        data/tmp/. Raises before/while writing on an
                        unsupported content type, an oversized payload, or
                        an unsafe original filename -- nothing lands in
                        data/blobs/ until the caller has separately
                        validated the file is usable (CONTRACT.md §1.1 S1:
                        "validate-all-then-write").
    2. commit_blob()  — given an already-streamed, already-hashed temp
                        file, either dedup onto an existing `blobs` row
                        (deleting the temp file) or move it into its final
                        content-addressed location and INSERT the row.
                        Takes no transaction of its own (same convention as
                        app/audit.py:append_event) -- the caller wraps this
                        in the same BEGIN/COMMIT as the `documents`/`pages`
                        rows it accompanies.

app/routes/documents.py composes this with app/db.py + app/audit.py + a
`doc_role`/case_id to record an actual upload; this module knows nothing
about cases, documents, or doc roles.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app import config

# Paths are resolved from app.config.DATA_DIR at CALL time (config.DATA_DIR,
# not a `from ... import DATA_DIR` name-bound copy) so a test can
# monkeypatch app.config.DATA_DIR to a throwaway tmp_path and have every
# blob write in that test land there instead of the real APP/data/ tree --
# the same "throwaway temp-dir per test" discipline every other test file
# in this repo already follows (app/db.py's own tests connect straight to a
# tmp_path DB). config.BLOBS_DIR itself is NOT used here for the same
# reason: it was computed once at app.config's own import time and would go
# stale under a DATA_DIR monkeypatch.

# Stream in 1 MiB chunks -- large enough to be efficient, small enough that
# a 56-page PDF (the largest real file this app currently exercises against)
# never sits in memory as a single buffer.
CHUNK_SIZE = 1024 * 1024

# v1 allow-list. CONTRACT.md's ingest task brief: "an allow-list of content
# types (PDF first)". Deliberately a closed frozenset, not a default-allow
# list -- widening it is a one-line, deliberate change, never an accident.
ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset({"application/pdf"})

# A generous per-file cap (~150 MB): big enough for a heavily-scanned 50+
# page plan set at 300dpi (the real Stantec file is 56 pages and nowhere
# near this), small enough that a runaway or duplicate upload can't quietly
# fill the disk. Not a CONTRACT.md-numbered rule -- a plain safety default
# for a local, single-operator app; change here if a real submission needs
# more.
MAX_UPLOAD_BYTES = 150 * 1024 * 1024

PDF_MAGIC = b"%PDF-"


class UploadTooLarge(ValueError):
    def __init__(self, limit: int):
        super().__init__(f"upload exceeds the {limit}-byte cap")
        self.limit = limit


class UnsupportedMediaType(ValueError):
    """Declared content type is not in the allow-list, or (when sniffed)
    the bytes don't match the declared type."""


class UnsafeFilename(ValueError):
    """A filename that looks like a path-traversal attempt. The
    original_name is never used to build a filesystem path -- blobs are
    stored purely by sha256 -- but a name that LOOKS like an attempt is
    still rejected outright, per this workflow's task brief."""


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def sanitize_original_name(name: str | None) -> str | None:
    """Reject a filename containing a path separator, a NUL byte, or a
    bare '.'/'..' component. Returns a trimmed bare name (never a path) on
    success, or None if no name was supplied at all.
    """
    if name is None:
        return None
    name = name.strip()
    if not name:
        return None
    if "\x00" in name:
        raise UnsafeFilename(f"filename contains a NUL byte: {name!r}")
    if "/" in name or "\\" in name:
        raise UnsafeFilename(f"filename must not contain a path separator: {name!r}")
    if name in (".", ".."):
        raise UnsafeFilename(f"filename must not be '.' or '..': {name!r}")
    if Path(name).name != name:
        raise UnsafeFilename(f"filename is not a bare name: {name!r}")
    return name


@dataclass(frozen=True)
class StreamedUpload:
    """The result of stream()-ing a payload to a temp file: already fully
    written to disk, already hashed, not yet in its final content-addressed
    location and not yet recorded in `blobs` -- see commit_blob().
    """

    tmp_path: Path
    sha256: str
    byte_size: int
    media_type: str
    original_name: str | None


class _Sink:
    """Internal, synchronous accumulator: feed() is called once per chunk
    (from either a sync or an async source -- see stream()/consume_upload_file
    below), writing straight to disk and updating the running hash/size. No
    chunk's bytes are retained after feed() returns.
    """

    def __init__(
        self,
        *,
        media_type: str,
        original_name: str | None,
        max_bytes: int,
        allowed_content_types: frozenset[str],
        sniff_magic: bool,
    ) -> None:
        if media_type not in allowed_content_types:
            raise UnsupportedMediaType(
                f"content type {media_type!r} is not allowed; allowed: {sorted(allowed_content_types)}"
            )
        self._safe_name = sanitize_original_name(original_name)
        self._media_type = media_type
        self._max_bytes = max_bytes
        self._sniff_magic = sniff_magic
        self._hasher = hashlib.sha256()
        self._size = 0
        self._first_chunk_seen = False

        tmp_dir = config.DATA_DIR / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        self._tmp_path = tmp_dir / f"upload.tmp-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self._fh = self._tmp_path.open("wb")
        self._finished = False

    def feed(self, chunk: bytes) -> None:
        if not chunk:
            return
        if not self._first_chunk_seen:
            self._first_chunk_seen = True
            if self._sniff_magic and self._media_type == "application/pdf" and not chunk.startswith(PDF_MAGIC):
                self.abort()
                raise UnsupportedMediaType(
                    "upload declared application/pdf but its bytes do not start with the PDF magic number"
                )
        self._size += len(chunk)
        if self._size > self._max_bytes:
            self.abort()
            raise UploadTooLarge(self._max_bytes)
        self._hasher.update(chunk)
        self._fh.write(chunk)

    def abort(self) -> None:
        if not self._fh.closed:
            self._fh.close()
        self._tmp_path.unlink(missing_ok=True)

    def finish(self) -> StreamedUpload:
        if self._finished:
            raise RuntimeError("_Sink.finish() called twice")
        self._finished = True
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._fh.close()
        return StreamedUpload(
            tmp_path=self._tmp_path,
            sha256=self._hasher.hexdigest(),
            byte_size=self._size,
            media_type=self._media_type,
            original_name=self._safe_name,
        )


def stream(
    chunks,
    *,
    media_type: str,
    original_name: str | None,
    max_bytes: int = MAX_UPLOAD_BYTES,
    allowed_content_types: frozenset[str] = ALLOWED_CONTENT_TYPES,
    sniff_magic: bool = True,
) -> StreamedUpload:
    """Synchronous entry point: `chunks` is any iterable of bytes (a
    generator reading a file in fixed-size pieces, a list of bytes objects
    in a test, ...). Never holds more than one chunk in memory.
    """
    sink = _Sink(
        media_type=media_type,
        original_name=original_name,
        max_bytes=max_bytes,
        allowed_content_types=allowed_content_types,
        sniff_magic=sniff_magic,
    )
    try:
        for chunk in chunks:
            sink.feed(chunk)
    except (UploadTooLarge, UnsupportedMediaType):
        raise
    except Exception:
        sink.abort()
        raise
    return sink.finish()


async def consume_upload_file(
    file,
    *,
    media_type: str | None = None,
    original_name: str | None = None,
    max_bytes: int = MAX_UPLOAD_BYTES,
    allowed_content_types: frozenset[str] = ALLOWED_CONTENT_TYPES,
    sniff_magic: bool = True,
    chunk_size: int = CHUNK_SIZE,
) -> StreamedUpload:
    """Async entry point for a FastAPI `UploadFile` (or anything with an
    async `.read(n)` and `.content_type`/`.filename`). Reads in fixed-size
    chunks via `await file.read(chunk_size)` -- the payload is STREAMED
    straight to disk; at no point does this function hold the whole file
    in memory (CONTRACT.md ingest task brief: "STREAMED to disk (never
    buffer a 56-page PDF in memory)").
    """
    resolved_media_type = media_type if media_type is not None else (getattr(file, "content_type", None) or "")
    resolved_name = original_name if original_name is not None else getattr(file, "filename", None)

    sink = _Sink(
        media_type=resolved_media_type,
        original_name=resolved_name,
        max_bytes=max_bytes,
        allowed_content_types=allowed_content_types,
        sniff_magic=sniff_magic,
    )
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            sink.feed(chunk)
    except (UploadTooLarge, UnsupportedMediaType):
        raise
    except Exception:
        sink.abort()
        raise
    return sink.finish()


def discard(streamed: StreamedUpload) -> None:
    """Delete a StreamedUpload's temp file without committing it -- used on
    any validation failure discovered AFTER stream()/consume_upload_file()
    succeeded (e.g. triage finds the PDF unopenable) so that, per
    CONTRACT.md §1.1 S1, nothing from a rejected upload reaches
    data/blobs/. Safe to call more than once or on an already-committed
    StreamedUpload (a no-op if the temp file is already gone).
    """
    streamed.tmp_path.unlink(missing_ok=True)


def _blob_target_path(sha256: str) -> Path:
    """Where a blob's bytes live once committed: data/blobs/<sha[0:2]>/<sha>
    (CONTRACT.md §3.6). A pure function of the hash alone, resolved from
    config.DATA_DIR at CALL time (see the module-level note above) -- both
    commit_blob() and discard_committed_file() below go through this one
    place so the path is computed identically everywhere.
    """
    return config.DATA_DIR / "blobs" / sha256[:2] / sha256


def discard_committed_file(sha256: str) -> None:
    """F13a's compensating half of commit_blob()'s file move, for a caller
    whose OWN transaction -- the one commit_blob() participated in -- later
    fails for an unrelated reason (e.g. the `documents`/`pages` INSERTs
    after it). A SQL ROLLBACK undoes the `blobs` row commit_blob() inserted,
    but cannot undo the os.replace() that already happened; without this,
    that failure permanently orphans a file in data/blobs/ with no row
    anywhere pointing at it, contradicting this app's own claim (see
    app/routes/documents.py's module docstring) that a validation/write
    failure leaves data/blobs/ exactly as it was.

    ONLY call this for a blob commit_blob() reported as newly-created
    (`was_new=True`) in the SAME still-open transaction that is about to be
    rolled back -- SQLite is single-writer, so nothing else in this app can
    have depended on that uncommitted row (see commit_blob()'s own docstring
    for the narrow cross-process race this still cannot fully rule out).
    Best-effort: a no-op if the file is already gone.
    """
    _blob_target_path(sha256).unlink(missing_ok=True)


def commit_blob(
    conn: sqlite3.Connection,
    streamed: StreamedUpload,
    *,
    actor_user_id: str | None,
) -> tuple[dict, bool]:
    """Turn an already-streamed, already-hashed temp file into a permanent,
    content-addressed blob: dedup onto an existing row when the sha256
    already exists (CONTRACT.md ingest task brief: "re-uploading identical
    bytes must reuse the blob and not duplicate it"), otherwise move the
    temp file into data/blobs/<ab>/<sha256> and INSERT the row.

    Returns (blob_row_as_dict, was_new). Opens no transaction of its own --
    call inside the same transaction as the `documents`/`pages` rows this
    upload produces (same convention as app/audit.py:append_event). If
    `was_new` is True, the CALLER is responsible for calling
    discard_committed_file(sha256) should anything LATER in that same
    transaction fail (F13a) -- this function can only guarantee consistency
    for failures inside itself; see app/routes/documents.py for the other
    half.

    F13a: an os.replace() (the file move below) cannot be undone by a SQL
    ROLLBACK, so if the subsequent INSERT fails for any reason OTHER than
    the expected dedup race, the just-moved file is removed again before
    the exception propagates -- this function never returns normally, and
    never leaves a caller mid-transaction, with a file on disk that has no
    accompanying row (previously: "no naturally reachable trigger found" in
    the adversarial review that raised this -- reachable via, e.g., a locked
    database or an actor_user_id FK violation on this exact INSERT).
    """
    existing = conn.execute("SELECT * FROM blobs WHERE sha256 = ?;", (streamed.sha256,)).fetchone()
    if existing is not None:
        streamed.tmp_path.unlink(missing_ok=True)
        return dict(existing), False

    rel_path = f"data/blobs/{streamed.sha256[:2]}/{streamed.sha256}"
    target = _blob_target_path(streamed.sha256)
    target.parent.mkdir(parents=True, exist_ok=True)

    # Atomic within the blobs directory: the temp file already lives on the
    # same filesystem (data/tmp/ and data/blobs/ share APP_ROOT/data), so
    # os.replace() is a single rename, never a partial copy.
    os.replace(streamed.tmp_path, target)

    blob_id = uuid.uuid4().hex
    created_at = _utc_now_iso()
    try:
        conn.execute(
            """
            INSERT INTO blobs (id, sha256, byte_size, media_type, original_name, rel_path, created_at, actor_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (blob_id, streamed.sha256, streamed.byte_size, streamed.media_type,
             streamed.original_name, rel_path, created_at, actor_user_id),
        )
    except sqlite3.IntegrityError:
        # Lost a race with a concurrent identical upload: the bytes at
        # `target` are byte-identical either way (same sha256), so the
        # overwrite above was harmless -- just adopt the row that won.
        existing = conn.execute("SELECT * FROM blobs WHERE sha256 = ?;", (streamed.sha256,)).fetchone()
        if existing is None:
            # Not actually the dedup race (some OTHER integrity failure on
            # this exact INSERT) -- the file we just wrote corresponds to no
            # row at all now. Self-heal before propagating (F13a).
            target.unlink(missing_ok=True)
            raise
        return dict(existing), False
    except Exception:
        # Anything else that fails this INSERT (locked database, disk full,
        # ...) -- same rule: never leave an unreferenced file behind.
        target.unlink(missing_ok=True)
        raise

    row = conn.execute("SELECT * FROM blobs WHERE id = ?;", (blob_id,)).fetchone()
    return dict(row), True
