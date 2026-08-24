"""Tests app/db.py against CONTRACT.md §3.1 and §1.1 S6 checks 1-2.

Offline, no network, no LLM, no PII — a throwaway temp-dir SQLite file per
test via the `db_path` fixture.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"

# Computed from the real migrations/ directory rather than hardcoded: the
# invariant this suite cares about is "every file in migrations/ applies, in
# lexical order, on a fresh DB" -- not "there is exactly one migration file
# forever". app/db.py's own docstring states the project's migration
# philosophy explicitly: a schema change is a NEW numbered file, never an
# edit to one that already shipped (0001_init.sql, then 0002_case_tracking.sql,
# then 0003_case_lifecycle.sql, ...). Deriving the expectation here means this
# file does not need a one-line edit every time a later workflow adds one.
EXPECTED_MIGRATIONS = sorted(p.name for p in MIGRATIONS_DIR.glob("*.sql"))

EXPECTED_TABLES = {
    "schema_migrations",
    "users",
    "board_members",
    "rulesets",
    "cases",
    "case_reviews",
    "blobs",
    "documents",
    "pages",
    "field_defs",
    "field_candidates",
    "field_values",
    "rules",
    "criteria_sets",
    "criteria_set_rules",
    "findings_nodes",
    "conditions",
    "motions",
    "decisions",
    "conflict_disclosures",
    "attendance",
    "deadlines",
    "events",
    "generated_documents",
    "jobs",
}


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "permit-review.db"


def test_connect_sets_and_asserts_pragmas(db_path: Path) -> None:
    conn = db.connect(db_path)
    try:
        assert conn.execute("PRAGMA foreign_keys;").fetchone()[0] == 1
        assert str(conn.execute("PRAGMA journal_mode;").fetchone()[0]).lower() == "wal"
        assert conn.execute("PRAGMA busy_timeout;").fetchone()[0] == 5000
        assert conn.execute("PRAGMA synchronous;").fetchone()[0] == 2  # FULL == 2 in SQLite
    finally:
        conn.close()


def test_migrate_creates_all_24_tables_plus_bookkeeping(db_path: Path) -> None:
    # 23 + `attendance` (0017_meeting_attendance.sql, W7's "meeting model").
    conn = db.connect(db_path)
    try:
        applied = db.migrate(conn, MIGRATIONS_DIR)
        assert applied == EXPECTED_MIGRATIONS

        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table';"
        ).fetchall()
        table_names = {r["name"] for r in rows} - {"sqlite_sequence"}
        assert EXPECTED_TABLES <= table_names
    finally:
        conn.close()


def test_migrate_is_idempotent_on_a_second_run(db_path: Path) -> None:
    conn = db.connect(db_path)
    try:
        first = db.migrate(conn, MIGRATIONS_DIR)
        assert first == EXPECTED_MIGRATIONS

        second = db.migrate(conn, MIGRATIONS_DIR)
        assert second == []

        rows = conn.execute("SELECT COUNT(*) AS n FROM schema_migrations;").fetchone()
        assert rows["n"] == len(EXPECTED_MIGRATIONS)
    finally:
        conn.close()


def test_migrate_is_idempotent_across_fresh_connections(db_path: Path) -> None:
    """Re-running migrate() against the same on-disk DB from a brand new
    connection (simulating a process restart) applies nothing new."""
    conn1 = db.connect(db_path)
    try:
        db.migrate(conn1, MIGRATIONS_DIR)
    finally:
        conn1.close()

    conn2 = db.connect(db_path)
    try:
        applied = db.migrate(conn2, MIGRATIONS_DIR)
        assert applied == []
    finally:
        conn2.close()


def test_migrate_records_sha256_and_applied_at(db_path: Path) -> None:
    conn = db.connect(db_path)
    try:
        db.migrate(conn, MIGRATIONS_DIR)
        row = conn.execute(
            "SELECT name, applied_at, sha256 FROM schema_migrations WHERE name = ?;",
            ("0001_init.sql",),
        ).fetchone()
        assert row is not None
        assert row["applied_at"].endswith("Z")
        assert len(row["sha256"]) == 64
        expected = db._sha256_file(MIGRATIONS_DIR / "0001_init.sql")
        assert row["sha256"] == expected
    finally:
        conn.close()


def test_migrate_raises_if_migrations_dir_is_empty(tmp_path: Path, db_path: Path) -> None:
    empty_dir = tmp_path / "empty-migrations"
    empty_dir.mkdir()

    conn = db.connect(db_path)
    try:
        with pytest.raises(db.MigrationError):
            db.migrate(conn, empty_dir)
    finally:
        conn.close()


def test_migrate_raises_if_an_applied_migration_file_changed_on_disk(
    tmp_path: Path, db_path: Path
) -> None:
    work_dir = tmp_path / "migrations"
    work_dir.mkdir()
    mfile = work_dir / "0001_init.sql"
    mfile.write_text("CREATE TABLE t (id TEXT PRIMARY KEY);\n", encoding="utf-8")

    conn = db.connect(db_path)
    try:
        applied = db.migrate(conn, work_dir)
        assert applied == ["0001_init.sql"]

        # Mutate the file after it shipped.
        mfile.write_text("CREATE TABLE t (id TEXT PRIMARY KEY, extra TEXT);\n", encoding="utf-8")

        with pytest.raises(db.MigrationError):
            db.migrate(conn, work_dir)
    finally:
        conn.close()


def test_migrate_is_atomic_on_a_failing_migration(tmp_path: Path, db_path: Path) -> None:
    """A migration file whose later statement fails must leave NEITHER its
    earlier statements' effects NOR a schema_migrations row behind."""
    work_dir = tmp_path / "migrations"
    work_dir.mkdir()
    (work_dir / "0001_ok.sql").write_text(
        "CREATE TABLE ok_table (id TEXT PRIMARY KEY);\n", encoding="utf-8"
    )
    (work_dir / "0002_broken.sql").write_text(
        "CREATE TABLE partial_table (id TEXT PRIMARY KEY);\n"
        "THIS IS NOT VALID SQL;\n",
        encoding="utf-8",
    )

    conn = db.connect(db_path)
    try:
        # Both files are picked up by the same migrate() call (lexical glob
        # order): 0001 commits successfully, then 0002 fails mid-script and
        # the whole call raises from there.
        with pytest.raises(sqlite3.OperationalError):
            db.migrate(conn, work_dir)

        # The good migration's table exists and was recorded...
        tables = {
            r["name"]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        }
        assert "ok_table" in tables
        recorded = {
            r["name"] for r in conn.execute("SELECT name FROM schema_migrations;").fetchall()
        }
        assert "0001_ok.sql" in recorded

        # ...but the broken migration's partial DDL was rolled back...
        assert "partial_table" not in tables
        # ...and it was never recorded as applied.
        assert "0002_broken.sql" not in recorded

        # A subsequent call only needs to (fail to) apply the broken one again.
        with pytest.raises(sqlite3.OperationalError):
            db.migrate(conn, work_dir)
    finally:
        conn.close()
