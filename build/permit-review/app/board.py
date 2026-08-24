"""Seeds the Planning Board roster (`users` + `board_members`) so the W7
meeting workflow has real seats to choose a mover/second from.

WHY THIS EXISTS. No prior workflow ever wrote a `board_members` row outside
a test fixture (grep confirms: before this module, the only INSERTs against
either table anywhere in this repo were in tests/*.py). The meeting UI
cannot function with an empty roster -- there would be nobody to move or
second a motion, and conflict_disclosures' own roll call has nothing to
roll. This module is the minimal fix: an idempotent seed, run once at
startup (app/main.py's lifespan, right after security.ensure_synthetic_user
-- same pattern, same seam), never a durable "roster editor" UI (out of
scope for this session; a future workflow can build one against these same
two tables without any migration).

WHERE THE NAMES COME FROM. Not invented. They are the seven Planning Board
members who actually signed the real, adopted Findings of Fact & Conclusions
of Law for M003, L059 (White Road, Shattuck), 2025-12-18
(`docs/Findings of Fact and Conclusions of Law/`) -- a public record of a
public body's own meeting minutes, not personal data about a private
individual. Ben Frey signs first, as Chair (`board_members.is_chair = 1`);
BUILD-STATE.md's own D-0027 entry already establishes that Ben is this
project's Chair, author and operator, so seeding him as the sitting Chair is
not a new claim this module invents -- it is the same fact already on record
elsewhere in this repo, made queryable. `term_start` is deliberately a round,
approximate date (not a specific real appointment date this repo has no
source for) -- CONTRACT.md's "never guess a legal value" governs STATUTORY
facts (deadlines, district boundaries, permitted uses); a placeholder seat
term-start for a roster the app needs merely to FUNCTION is not that kind of
fact, and is corrected trivially (a normal `board_members` row edit,
whenever this project gets a roster-admin screen) if it is ever wrong.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

#: (display_name, seat, is_chair) -- source: the signature block of the
#: real adopted Shattuck decision, in signing order.
_SEED_MEMBERS: tuple[tuple[str, str, bool], ...] = (
    ("Ben Frey", "Chair", True),
    ("Lucas Kostenbader", "Vice-Chair", False),
    ("Kevin Houghton", "Member", False),
    ("Wanda Wilcox", "Member", False),
    ("Scott Shott", "Member", False),
    ("Tyler Tibbitts", "Member", False),
    ("Mike Titus", "Member", False),
)

_SEED_TERM_START = "2024-01-01"


def _new_id() -> str:
    return uuid.uuid4().hex


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def ensure_seed_board(conn: sqlite3.Connection) -> int:
    """Idempotently seed the real sitting Planning Board if `board_members`
    is completely empty. Returns the number of seats created (0 on every
    call after the first). Never touches an existing roster -- if even ONE
    board_members row already exists (a real roster someone has started
    entering by hand), this function does nothing at all, so it can never
    clobber real data with placeholder seed data.
    """
    existing = conn.execute("SELECT 1 FROM board_members LIMIT 1;").fetchone()
    if existing is not None:
        return 0

    now = _utc_now_iso()
    created = 0
    conn.execute("BEGIN;")
    try:
        for display_name, seat, is_chair in _SEED_MEMBERS:
            user_id = _new_id()
            conn.execute(
                "INSERT INTO users (id, display_name, role, active, created_at) "
                "VALUES (?, ?, 'board_member', 1, ?);",
                (user_id, display_name, now),
            )
            conn.execute(
                """
                INSERT INTO board_members
                    (id, user_id, seat, is_alternate, is_chair, term_start, term_end, created_at)
                VALUES (?, ?, ?, 0, ?, ?, NULL, ?);
                """,
                (_new_id(), user_id, seat, int(is_chair), _SEED_TERM_START, now),
            )
            created += 1
        conn.execute("COMMIT;")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK;")
        raise
    return created


def list_sitting_members(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Currently-sitting seats (`term_end IS NULL`), chair first then by
    name -- the same ordering render/case_findings.py's own signature grid
    already uses, so the meeting page's mover/second choices read in the
    same order the eventual document signs in."""
    rows = conn.execute(
        """
        SELECT bm.id AS board_member_id, u.display_name AS name, bm.seat AS seat,
               bm.is_chair AS is_chair, bm.is_alternate AS is_alternate
        FROM board_members bm
        JOIN users u ON u.id = bm.user_id
        WHERE bm.term_end IS NULL
        ORDER BY bm.is_chair DESC, bm.is_alternate ASC, u.display_name;
        """
    ).fetchall()
    return [
        {
            "board_member_id": r["board_member_id"],
            "name": r["name"],
            "seat": r["seat"],
            "is_chair": bool(r["is_chair"]),
            "is_alternate": bool(r["is_alternate"]),
        }
        for r in rows
    ]
