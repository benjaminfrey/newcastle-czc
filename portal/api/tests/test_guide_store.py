"""The guide's record (plan 2, Task 5): append-only, so backing up is kept as data (spec §9)."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from portal_api.guide import store
from portal_api.guide.engine import Action
from tests.test_projects_schema import _project

SHOWN = {"turn_id": "lot", "ask": "Here's what the Town knows about your lot. Is it right?"}


def _started(conn) -> str:
    pid, _ = _project(conn)
    store.start(conn, pid, "new_house", "d" * 64)
    return pid


def test_actions_come_back_in_order(engine):
    with engine.begin() as conn:
        pid = _started(conn)
        assert store.record(conn, pid, Action("answer", "lot", "yes"), SHOWN, "d" * 64, "applicant:x") == 1
        assert store.record(conn, pid, Action("answer", "confirm", "yes"), SHOWN, "d" * 64, "applicant:x") == 2
        store.record(conn, pid, Action("back", None, None), SHOWN, "d" * 64, "applicant:x")
        opening, actions = store.conversation(conn, pid)
    assert opening == "new_house"
    assert actions == [Action("answer", "lot", "yes"), Action("answer", "confirm", "yes"), Action("back", None, None)]


def test_no_conversation_is_none(engine):
    with engine.begin() as conn:
        pid, _ = _project(conn)
        assert store.conversation(conn, pid) is None


def test_a_restart_starts_the_actions_over(engine):
    with engine.begin() as conn:
        pid = _started(conn)
        store.record(conn, pid, Action("answer", "lot", "yes"), SHOWN, "d" * 64, "a")
        store.restart(conn, pid, "change_of_use", SHOWN, "d" * 64, "a")
        store.record(conn, pid, Action("answer", "lot", "no"), SHOWN, "d" * 64, "a")
        opening, actions = store.conversation(conn, pid)
    assert opening == "change_of_use" and actions == [Action("answer", "lot", "no")]


def test_actions_cannot_be_changed_or_deleted(engine):
    with engine.begin() as conn:
        pid = _started(conn)
        store.record(conn, pid, Action("answer", "lot", "yes"), SHOWN, "d" * 64, "a")
        store.add_note(conn, pid, "We'd like a porch too.", "a")
    for stmt in ("UPDATE guide_action SET turn_id = 'x'", "DELETE FROM guide_action",
                 "UPDATE guide_note SET body = 'x'", "DELETE FROM guide_note"):
        with pytest.raises(ProgrammingError, match="append-only"):
            with engine.begin() as conn:
                conn.execute(text(stmt))


def test_notes_come_back_in_order(engine):
    with engine.begin() as conn:
        pid = _started(conn)
        store.add_note(conn, pid, "First.", "a")
        store.add_note(conn, pid, "Second.", "a")
        assert [n["body"] for n in store.notes(conn, pid)] == ["First.", "Second."]


@pytest.mark.parametrize("body", ["", "x" * 4001])
def test_a_note_must_be_1_to_4000_characters(engine, body):
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            pid = _started(conn)
            store.add_note(conn, pid, body, "a")


def test_a_revisit_is_recorded_and_replayed(engine):
    with engine.begin() as conn:
        pid = _started(conn)
        store.record(conn, pid, Action("answer", "lot", "yes"), SHOWN, "d" * 64, "applicant:x")
        assert store.record(conn, pid, Action("revisit", "lot", None), SHOWN, "d" * 64, "applicant:x") == 2
        _, actions = store.conversation(conn, pid)
    assert actions[-1] == Action("revisit", "lot", None)
