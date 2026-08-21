"""Implements CONTRACT.md §3.1 (connection pragmas) and the migration runner
described in §2 (app/migrations/, schema_migrations bookkeeping), §1.1 S6
check 1 (migrations apply to a throwaway temp DB and are idempotent on a
second run) and check 2 (PRAGMA values asserted after connect).

Raw SQL only. No ORM.
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MigrationError(RuntimeError):
    """Raised when a required PRAGMA did not take, no migration files are
    found, or an already-applied migration file's contents have drifted from
    what schema_migrations recorded (migrations must never be edited after
    they ship — a real change is a new numbered file).
    """


def _utc_now_iso() -> str:
    """ISO-8601 UTC, 'Z' suffix, millisecond precision — CONTRACT.md §3.3/§3.4
    timestamp format, reused here for schema_migrations.applied_at.
    """
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def connect(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with the CONTRACT.md §3.1 pragmas set and
    verified, in order:

        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA busy_timeout = 5000;
        PRAGMA synchronous = FULL;

    foreign_keys and journal_mode are read back and asserted; a mismatch
    raises MigrationError rather than running unsafe. isolation_level=None
    puts the connection in autocommit mode so transactions are explicit
    (BEGIN/COMMIT/ROLLBACK), matching the "raw SQL, no ORM" contract.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), isolation_level=None)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = FULL;")

    fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
    if fk != 1:
        conn.close()
        raise MigrationError(f"PRAGMA foreign_keys did not take (got {fk!r})")

    jm = conn.execute("PRAGMA journal_mode;").fetchone()[0]
    if str(jm).lower() != "wal":
        conn.close()
        raise MigrationError(f"PRAGMA journal_mode did not take (got {jm!r})")

    return conn


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def migrate(conn: sqlite3.Connection, migrations_dir: Path) -> list[str]:
    """Apply app/migrations/NNNN_*.sql files in lexical order, each inside
    its own transaction, recording each in schema_migrations. Re-running is a
    no-op for already-applied migrations (CONTRACT.md §1.1 S6 check 1, §3.1).

    Returns the list of migration filenames newly applied by this call
    (empty when the database was already fully up to date).

    Atomicity: a literal ``BEGIN;`` prefixed onto each migration's SQL opens
    a real SQLite transaction before its statements run. sqlite3.executescript
    only implicitly commits a transaction that was already pending *before*
    the call — it does not touch a transaction opened by the script text
    itself — so that transaction stays open across the executescript() call
    and the follow-up bookkeeping INSERT, and only the final explicit COMMIT
    below closes it. Any exception leaves the DDL and the schema_migrations
    row equally un-applied.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name        TEXT PRIMARY KEY,
            applied_at  TEXT NOT NULL,
            sha256      TEXT NOT NULL
        );
        """
    )

    applied: dict[str, str] = {
        row["name"]: row["sha256"]
        for row in conn.execute("SELECT name, sha256 FROM schema_migrations;").fetchall()
    }

    files = sorted(migrations_dir.glob("*.sql"))
    if not files:
        raise MigrationError(f"no migration files found in {migrations_dir}")

    newly_applied: list[str] = []
    for f in files:
        name = f.name
        digest = _sha256_file(f)

        if name in applied:
            if applied[name] != digest:
                raise MigrationError(
                    f"migration {name} has changed on disk since it was applied "
                    f"(recorded sha256 {applied[name]}, file now {digest}); "
                    "migrations must never be edited after they ship — add a new "
                    "numbered file instead"
                )
            continue

        sql = f.read_text(encoding="utf-8")
        try:
            conn.executescript(f"BEGIN;\n{sql}")
            conn.execute(
                "INSERT INTO schema_migrations (name, applied_at, sha256) VALUES (?, ?, ?);",
                (name, _utc_now_iso(), digest),
            )
            conn.execute("COMMIT;")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK;")
            raise

        newly_applied.append(name)

    return newly_applied
