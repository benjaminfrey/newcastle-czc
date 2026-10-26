"""Projects in the database (projects brief §5.1): the tables, the conversion of each
draft application into a project, and projects.py's building blocks."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError

from portal_api import projects
from tests.conftest import API_DIR, TEST_URL, _recreate_database

TABLES = {"project", "project_part", "project_form", "submission", "review"}
SNAP = {"source": "manual", "parcel_id": None, "map_lot": "004-036",
        "facts": {"map_lot": "004-036", "location": None, "acres": None, "districts": [], "streets": [],
                  "on_state_highway": None},
        "as_of": None, "verified": False, "disputed": False, "note": ""}


def _applicant(conn) -> str:
    return str(conn.execute(text("INSERT INTO applicant (email) VALUES ('a@example.com') RETURNING id")).scalar())


def _project(conn, parts=("building",)) -> tuple[str, list[str]]:
    pid = projects.create(conn, applicant_id=_applicant(conn), ruleset_key="adopted-v1.0",
                          title="A new building at 461 Sheepscot Road", snapshot=SNAP)
    return pid, [projects.add_part(conn, pid, k) for k in parts]


def test_tables_exist(engine):
    assert TABLES <= set(inspect(engine).get_table_names())


def test_submission_is_insert_only(engine):
    with engine.begin() as conn:
        pid, _ = _project(conn)
        conn.execute(text("UPDATE project SET status = 'submitted' WHERE id = :p"), {"p": pid})
        assert projects.lock(conn, pid, 0, None, {"answers": []}) == 1
    for stmt in ("UPDATE submission SET sha256 = repeat('0', 64)", "DELETE FROM submission"):
        with pytest.raises(ProgrammingError, match="append-only"):
            with engine.begin() as conn:
                conn.execute(text(stmt))


def test_pin_forms_pins_and_unpins(engine):
    with engine.begin() as conn:
        pid, _ = _project(conn)
        projects.pin_forms(conn, pid, {"small_project_plan": 1, "entrance_permit": 1})
        assert projects.forms(conn, pid) == {"small_project_plan": 1, "entrance_permit": 1}
        # A form already pinned keeps its version; one no longer wanted unpins.
        projects.pin_forms(conn, pid, {"small_project_plan": 2})
        assert projects.forms(conn, pid) == {"small_project_plan": 1}
        projects.pin_forms(conn, pid, {"small_project_plan": 2, "entrance_permit": 2})
        assert projects.forms(conn, pid) == {"small_project_plan": 1, "entrance_permit": 2}


def test_parts_add_and_remove(engine):
    with engine.begin() as conn:
        pid, (b1, b2) = _project(conn, ("building", "building"))
        d = projects.add_part(conn, pid, "driveway")
        assert [(p["kind"], p["position"]) for p in projects.parts(conn, pid)] == \
            [("building", 0), ("building", 1), ("driveway", 0)]
        projects.remove_part(conn, pid, b1)
        assert [p["id"] for p in projects.parts(conn, pid)] == [b2, d]


def test_answers_are_kept_per_part(engine):
    with engine.begin() as conn:
        pid, (b1, b2) = _project(conn, ("building", "building"))
        projects.save_answers(conn, pid, [("floor_area", b1, 1200), ("stories", b1, 2), ("deed_book", None, "12")], "t")
        projects.copy_part_answers(conn, pid, ["floor_area"], b1, b2)
        assert projects.answers(conn, pid) == {("floor_area", b1): 1200, ("stories", b1): 2,
                                               ("deed_book", None): "12", ("floor_area", b2): 1200}


def test_lock_with_a_stale_revision_writes_nothing(engine):
    with engine.begin() as conn:
        pid, _ = _project(conn)
        conn.execute(text("UPDATE project SET status = 'submitted', revision = 3 WHERE id = :p"), {"p": pid})
        assert projects.lock(conn, pid, 2, None, {"answers": []}) is None
        assert conn.execute(text("SELECT count(*) FROM submission")).scalar() == 0
        assert conn.execute(text("SELECT status FROM project WHERE id = :p"), {"p": pid}).scalar() == "submitted"
        assert projects.lock(conn, pid, 3, None, {"answers": []}) == 1
        row = conn.execute(text("SELECT status, revision FROM project WHERE id = :p"), {"p": pid}).one()
        assert (row.status, row.revision) == ("locked", 4)


def test_a_locked_project_takes_no_more_changes(engine):
    with engine.begin() as conn:
        pid, _ = _project(conn)
        conn.execute(text("UPDATE project SET status = 'submitted' WHERE id = :p"), {"p": pid})
        projects.lock(conn, pid, 0, None, {"answers": []})
        assert projects.bump(conn, pid, 1) is None


MIGRATION_URL = TEST_URL.rsplit("/", 1)[0] + "/portal_test_migration"


def test_the_migration_turns_each_application_into_a_project():
    _recreate_database(MIGRATION_URL)
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", MIGRATION_URL)
    command.upgrade(cfg, "0006")
    eng = create_engine(MIGRATION_URL)
    try:
        with eng.begin() as conn:
            a = _applicant(conn)
            sp = str(conn.execute(text("INSERT INTO application (applicant_id, form_key, form_version, ruleset_key,"
                                       " revision) VALUES (:a, 'small_project_plan', 1, 'adopted-v1.0', 5) RETURNING id"),
                                  {"a": a}).scalar())
            use = str(conn.execute(text("INSERT INTO application (applicant_id, form_key, form_version, ruleset_key)"
                                        " VALUES (:a, 'use_permit', 1, 'adopted-v1.0') RETURNING id"), {"a": a}).scalar())
            items = [str(conn.execute(text("INSERT INTO application_item (application_id, kind, position)"
                                           " VALUES (:s, :k, :p) RETURNING id"), {"s": sp, "k": k, "p": p}).scalar())
                     for k, p in (("building", 0), ("building", 1), ("component", 0))]
            for app in (sp, use):
                conn.execute(text("INSERT INTO property_snapshot (application_id, source, map_lot, facts, verified)"
                                  " VALUES (:s, 'manual', '004-036', '{}', false)"), {"s": app})
            conn.execute(text("INSERT INTO answer (application_id, field_id, item_id, value, set_by)"
                              " VALUES (:s, 'floor_area', :i, '1200', 't'), (:s, 'deed_book', NULL, '\"12\"', 't')"),
                         {"s": sp, "i": items[1]})
        command.upgrade(cfg, "0007")
        with eng.begin() as conn:
            got = {str(r.id): (r.title, r.status, r.revision) for r in conn.execute(text(
                "SELECT id, title, status, revision FROM project"))}
            assert got == {sp: ("Small Project Plan Application", "draft", 5), use: ("Use Permit Application", "draft", 0)}
            assert dict(conn.execute(text("SELECT form_key, project_id::text FROM project_form")).all()) == \
                {"small_project_plan": sp, "use_permit": use}
            parts = conn.execute(text("SELECT id::text, project_id::text, kind FROM project_part ORDER BY kind, position")).all()
            assert [(p.project_id, p.kind) for p in parts] == [(sp, "addition"), (sp, "building"), (sp, "building"), (use, "use")]
            assert {p.id for p in parts} >= set(items)
            assert sorted(conn.execute(text("SELECT field_id, part_id::text FROM answer WHERE project_id = :s"),
                                       {"s": sp}).all()) == [("deed_book", None), ("floor_area", items[1])]
            assert conn.execute(text("SELECT count(*) FROM property_snapshot WHERE project_id IS NOT NULL")).scalar() == 2
        command.downgrade(cfg, "0006")
        command.upgrade(cfg, "head")
    finally:
        eng.dispose()
