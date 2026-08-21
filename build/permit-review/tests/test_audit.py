"""Tests app/audit.py against CONTRACT.md §3.3.

Offline, no network, no LLM, no PII — a throwaway temp-dir SQLite file per
test via the `conn` fixture (migrated + given the synthetic actor row).
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import audit, db, security  # noqa: E402

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "app" / "migrations"

GENESIS_HASH = "0" * 64


@pytest.fixture()
def conn(tmp_path: Path):
    c = db.connect(tmp_path / "permit-review.db")
    db.migrate(c, MIGRATIONS_DIR)
    security.ensure_synthetic_user(c)
    try:
        yield c
    finally:
        c.close()


# ---------------------------------------------------------------------------
# append_event / verify_chain — the happy path
# ---------------------------------------------------------------------------


def test_verify_chain_on_empty_events_is_true(conn: sqlite3.Connection) -> None:
    assert audit.verify_chain(conn) == (True, None)


def test_first_event_chains_from_genesis_hash(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn,
        actor_user_id=security.SYNTHETIC_USER_ID,
        kind="case.created",
        payload={"label": "M003, L059"},
    )
    row = conn.execute("SELECT prev_hash FROM events ORDER BY seq ASC LIMIT 1;").fetchone()
    assert row["prev_hash"] == GENESIS_HASH


def test_three_event_chain_verifies(conn: sqlite3.Connection) -> None:
    for i in range(3):
        audit.append_event(
            conn,
            actor_user_id=security.SYNTHETIC_USER_ID,
            kind=f"test.event.{i}",
            payload={"i": i},
        )
    ok, bad_seq = audit.verify_chain(conn)
    assert ok is True
    assert bad_seq is None

    rows = conn.execute("SELECT seq, prev_hash, hash FROM events ORDER BY seq ASC;").fetchall()
    assert len(rows) == 3
    assert rows[0]["prev_hash"] == GENESIS_HASH
    for prev, cur in zip(rows, rows[1:]):
        assert cur["prev_hash"] == prev["hash"]


def test_null_actor_hashes_as_literal_system(conn: sqlite3.Connection) -> None:
    event_id = audit.append_event(
        conn, actor_user_id=None, kind="system.startup", payload={}
    )
    row = conn.execute(
        "SELECT actor_user_id, at, kind, payload_json, prev_hash, hash FROM events WHERE id = ?;",
        (event_id,),
    ).fetchone()
    assert row["actor_user_id"] is None

    expected = audit._compute_hash(
        row["prev_hash"], event_id, row["at"], "system", row["kind"], row["payload_json"]
    )
    assert row["hash"] == expected

    ok, bad_seq = audit.verify_chain(conn)
    assert ok is True
    assert bad_seq is None


def test_payload_json_is_reproducibly_serialized(conn: sqlite3.Connection) -> None:
    event_id = audit.append_event(
        conn,
        actor_user_id=security.SYNTHETIC_USER_ID,
        kind="test.serialization",
        payload={"b": 2, "a": 1, "nested": {"z": True, "y": None}},
    )
    row = conn.execute("SELECT payload_json FROM events WHERE id = ?;", (event_id,)).fetchone()
    assert row["payload_json"] == json.dumps(
        {"b": 2, "a": 1, "nested": {"z": True, "y": None}},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    # sorted keys, no spaces after ':' or ','
    assert row["payload_json"] == '{"a":1,"b":2,"nested":{"y":null,"z":true}}'


def test_case_and_entity_columns_round_trip(conn: sqlite3.Connection) -> None:
    event_id = audit.append_event(
        conn,
        actor_user_id=security.SYNTHETIC_USER_ID,
        kind="field_value.overridden",
        payload={"reason": "plan governs over form"},
        case_id=None,
        entity_table="field_values",
        entity_id="fv-123",
    )
    row = conn.execute(
        "SELECT entity_table, entity_id, case_id FROM events WHERE id = ?;", (event_id,)
    ).fetchone()
    assert row["entity_table"] == "field_values"
    assert row["entity_id"] == "fv-123"
    assert row["case_id"] is None


# ---------------------------------------------------------------------------
# append-only enforcement — the triggers
# ---------------------------------------------------------------------------


def test_events_update_trigger_aborts(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="test.event", payload={}
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("UPDATE events SET kind = 'tampered' WHERE seq = 1;")


def test_events_delete_trigger_aborts(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="test.event", payload={}
    )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        conn.execute("DELETE FROM events WHERE seq = 1;")


def test_rejected_update_leaves_the_row_and_chain_intact(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="test.event", payload={"n": 1}
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE events SET payload_json = '{\"n\":999}' WHERE seq = 1;")

    row = conn.execute("SELECT payload_json FROM events WHERE seq = 1;").fetchone()
    assert row["payload_json"] == '{"n":1}'
    assert audit.verify_chain(conn) == (True, None)


# ---------------------------------------------------------------------------
# tamper detection — the hash chain itself, independent of the triggers.
#
# The triggers above prove SQL-level mutation is blocked. These tests prove
# the second, independent layer: if a row's stored bytes were EVER changed
# by any means (e.g. direct file/bytes editing outside SQLite, or a future
# schema without the guard triggers), verify_chain() catches it. We drop the
# guard triggers ourselves to reach that state in-process, since there is no
# other way to write to `events` at all once they are in place.
# ---------------------------------------------------------------------------


def _drop_events_guard_triggers(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TRIGGER trg_events_no_update;")
    conn.execute("DROP TRIGGER trg_events_no_delete;")


def test_tampering_with_a_payload_breaks_verification(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.one", payload={"amount": 100}
    )
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.two", payload={"amount": 200}
    )
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.three", payload={"amount": 300}
    )
    assert audit.verify_chain(conn) == (True, None)

    _drop_events_guard_triggers(conn)
    conn.execute(
        "UPDATE events SET payload_json = '{\"amount\":999999}' WHERE seq = 2;"
    )

    ok, bad_seq = audit.verify_chain(conn)
    assert ok is False
    assert bad_seq == 2


def test_tampering_with_the_hash_itself_breaks_verification(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.one", payload={}
    )
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.two", payload={}
    )

    _drop_events_guard_triggers(conn)
    bogus_hash = ("deadbeef" * 8)[:64]
    row1 = conn.execute("SELECT hash FROM events WHERE seq = 1;").fetchone()
    assert row1["hash"] != bogus_hash  # guard against a freak real collision
    conn.execute("UPDATE events SET hash = ? WHERE seq = 1;", (bogus_hash,))

    ok, bad_seq = audit.verify_chain(conn)
    assert ok is False
    # row 1's own hash no longer matches its recomputation...
    assert bad_seq == 1


def test_tampering_with_prev_hash_link_breaks_verification(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.one", payload={}
    )
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.two", payload={}
    )

    _drop_events_guard_triggers(conn)
    conn.execute("UPDATE events SET prev_hash = ? WHERE seq = 2;", ("a" * 64,))

    ok, bad_seq = audit.verify_chain(conn)
    assert ok is False
    assert bad_seq == 2


def test_deleting_a_middle_event_breaks_verification(conn: sqlite3.Connection) -> None:
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.one", payload={}
    )
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.two", payload={}
    )
    audit.append_event(
        conn, actor_user_id=security.SYNTHETIC_USER_ID, kind="event.three", payload={}
    )

    _drop_events_guard_triggers(conn)
    conn.execute("DELETE FROM events WHERE seq = 2;")

    ok, bad_seq = audit.verify_chain(conn)
    assert ok is False
    assert bad_seq == 3  # seq 3's prev_hash now points at a hash that isn't seq 1's
