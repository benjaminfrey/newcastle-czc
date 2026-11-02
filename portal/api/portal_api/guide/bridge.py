"""The guide's numbers, carried into the project's form answers.

The project's dashboard, its reviews and fees (`forms/needs.py`), the printed forms and Send all
read the form answers, so the guide writes each number it settles into the form field its turn
names, for the first part of the opening's kind. Stories are written as the Code counts them.
A value the form wouldn't accept, or one the person took back, leaves the field empty again, but
only a field the guide filled: an answer someone typed on the form is never cleared here.
"""

from sqlalchemy import Connection, text

from portal_api import projects as pj
from portal_api.forms.answers import AnswerError, check_value
from portal_api.forms.expr import evaluate
from portal_api.guide.checks import counted_stories
from portal_api.guide.content import load_content

GUIDE = "guide:"


def _get(facts: dict, path: str):
    cur = facts
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _guide_set(conn: Connection, project_id: str) -> set[tuple]:
    """The fields whose latest answer the guide wrote."""
    return {(r.field_id, str(r.part_id) if r.part_id else None) for r in conn.execute(text(
        "SELECT DISTINCT ON (field_id, part_id) field_id, part_id, set_by FROM answer"
        " WHERE project_id = :p ORDER BY field_id, part_id, seq DESC"
    ), {"p": project_id}) if r.set_by.startswith(GUIDE)}


def sync(conn: Connection, loaded, state, by: str) -> None:
    """Write what changed. `loaded` is the project as routes/projects.py's Loaded sees it."""
    content = load_content()
    kind = content.openings[state.opening].part
    part_id = next((p["id"] for p in loaded.parts if p["kind"] == kind), None)
    current = pj.answers(conn, loaded.row.id)
    ours = _guide_set(conn, loaded.row.id)
    changes, seen = [], set()
    for t in content.turns:
        if not t.answer_field or t.answer_field in seen:
            continue
        if t.when is not None and evaluate(t.when, state.facts) is False:
            continue
        seen.add(t.answer_field)
        try:
            section, f = loaded.form.field(t.answer_field)
        except KeyError:
            continue
        key = (t.answer_field, part_id if section.repeat else None)
        if section.repeat and part_id is None:
            continue
        value = counted_stories(state.facts) if t.computed == "stories" else _get(state.facts, t.fact)
        checked = None
        if value is not None:
            try:
                checked = check_value(f, value)
            except AnswerError:
                checked = None
        if checked is None:
            if key in current and key in ours:
                changes.append((*key, None))
        elif current.get(key) != checked:
            changes.append((*key, checked))
    pj.save_answers(conn, loaded.row.id, changes, GUIDE + by)
