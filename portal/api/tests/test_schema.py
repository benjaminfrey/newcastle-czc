import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError


def test_email_must_be_lowercase(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO applicant (email) VALUES ('Ben@Example.com')"))


def test_email_is_unique(engine):
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO applicant (email) VALUES ('a@example.com')"))
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO applicant (email) VALUES ('a@example.com')"))


def test_role_is_restricted(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO applicant (email, role) VALUES ('b@example.com', 'mayor')"))


def test_event_rows_cannot_be_updated_or_deleted(engine):
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO event (id, at, actor, kind, payload_json, prev_hash, hash) "
            "VALUES (gen_random_uuid(), 'now', 'system', 'test', '{}', repeat('0',64), repeat('1',64))"
        ))
    for stmt in ("UPDATE event SET kind='x'", "DELETE FROM event"):
        with pytest.raises(ProgrammingError, match="event is append-only"):
            with engine.begin() as conn:
                conn.execute(text(stmt))
