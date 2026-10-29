"""parts.yaml and the project's form (projects brief §4, §6.2)."""

from portal_api.forms.formdefs import ICONS, latest_version, load_form
from portal_api.forms.parts import derived, load_parts, project_form, wanted_forms
from portal_api.ruleset import load_ruleset

RULESET = load_ruleset()
ALL = ["building", "addition", "renovation", "site", "use", "driveway", "divide", "other"]


def test_parts_load_in_tile_order_with_the_briefs_icons():
    parts = load_parts()
    assert parts.ids == ALL
    assert {p.id: p.icon for p in parts.parts} == {
        "building": "building-cottage", "addition": "home-plus", "renovation": "paint", "site": "shovel",
        "use": "building-store", "driveway": "road", "divide": "layout-grid", "other": "help-circle"}
    assert all(p.icon in ICONS for p in parts.parts)
    assert [p.id for p in parts.parts if p.repeats] == ["building", "addition"]
    assert all((p.status, p.approved_by, p.approved_on) == ("approved", "Ben Frey, Planning Board chair", "2026-10-28")
               for p in parts.parts)
    assert (parts.project_status, parts.project_approved_by) == ("approved", "Ben Frey, Planning Board chair")


def test_every_section_a_part_names_exists():
    parts = load_parts()
    refs = [r for p in parts.parts for r in p.sections] + [(s.form_key, s.section_id) for s in parts.project_sections]
    for form_key, section_id in refs:
        form = load_form(form_key, latest_version(form_key), RULESET)
        assert section_id in {s.id for s in form.sections}, (form_key, section_id)


def test_every_input_a_part_names_is_a_question_it_asks():
    parts = load_parts()
    form = project_form(wanted_forms(ALL, parts), ALL, RULESET, parts)
    asked = {f.id for _, f in form.fields() if f.is_question}
    for p in parts.parts:
        assert set(p.inputs.values()) <= asked, p.id
    assert set(parts.project_inputs.values()) <= asked


def test_field_ids_are_unique_across_the_forms():
    form = project_form(wanted_forms(ALL, load_parts()), ALL, RULESET)
    ids = [f.id for _, f in form.fields()]
    assert len(ids) == len(set(ids))


def test_one_step_per_part_present_after_the_cover():
    form = project_form(wanted_forms(["driveway", "building"], load_parts()), ["driveway", "building"], RULESET)
    assert [s.id for s in form.steps] == ["your_lot", "about_you", "the_work", "building", "driveway"]
    building = [s for s in form.sections if s.step == "building"]
    assert {s.repeat.kind for s in building} == {"building"}
    assert all(f.step is None for s in form.sections for f in s.fields)


def test_an_addition_walks_its_own_parts():
    form = project_form(wanted_forms(["addition"], load_parts()), ["addition"], RULESET)
    (component,) = [s for s in form.sections if s.id == "component"]
    assert component.repeat.kind == "addition" and component.step == "addition"


def test_what_only_prints_comes_last_and_is_never_asked():
    form = project_form(wanted_forms(["use"], load_parts()), ["use"], RULESET)
    tail = [s.id for s in form.sections if s.step is None]
    assert set(tail) >= {"certification", "office", "use_header", "use_certification", "use_office"}
    assert not any(f.is_question for s in form.sections if s.step is None for f in s.fields)


def test_derived_answers():
    rows = [{"id": "b1", "kind": "building"}, {"id": "b2", "kind": "building"}, {"id": "s", "kind": "site"}]
    got = derived(rows, {("dwelling_units", "b1"): 2.0, ("dwelling_units", "b2"): {"unknown": True}})
    assert got == {("work_kinds", None): ["new_building", "site"], ("new_homes_total", None): 2.0}
