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


# ---- Steps, screens, controls and defaults (the wizard) ----

def stepped():
    cover = copy.deepcopy(COVER)
    cover["steps"] = [{"id": "your_lot", "title": "Your lot"}]
    cover["sections"][0]["step"] = "your_lot"
    form = copy.deepcopy(FORM)
    form["steps"] = [{"id": "buildings", "title": "Buildings"}, {"id": "extra", "title": "Extra"}]
    b = form["sections"][0]
    b["step"] = "buildings"
    b["screens"] = [{"id": "shape", "layout": None}]
    b["fields"][0].update(control="stepper", screen="shape")
    b["fields"][1].update(control="tiles", screen="shape")
    return cover, form


def broken_stepped(tmp_path, ruleset, change):
    cover, form = stepped()
    change(cover, form)
    write(tmp_path, cover=cover, form=form)
    with pytest.raises(DefinitionError) as exc:
        load_form("test_permit", 1, ruleset, root=tmp_path)
    return str(exc.value)


def test_steps_load_in_order_with_the_cover_first(tmp_path, ruleset):
    cover, form = stepped()
    write(tmp_path, cover=cover, form=form)
    f = load_form("test_permit", 1, ruleset, root=tmp_path)
    assert [s.id for s in f.steps] == ["your_lot", "buildings", "extra"]
    assert f.step_of("deed_book") == "your_lot" and f.step_of("stories") == "buildings"
    b = f.sections[1]
    assert [(x.id, x.layout) for x in b.screens] == [("shape", None)]
    assert b.fields[0].screen == "shape" and b.fields[0].control == "stepper"


def test_field_step_overrides_section_step(tmp_path, ruleset):
    cover, form = stepped()
    form["sections"][0]["fields"][3]["step"] = "extra"  # the at_submit field; not a question
    cover["sections"][0]["fields"][1]["step"] = "your_lot"
    write(tmp_path, cover=cover, form=form)
    f = load_form("test_permit", 1, ruleset, root=tmp_path)
    assert f.step_of("signature") == "extra"


def test_rejects_question_without_a_step(tmp_path, ruleset):
    assert "step" in broken_stepped(tmp_path, ruleset, lambda c, f: c["sections"][0].pop("step"))


def test_rejects_unknown_step(tmp_path, ruleset):
    assert "nowhere" in broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0].update(step="nowhere"))


def test_screen_groups_load(tmp_path, ruleset):
    cover, form = stepped()
    form["sections"][0]["screens"] = [{"id": "walls", "layout": "compass"}]
    for fl in form["sections"][0]["fields"][:2]:
        fl["screen"] = "walls"
    write(tmp_path, cover=cover, form=form)
    b = load_form("test_permit", 1, ruleset, root=tmp_path).sections[1]
    assert b.screens[0].layout == "compass"
    assert [fl.screen for fl in b.fields[:2]] == ["walls", "walls"]


def test_rejects_undeclared_screen(tmp_path, ruleset):
    assert "nowhere" in broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0]["fields"][0].update(screen="nowhere"))


def test_rejects_bad_screen_layout(tmp_path, ruleset):
    assert "layout" in broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0]["screens"][0].update(layout="spiral"))


def test_pages_and_add_options_are_gone(tmp_path, ruleset):
    assert "pages" in broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0].update(pages=[{"id": "a", "title": "A"}]))
    assert "add_options" in broken_stepped(
        tmp_path, ruleset, lambda c, f: f["sections"][0]["repeat"].update(add_options=[{"label": "A building"}]))


def test_rejects_unknown_control(tmp_path, ruleset):
    msg = broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0]["fields"][0].update(control="knob"))
    assert "control" in msg


def test_rejects_bad_default(tmp_path, ruleset):
    def bad(c, f):
        f["sections"][0]["fields"][0].update(default="maybe")
    assert "default" in broken_stepped(tmp_path, ruleset, bad)


def test_rejects_malformed_step(tmp_path, ruleset):
    msg = broken_stepped(tmp_path, ruleset, lambda c, f: f["steps"].append({"title": "No id"}))
    assert "step" in msg and "test-permit" in msg


def test_rejects_malformed_screen(tmp_path, ruleset):
    msg = broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0]["screens"].append({"layout": "compass"}))
    assert "screen" in msg


