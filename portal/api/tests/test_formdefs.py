"""The form-definition format: a small valid form is built in a temporary folder,
then broken one rule at a time."""

import copy

import pytest
import yaml

from portal_api.forms.definitions import DefinitionError
from portal_api.forms.formdefs import form_drafts, latest_version, load_form
from portal_api.ruleset import load_ruleset

APPROVED = {"status": "approved", "approved_by": "Ben Frey, Planning Board chair", "approved_on": "2026-10-21"}

COVER = {
    "key": "cover_sheet", "version": 1, "ruleset_key": "adopted-v1.0", "official_title": "Cover Sheet",
    "sections": [{
        "id": "location", "official_title": "Location of Proposed Project", "chapter": "Where it is", **APPROVED,
        "fields": [
            {"id": "map_lot", "official_label": "Map / Lot", "source": "property", "from": "map_lot", **APPROVED},
            {"id": "deed_book", "official_label": "Deed Book", "source": "question", "label": "Deed book?",
             "type": "text", "why": "8.2.a.2", "allow_unknown": True, **APPROVED},
        ],
    }],
}

FORM = {
    "key": "test_permit", "version": 1, "ruleset_key": "adopted-v1.0", "official_title": "Test Form",
    "include": ["cover-sheet.v1"],
    "sections": [
        {"id": "building", "official_title": "Building Form", "chapter": "Your building", **APPROVED,
         "repeat": {"kind": "building", "add_label": "Add another building", "min": 1, "max": 20},
         "fields": [
             {"id": "stories", "official_label": "Total number of stories", "source": "question",
              "label": "How many stories?", "type": "number", "min": 1, "max": 10, "why": "8.10.b.1",
              "required": True, **APPROVED},
             {"id": "roof", "official_label": "Roof Style", "source": "question", "label": "Roof shape?",
              "type": "choice", "why": "8.10.b.1", "show_if": {"gte": ["item.stories", 1]},
              "options": [{"value": "gable", "label": "Gable (a simple peak)", "official": "Gable"},
                          {"value": "shed", "label": "Shed (one slope)", "official": "Shed"}], **APPROVED},
             {"id": "map_lot_copy", "official_label": "Map / Lot", "source": "derived", "from": "map_lot", **APPROVED},
             {"id": "signature", "official_label": "Applicant Signature", "source": "at_submit", **APPROVED},
         ]},
    ],
}


def write(root, cover=COVER, form=FORM, name="test-permit.v1.yaml"):
    (root / "cover-sheet.v1.yaml").write_text(yaml.safe_dump(cover))
    (root / name).write_text(yaml.safe_dump(form))


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()


def broken(tmp_path, ruleset, change):
    form = copy.deepcopy(FORM)
    change(form)
    write(tmp_path, form=form)
    with pytest.raises(DefinitionError) as exc:
        load_form("test_permit", 1, ruleset, root=tmp_path)
    return str(exc.value)


def test_valid_fixture_loads(tmp_path, ruleset):
    write(tmp_path)
    form = load_form("test_permit", 1, ruleset, root=tmp_path)
    assert form.official_title == "Test Form"
    assert [s.id for s in form.sections] == ["location", "building"]
    assert [f.id for _, f in form.fields()] == ["map_lot", "deed_book", "stories", "roof", "map_lot_copy", "signature"]
    building = form.sections[1]
    assert building.repeat.kind == "building" and building.repeat.max == 20
    roof = building.fields[1]
    assert roof.is_question and [o.official for o in roof.options] == ["Gable", "Shed"]
    assert not building.fields[3].is_question


def test_rejects_duplicate_ids(tmp_path, ruleset):
    msg = broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][1].update(id="deed_book"))
    assert "deed_book" in msg and "duplicate" in msg


def test_rejects_unknown_type(tmp_path, ruleset):
    assert "type" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][0].update(type="slider"))


def test_rejects_unknown_source(tmp_path, ruleset):
    assert "source" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][3].update(source="guess"))


def test_rejects_choice_without_options(tmp_path, ruleset):
    assert "options" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][1].update(options=[]))


def test_rejects_duplicate_option_values(tmp_path, ruleset):
    def dup(f):
        f["sections"][0]["fields"][1]["options"][1]["value"] = "gable"
    assert "option" in broken(tmp_path, ruleset, dup)


def test_rejects_min_above_max(tmp_path, ruleset):
    assert "min" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][0].update(min=11))


def test_rejects_bad_show_if(tmp_path, ruleset):
    assert "roof" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][1].update(show_if={"maybe": "x"}))


def test_rejects_show_if_outside_the_scopes(tmp_path, ruleset):
    msg = broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][1].update(show_if={"eq": ["stories", 1]}))
    assert "answers." in msg


def test_rejects_unresolved_citation(tmp_path, ruleset):
    assert "99.1.a" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][0].update(why="99.1.a"))


def test_rejects_other_ruleset(tmp_path, ruleset):
    assert "ruleset" in broken(tmp_path, ruleset, lambda f: f.update(ruleset_key="v1.2-draft"))


def test_rejects_unknown_from(tmp_path, ruleset):
    assert "from" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][2].update(**{"from": "owner_name"}))


def test_rejects_question_without_label(tmp_path, ruleset):
    assert "label" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][0].pop("label"))


def test_rejects_required_upload(tmp_path, ruleset):
    def up(f):
        f["sections"][0]["fields"][0].update(type="upload", required=True)
        for k in ("min", "max"):
            f["sections"][0]["fields"][0].pop(k)
    assert "upload" in broken(tmp_path, ruleset, up)


def test_rejects_bad_repeat(tmp_path, ruleset):
    assert "repeat" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["repeat"].update(min=3, max=2))


def test_rejects_approved_without_approver(tmp_path, ruleset):
    assert "approved_by" in broken(tmp_path, ruleset, lambda f: f["sections"][0]["fields"][0].pop("approved_by"))


def test_form_version_is_pinned(tmp_path, ruleset):
    write(tmp_path)
    v2 = copy.deepcopy(FORM)
    v2.update(version=2, official_title="Test Form, second edition")
    (tmp_path / "test-permit.v2.yaml").write_text(yaml.safe_dump(v2))
    assert load_form("test_permit", 1, ruleset, root=tmp_path).official_title == "Test Form"
    assert latest_version("test_permit", root=tmp_path) == 2


def test_drafts_lists_sections_and_fields(tmp_path, ruleset):
    form = copy.deepcopy(FORM)
    form["sections"][0]["status"] = "draft"
    form["sections"][0]["fields"][1]["status"] = "draft"
    cover = copy.deepcopy(COVER)
    cover["sections"][0]["fields"][1]["status"] = "draft"
    write(tmp_path, cover=cover, form=form)
    drafts = form_drafts(load_form("test_permit", 1, ruleset, root=tmp_path))
    assert {(d.file, d.id) for d in drafts} == {
        ("test-permit.v1.yaml", "building"), ("test-permit.v1.yaml", "roof"), ("cover-sheet.v1.yaml", "deed_book")}
