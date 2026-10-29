"""Sign-in links and sessions. Only SHA-256 hashes of tokens are stored."""

import hashlib
import ipaddress
import secrets
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy import Connection, text

from portal_api.db import transaction

SESSION_COOKIE = "portal_session"
# Serialises sign-in link reservations (see reserve_signin_token).
_SIGNIN_LOCK = 7_041_956


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


def upsert_applicant(conn: Connection, email: str) -> Applicant:
    r = conn.execute(
        text(
            "INSERT INTO applicant (email) VALUES (:email) "
            "ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email RETURNING id, email, role"
        ),
        {"email": email},
    ).one()
    return Applicant(id=str(r.id), email=r.email, role=r.role)


def rate_bucket(ip: str | None) -> str | None:
    """IPv4 addresses count singly; IPv6 per /64, which one client can rotate through."""
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if isinstance(addr, ipaddress.IPv6Address):
        if addr.ipv4_mapped:
            return str(addr.ipv4_mapped)
        return str(ipaddress.IPv6Network(f"{addr}/64", strict=False))
    return str(addr)


@dataclass(frozen=True)
class Limits:
    per_email_ip: int
    per_email: int
    per_ip: int
    global_: int


def reserve_signin_token(conn: Connection, *, email: str, hashed: str, bucket: str | None,
                         minutes: int, limits: Limits) -> str | None:
    """Checks the hourly limits and records an unsent token, or returns None if over a limit.
    One lock serialises every check-and-insert, so parallel requests cannot overshoot.
    Commit promptly: nothing slow may run while the lock is held."""
    conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SIGNIN_LOCK})
    c = conn.execute(text(
        "SELECT "
        " count(*) FILTER (WHERE email = :e AND requested_ip IS NOT DISTINCT FROM :b) AS email_ip,"
        " count(*) FILTER (WHERE email = :e) AS email,"
        " count(*) FILTER (WHERE :b IS NOT NULL AND requested_ip = :b) AS ip,"
        " count(*) AS total "
        "FROM signin_token WHERE created_at > now() - interval '1 hour'"
    ), {"e": email, "b": bucket}).one()
    if (c.email_ip >= limits.per_email_ip or c.email >= limits.per_email
            or c.ip >= limits.per_ip or c.total >= limits.global_):
        return None
    return str(conn.execute(text(
        "INSERT INTO signin_token (email, token_hash, requested_ip, expires_at) "
        "VALUES (:e, :h, :b, now() + make_interval(mins => :m)) RETURNING id"
    ), {"e": email, "h": hashed, "b": bucket, "m": minutes}).scalar())


def mark_sent(conn: Connection, token_id: str) -> None:
    conn.execute(text("UPDATE signin_token SET sent_at = now() WHERE id = :i"), {"i": token_id})


def discard_signin_token(conn: Connection, token_id: str) -> None:
    conn.execute(text("DELETE FROM signin_token WHERE id = :i"), {"i": token_id})


def redeem_signin_token(conn: Connection, hashed: str) -> Applicant | None:
    """Marks the token used and returns its applicant (created now if new), or None if
    unknown, unsent, used or expired. The conditional UPDATE is atomic, so two
    concurrent redemptions cannot both succeed."""
    row = conn.execute(text(
        "UPDATE signin_token SET used_at = now() "
        "WHERE token_hash = :h AND used_at IS NULL AND sent_at IS NOT NULL AND expires_at > now() "
        "RETURNING email"
    ), {"h": hashed}).one_or_none()
    if row is None:
        return None
    return upsert_applicant(conn, row.email)


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


DETAILS = ("name", "phone", "mailing_address")


def details(conn: Connection, applicant_id: str) -> dict:
    """The account's details: name, phone and mailing address, each None until given."""
    r = conn.execute(text("SELECT name, phone, mailing_address FROM applicant WHERE id = :a"),
                     {"a": applicant_id}).one()
    return {k: getattr(r, k) for k in DETAILS}


def save_details(conn: Connection, applicant_id: str, new: dict) -> list[str]:
    """Saves the details; returns the names of those that changed."""
    old = details(conn, applicant_id)
    changed = [k for k in DETAILS if old[k] != new[k]]
    if changed:
        conn.execute(text("UPDATE applicant SET name = :name, phone = :phone, mailing_address = :mailing_address"
                          " WHERE id = :a"), {**new, "a": applicant_id})
    return changed


def current_applicant(request: Request, conn: Connection) -> Applicant | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    row = conn.execute(text(
        "SELECT applicant_id FROM session WHERE token_hash = :h "
        "AND revoked_at IS NULL AND expires_at > now()"
    ), {"h": token_hash(token)}).one_or_none()
    return _applicant_by_id(conn, str(row.applicant_id)) if row else None


def require_applicant(request: Request, conn: Connection = transaction) -> Applicant:
    applicant = current_applicant(request, conn)
    if applicant is None:
        raise HTTPException(status_code=401, detail="signed_out")
    return applicant


# For route signatures: `applicant: Applicant = auth.require`.
require = Depends(require_applicant, scope="function")
