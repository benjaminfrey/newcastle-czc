import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from tests.conftest import API_DIR, TEST_URL

TABLES = {"application", "property_snapshot", "application_item", "answer", "section_note", "attachment"}


def _application(conn) -> str:
    applicant = conn.execute(text("INSERT INTO applicant (email) VALUES ('a@example.com') RETURNING id")).scalar()
    return str(conn.execute(text(
        "INSERT INTO application (applicant_id, form_key, form_version, ruleset_key) "
        "VALUES (:a, 'use_permit', 1, 'adopted-v1.0') RETURNING id"), {"a": applicant}).scalar())


def test_tables_exist(engine):
    assert TABLES <= set(inspect(engine).get_table_names())


def test_answer_is_insert_only(engine):
    with engine.begin() as conn:
        app_id = _application(conn)
        conn.execute(text("INSERT INTO answer (application_id, field_id, value, set_by) "
                          "VALUES (:a, 'deed_book', '\"12\"', 'applicant')"), {"a": app_id})
    for stmt in ("UPDATE answer SET field_id = 'x'", "DELETE FROM answer",
                 "UPDATE section_note SET text = 'x'"):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO section_note (application_id, section_id, text, set_by) "
                              "VALUES (:a, 's', 'n', 'applicant')"), {"a": app_id})
        with pytest.raises(ProgrammingError, match="append-only"):
            with engine.begin() as conn:
                conn.execute(text(stmt))


def test_snapshot_source_is_checked(engine):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            app_id = _application(conn)
            conn.execute(text("INSERT INTO property_snapshot (application_id, source, map_lot, facts, verified) "
                              "VALUES (:a, 'guess', '004-036', '{}', false)"), {"a": app_id})


def test_downgrade_removes_tables(engine):
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", TEST_URL)
    command.downgrade(cfg, "0004")
    try:
        assert not TABLES & set(inspect(engine).get_table_names())
    finally:
        command.upgrade(cfg, "head")
    assert TABLES <= set(inspect(engine).get_table_names())
