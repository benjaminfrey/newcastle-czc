"""Append-only, hash-chained audit log.

    hash = sha256( prev_hash || id || at || actor || kind || payload_json )

UTF-8, concatenated in that order with no separator; prev_hash of the first row
is GENESIS_HASH. Same formula as the Planning Board Review app
(build/permit-review/app/audit.py). Payloads carry ids, never personal details.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import Connection, text

GENESIS_HASH = "0" * 64
# Serialises appends so two transactions can never chain onto the same row.
_APPEND_LOCK = 7_041_955


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prev_hash: str, id_: str, at: str, actor: str, kind: str, payload_json: str) -> str:
    h = hashlib.sha256()
    for part in (prev_hash, id_, at, actor, kind, payload_json):
        h.update(part.encode("utf-8"))
    return h.hexdigest()


def append_event(conn: Connection, *, actor: str, kind: str, payload: dict) -> str:
    conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _APPEND_LOCK})
    prev = conn.execute(text("SELECT hash FROM event ORDER BY seq DESC LIMIT 1")).scalar()
    prev_hash = prev or GENESIS_HASH
    id_ = str(uuid.uuid4())
    at = datetime.now(UTC).isoformat(timespec="microseconds")
    payload_json = _canonical(payload)
    conn.execute(
        text(
            "INSERT INTO event (id, at, actor, kind, payload_json, prev_hash, hash) "
            "VALUES (:id, :at, :actor, :kind, :payload_json, :prev_hash, :hash)"
        ),
        {
            "id": id_, "at": at, "actor": actor, "kind": kind,
            "payload_json": payload_json, "prev_hash": prev_hash,
            "hash": _hash(prev_hash, id_, at, actor, kind, payload_json),
        },
    )
    return id_


def verify_chain(conn: Connection) -> tuple[bool, int | None]:
    expected_prev = GENESIS_HASH
    rows = conn.execute(text(
        "SELECT seq, id, at, actor, kind, payload_json, prev_hash, hash FROM event ORDER BY seq"
    ))
    for r in rows:
        recomputed = _hash(r.prev_hash, str(r.id), r.at, r.actor, r.kind, r.payload_json)
        if r.prev_hash != expected_prev or r.hash != recomputed:
            return False, r.seq
        expected_prev = r.hash
    return True, None
