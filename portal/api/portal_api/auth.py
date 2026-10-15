"""Sign-in links and sessions. Only SHA-256 hashes of tokens are stored."""

import hashlib
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Connection, text

from portal_api.db import get_conn

SESSION_COOKIE = "portal_session"


@dataclass(frozen=True)
class Applicant:
    id: str
    email: str
    role: str


def new_token() -> tuple[str, str]:
    """Returns (token for the applicant, hash for the database)."""
    token = secrets.token_urlsafe(32)
    return token, token_hash(token)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalise_email(email: str) -> str:
    return email.strip().lower()


def upsert_applicant(conn: Connection, email: str) -> str:
    return str(conn.execute(
        text(
            "INSERT INTO applicant (email) VALUES (:email) "
            "ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email RETURNING id"
        ),
        {"email": email},
    ).scalar())


def recent_requests(conn: Connection, *, applicant_id: str, ip: str | None) -> tuple[int, int]:
    by_email = conn.execute(text(
        "SELECT count(*) FROM signin_token WHERE applicant_id = :a "
        "AND created_at > now() - interval '1 hour'"
    ), {"a": applicant_id}).scalar()
    by_ip = conn.execute(text(
        "SELECT count(*) FROM signin_token WHERE requested_ip = :ip "
        "AND created_at > now() - interval '1 hour'"
    ), {"ip": ip}).scalar() if ip else 0
    return by_email, by_ip


def store_signin_token(conn: Connection, *, applicant_id: str, hashed: str, ip: str | None, minutes: int) -> None:
    conn.execute(text(
        "INSERT INTO signin_token (applicant_id, token_hash, requested_ip, expires_at) "
        "VALUES (:a, :h, :ip, now() + make_interval(mins => :m))"
    ), {"a": applicant_id, "h": hashed, "ip": ip, "m": minutes})


def redeem_signin_token(conn: Connection, hashed: str) -> Applicant | None:
    """Marks the token used and returns its applicant, or None if unknown, used or expired.
    The conditional UPDATE is atomic, so two concurrent redemptions cannot both succeed."""
    row = conn.execute(text(
        "UPDATE signin_token SET used_at = now() "
        "WHERE token_hash = :h AND used_at IS NULL AND expires_at > now() "
        "RETURNING applicant_id"
    ), {"h": hashed}).one_or_none()
    if row is None:
        return None
    return _applicant_by_id(conn, str(row.applicant_id))


def create_session(conn: Connection, *, applicant_id: str, days: int) -> str:
    token, hashed = new_token()
    conn.execute(text(
        "INSERT INTO session (applicant_id, token_hash, expires_at) "
        "VALUES (:a, :h, now() + make_interval(days => :d))"
    ), {"a": applicant_id, "h": hashed, "d": days})
    return token


def revoke_session(conn: Connection, token: str) -> str | None:
    row = conn.execute(text(
        "UPDATE session SET revoked_at = now() WHERE token_hash = :h AND revoked_at IS NULL "
        "RETURNING applicant_id"
    ), {"h": token_hash(token)}).one_or_none()
    return str(row.applicant_id) if row else None


def _applicant_by_id(conn: Connection, applicant_id: str) -> Applicant:
    r = conn.execute(text("SELECT id, email, role FROM applicant WHERE id = :a"), {"a": applicant_id}).one()
    return Applicant(id=str(r.id), email=r.email, role=r.role)


def current_applicant(request: Request, conn: Connection) -> Applicant | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = conn.execute(text(
        "SELECT applicant_id FROM session WHERE token_hash = :h "
        "AND revoked_at IS NULL AND expires_at > now()"
    ), {"h": token_hash(token)}).one_or_none()
    return _applicant_by_id(conn, str(row.applicant_id)) if row else None


def require_applicant(request: Request, conn: Connection = Depends(get_conn)) -> Applicant:
    applicant = current_applicant(request, conn)
    if applicant is None:
        raise HTTPException(status_code=401, detail="signed_out")
    return applicant
