"""Implements CONTRACT.md §1.1 S4 (Host/Origin checks) and provides the one
seam a future real authentication system replaces: current_user().

Phase 0/1 has no login (§1.2: no PII, no uploads in this workflow). Every
request acts as one synthetic local operator, so every mutating table's
actor_user_id and every events row still has someone to attribute to.
Swapping in real auth later means replacing current_user()'s body — nothing
else in the app should construct a "who is acting" user id any other way.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# current_user() — THE ONE SEAM real auth replaces.
# ---------------------------------------------------------------------------

SYNTHETIC_USER_ID = "u_local_operator"
SYNTHETIC_USER_DISPLAY_NAME = "Local Operator"
SYNTHETIC_USER_ROLE = "planner"  # one of users.role's CHECK values (0001_init.sql)


@dataclass(frozen=True)
class CurrentUser:
    id: str
    display_name: str
    role: str


def current_user() -> CurrentUser:
    """Return the single synthetic session user for this local,
    single-operator phase of the app.

    THIS IS THE SEAM. When real authentication arrives, this function's body
    is what changes (to read a session / token and look up the real user);
    every caller elsewhere in the app should already be going through
    current_user() rather than hard-coding SYNTHETIC_USER_ID, so nothing else
    needs to change alongside it.
    """
    return CurrentUser(
        id=SYNTHETIC_USER_ID,
        display_name=SYNTHETIC_USER_DISPLAY_NAME,
        role=SYNTHETIC_USER_ROLE,
    )


def ensure_synthetic_user(conn: sqlite3.Connection) -> None:
    """Idempotently make sure the synthetic user row exists, so every
    actor_user_id foreign key that points at current_user().id resolves.
    Safe to call on every startup and from tests; does nothing if the row is
    already there.
    """
    existing = conn.execute("SELECT 1 FROM users WHERE id = ?;", (SYNTHETIC_USER_ID,)).fetchone()
    if existing is not None:
        return

    now = datetime.now(timezone.utc)
    created_at = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"

    conn.execute(
        """
        INSERT INTO users (id, display_name, email, role, active, created_at, actor_user_id)
        VALUES (?, ?, NULL, ?, 1, ?, NULL);
        """,
        (SYNTHETIC_USER_ID, SYNTHETIC_USER_DISPLAY_NAME, SYNTHETIC_USER_ROLE, created_at),
    )


# ---------------------------------------------------------------------------
# Host / Origin validation — CONTRACT.md §1.1 S4.
#
# Pure functions, no framework dependency, so they're testable without
# FastAPI/Starlette. app/main.py's middleware wires these into request
# handling and turns a False into an HTTP 403.
# ---------------------------------------------------------------------------

STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def allowed_hosts(port: int) -> frozenset[str]:
    return frozenset({f"127.0.0.1:{port}", f"localhost:{port}"})


def allowed_origins(port: int) -> frozenset[str]:
    return frozenset({f"http://127.0.0.1:{port}", f"http://localhost:{port}"})


def is_host_allowed(host_header: str | None, port: int) -> bool:
    """CONTRACT.md §1.1 S4: reject (403) any request whose Host header is not
    in {"127.0.0.1:<port>", "localhost:<port>"}. A missing Host header is
    rejected too — every real HTTP/1.1+ request carries one.
    """
    if host_header is None:
        return False
    return host_header in allowed_hosts(port)


def is_origin_allowed(
    method: str,
    origin_header: str | None,
    referer_header: str | None,
    port: int,
) -> bool:
    """CONTRACT.md §1.1 S4: for a state-changing method (POST/PUT/PATCH/
    DELETE), any Origin or Referer header that IS PRESENT must match this
    app's own origin. A state-changing request carrying NEITHER header is
    accepted (curl / --selftest, which send no browser headers at all).

    Origin, when present, is compared for exact equality (it never carries a
    path). Referer, when present, is compared by prefix, since a real Referer
    is a full URL including path/query, not a bare origin.
    """
    if method.upper() not in STATE_CHANGING_METHODS:
        return True
    if origin_header is None and referer_header is None:
        return True

    allowed = allowed_origins(port)

    if origin_header is not None and origin_header not in allowed:
        return False
    if referer_header is not None and not any(referer_header.startswith(o) for o in allowed):
        return False
    return True