def test_rejects_control_that_does_not_suit_the_type(tmp_path, ruleset):
    # A switch answers yes or no; on a number it would be refused at every save.
    msg = broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0]["fields"][0].update(control="switch"))
    assert "switch" in msg and "number" in msg


def test_a_form_without_steps_still_loads(tmp_path, ruleset):
    write(tmp_path)
    assert load_form("test_permit", 1, ruleset, root=tmp_path).steps == ()


# ---- Cards, icons and copies (task-list brief) ----

def test_screen_may_span_sections_of_one_step(tmp_path, ruleset):
    cover, form = stepped()
    extra = copy.deepcopy(form["sections"][0])
    extra.update(id="building_more", screens=[])
    extra["fields"] = [{"id": "height", "official_label": "Height", "source": "question", "label": "How tall?",
                        "type": "number", "why": "8.10.b.1", "screen": "shape", **APPROVED}]
    form["sections"].append(extra)
    write(tmp_path, cover=cover, form=form)
    f = load_form("test_permit", 1, ruleset, root=tmp_path)
    assert f.field("height")[1].screen == "shape" and f.screen_layout("height") is None


def test_rejects_screen_across_repeat_kinds(tmp_path, ruleset):
    def change(c, f):
        other = copy.deepcopy(f["sections"][0])
        other.update(id="component", screens=[])
        other["repeat"] = {"kind": "component", "add_label": "Add one", "min": 0, "max": 5}
        other["fields"] = [{"id": "c_width", "official_label": "Width", "source": "question", "label": "How wide?",
                            "type": "number", "why": "8.10.b.1", "screen": "shape", **APPROVED}]
        f["sections"].append(other)
    assert "repeat" in broken_stepped(tmp_path, ruleset, change)


def test_rejects_duplicate_screen_ids_in_a_step(tmp_path, ruleset):
    def change(c, f):
        f["sections"][0]["screens"] = [{"id": "shape"}, {"id": "shape"}]
    assert "duplicate screen" in broken_stepped(tmp_path, ruleset, change)


def test_icons_load_and_unknown_icons_are_refused(tmp_path, ruleset):
    cover, form = stepped()
    opts = form["sections"][0]["fields"][1]["options"]
    opts[0]["icon"], opts[1]["icon"] = "home", "building"
    write(tmp_path, cover=cover, form=form)
    f = load_form("test_permit", 1, ruleset, root=tmp_path)
    assert [o.icon for o in f.field("roof")[1].options] == ["home", "building"]
    def unknown(c, f):
        f["sections"][0]["fields"][1]["options"][0]["icon"] = "not-an-icon"
        f["sections"][0]["fields"][1]["options"][1]["icon"] = "home"
    assert "not-an-icon" in broken_stepped(tmp_path, ruleset, unknown)


def test_rejects_icons_on_some_options(tmp_path, ruleset):
    assert "every option" in broken_stepped(
        tmp_path, ruleset, lambda c, f: f["sections"][0]["fields"][1]["options"][0].update(icon="home"))


def test_copies_only_in_a_repeat(tmp_path, ruleset):
    cover, form = stepped()
    form["sections"][0]["fields"][0]["copies"] = True
    write(tmp_path, cover=cover, form=form)
    assert load_form("test_permit", 1, ruleset, root=tmp_path).field("stories")[1].copies is True
    assert "copies" in broken_stepped(tmp_path, ruleset, lambda c, f: c["sections"][0]["fields"][1].update(copies=True))


def test_ask_first_is_a_rank(tmp_path, ruleset):
    cover, form = stepped()
    form["sections"][0]["fields"][0]["ask_first"] = 2
    form["sections"][0]["fields"][1]["ask_first"] = 1
    write(tmp_path, cover=cover, form=form)
    f = load_form("test_permit", 1, ruleset, root=tmp_path)
    assert (f.field("stories")[1].ask_first, f.field("roof")[1].ask_first) == (2, 1)
    assert "ask_first" in broken_stepped(tmp_path, ruleset, lambda c, f: f["sections"][0]["fields"][0].update(ask_first=-1))


def test_short_names_load(tmp_path, ruleset):
    cover, form = stepped()
    form["sections"][0]["fields"][0]["short"] = "Stories"
    write(tmp_path, cover=cover, form=form)
    assert load_form("test_permit", 1, ruleset, root=tmp_path).field("stories")[1].short == "Stories"
