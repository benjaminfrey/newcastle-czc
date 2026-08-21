"""Implements CONTRACT.md §3.3 (the audit chain).

events is append-only and hash-chained:

    hash = sha256( prev_hash || id || at || actor || kind || payload_json )

Concatenation is of the UTF-8 bytes of the exact stored strings, in that
order, with NO separator. prev_hash for the first row is "0" * 64. actor is
the stored actor_user_id, or the literal string "system" when it is NULL.
payload_json is hashed exactly as stored, and MUST be serialized with
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) so
the hash is reproducible byte-for-byte from the payload dict alone.

The events table's own BEFORE UPDATE / BEFORE DELETE triggers (0001_init.sql)
make tampering-by-mutation impossible; verify_chain() here is what catches
tampering-by-direct-write (bypassing this module, e.g. a hand SQL UPDATE that
somehow got past the trigger, or bytes edited outside SQLite entirely).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone

GENESIS_HASH = "0" * 64
SYSTEM_ACTOR = "system"


def _utc_now_iso() -> str:
    """ISO-8601 UTC, 'Z' suffix, millisecond precision — CONTRACT.md §3.3."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _payload_dumps(payload: dict) -> str:
    """CONTRACT.md §3.3: the exact, reproducible serialization the hash is
    computed over.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_hash(prev_hash: str, id_: str, at: str, actor: str, kind: str, payload_json: str) -> str:
    h = hashlib.sha256()
    for part in (prev_hash, id_, at, actor, kind, payload_json):
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def append_event(
    conn: sqlite3.Connection,
    *,
    actor_user_id: str | None,
    kind: str,
    payload: dict,
    case_id: str | None = None,
    entity_table: str | None = None,
    entity_id: str | None = None,
) -> str:
    """Append one row to the hash-chained, append-only events log and return
    its id.

    Opens no transaction of its own — call it inside the same transaction as
    the mutation it records (CONTRACT.md §3.3: "every mutation appends an
    events row in the same transaction"). On a connection in autocommit mode
    with no transaction currently open, this INSERT simply commits by
    itself, which is correct for a standalone event (e.g. in tests).
    """
    prev_row = conn.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1;").fetchone()
    prev_hash = prev_row["hash"] if prev_row is not None else GENESIS_HASH

    event_id = uuid.uuid4().hex
    at = _utc_now_iso()
    actor = actor_user_id if actor_user_id is not None else SYSTEM_ACTOR
    payload_json = _payload_dumps(payload)

    hash_ = _compute_hash(prev_hash, event_id, at, actor, kind, payload_json)

    conn.execute(
        """
        INSERT INTO events
            (id, at, actor_user_id, kind, case_id, entity_table, entity_id,
             payload_json, prev_hash, hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            event_id,
            at,
            actor_user_id,
            kind,
            case_id,
            entity_table,
            entity_id,
            payload_json,
            prev_hash,
            hash_,
        ),
    )
    return event_id


def verify_chain(conn: sqlite3.Connection) -> tuple[bool, int | None]:
    """Walk events by seq ascending, recomputing every hash from its stored
    fields and checking prev_hash links row-to-row (CONTRACT.md §3.3).

    Returns (True, None) if the whole chain verifies, including the empty
    chain. Otherwise returns (False, seq) naming the seq of the first row
    that fails — either because its prev_hash does not match the previous
    row's stored hash (or GENESIS_HASH, for the first row), or because its
    own stored hash does not match the recomputation over its stored fields
    (tampered payload_json, at, kind, or actor_user_id).
    """
    rows = conn.execute(
        """
        SELECT seq, id, at, actor_user_id, kind, payload_json, prev_hash, hash
        FROM events
        ORDER BY seq ASC;
        """
    ).fetchall()

    expected_prev = GENESIS_HASH
    for row in rows:
        if row["prev_hash"] != expected_prev:
            return False, row["seq"]

        actor = row["actor_user_id"] if row["actor_user_id"] is not None else SYSTEM_ACTOR
        recomputed = _compute_hash(
            row["prev_hash"], row["id"], row["at"], actor, row["kind"], row["payload_json"]
        )
        if recomputed != row["hash"]:
            return False, row["seq"]

        expected_prev = row["hash"]

    return True, None
