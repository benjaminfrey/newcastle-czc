"""The three application forms and the cover sheet, checked against the Town's
Planning Application packet (the field inventory in the M4 plan) and the Code."""

import re

import pytest
import yaml

from portal_api.forms.definitions import DIR as DEFS_DIR
from portal_api.forms.expr import evaluate
from portal_api.forms.formdefs import FORM_KEYS, form_drafts, latest_version, load_form
from portal_api.ruleset import load_ruleset

VERDICT_WORDS = re.compile(r"\b(approved|denied|compliant|meets|fails|violates)\b", re.IGNORECASE)

# The packet's printed fields, section by section (Cover Sheet and Use Form from the
# Verney Use Application of 2025-04-02; Building Form and Components Section from the
# Dalton application of 2025-09-09). New fields the portal adds are listed separately.
COVER = {
    "Location of Proposed Project": {"Map / Lot", "Street Address", "Deed Book", "Page"},
    "Applicant": {"Email", "Phone", "Address"},
    "Property Owner (if different)": {"Email", "Phone", "Address"},
    "Agent (if applicable)": {"Email", "Phone", "Address"},
    "Site Information (existing)": {"Zoning District", "Lot Area (acres)", "Lot Width (ft)", "Street Frontage (ft)",
                                    "Lot Depth (ft)", "Number of Existing Dwelling Units"},
    "Certification": {"Applicant Signature", "Date", "Name (print)"},
    "Official Use Only": {"Date Received"},
}
USE_FORM = {
    "Proposed Project": {"Applicant Name", "Street Address", "Map / Lot"},
    "Existing": {"Existing Use(s)", "Description"},
    "Proposed": {"Uses to be Established", "Description", "Uses to be Discontinued", "Description of Uses to be Discontinued"},
    "Use Form Certification": {"Applicant Signature", "Date", "Name (print)"},
    "Use Form — Official Use Only": {"Permit Type Required"},
}
BUILDING_FORM = {
    "Building Form": {"Map / Lot", "Street Address", "Zoning District", "Building reference (name)",
                      "Only being renovated, not changing size or location"},
    "Building Location (proposed)": {"Setback from front lot line", "Setback from side lot line",
                                     "Setback from other side lot line", "Setback from rear lot line"},
    "Building Details (proposed)": {"Building type", "Proposed number of dwelling units"},
    "Main Building Mass Details": {"Width of Main Building Mass", "Depth of Main Building Mass",
                                   "Total number of stories", "Floor Area of Main Building Mass",
                                   "Elevation of first (ground) floor", "First floor height", "Second floor height",
                                   "Third floor height", "Fourth floor height", "Roof Style", "Roof Slope on Main Building Mass",
                                   "Exterior finish material"},
    "Windows & Doors - Main Building Mass": {"North facing facade %", "East facing facade %",
                                             "South facing facade %", "West facing facade %"},
}
COMPONENTS = {
    "Components Section": {"Only being renovated, not changing size or location", "Component",
                           "Name of other architectural component", "Building attached to",
                           "Width", "Depth (Length for a Patio)", "Height", "Roof Style on Component", "Roof Slope",
                           "Exterior finish material", "North facing facade %", "East facing facade %",
                           "South facing facade %", "West facing facade %"},
}


@pytest.fixture(scope="module")
def ruleset():
    return load_ruleset()


@pytest.fixture(scope="module")
def forms(ruleset):
    return {k: load_form(k, latest_version(k), ruleset) for k in FORM_KEYS}


def labels_by_section(form, titles):
    out = {}
    for s in form.sections:
        if s.official_title in titles:
            out.setdefault(s.official_title, set()).update(f.official_label for f in s.fields)
    return out


@pytest.mark.parametrize("key,expected", [
    ("use_permit", {**COVER, **USE_FORM}),
    ("small_project_plan", {**COVER, **BUILDING_FORM, **COMPONENTS}),
    ("entrance_permit", COVER),
])
def test_every_packet_field_is_present(forms, key, expected):
    got = labels_by_section(forms[key], expected)
    for title, labels in expected.items():
        assert labels <= got.get(title, set()), (title, labels - got.get(title, set()))


def test_every_field_has_a_source(forms):
    for form in forms.values():
        for _, f in form.fields():
            assert f.source in {"question", "property", "account", "derived", "at_submit", "staff"}


def test_building_classes_follow_article_5(forms, ruleset):
    classes = {n["text"] for k, n in ruleset._nodes.items()
               if k.startswith("adopted-v1.0:a5.s1.c.1.") and k.count(".") == 6}
    assert len(classes) == 9
    _, f = forms["small_project_plan"].field("building_class")
    assert {o.official for o in f.options} == classes


def test_no_standard_met_column(forms):
    for form in forms.values():
        for _, f in form.fields():
            assert "standard met" not in f.official_label.lower()


def test_no_verdict_words_in_form_text(forms):
    for form in forms.values():
        for s, f in form.fields():
            for text in (s.official_title, s.chapter, f.official_label, f.label, f.help,
                         *(o.label for o in f.options), *(o.official for o in f.options)):
                assert not VERDICT_WORDS.search(text or ""), (f.id, text)
        # The layout's words reach the applicant too: steps, sheet pages, "Add a building" choices.
        layout = [st.title for st in form.steps]
        for s in form.sections:
            if s.repeat:
                layout.append(s.repeat.add_label)
        for text in layout:
            assert not VERDICT_WORDS.search(text or ""), text


@pytest.mark.parametrize("on_highway,shown", [(True, True), (False, False), (None, True)])
def test_mainedot_question_shows_unless_known_off_highway(forms, on_highway, shown):
    _, f = forms["entrance_permit"].field("mainedot_permit")
    result = evaluate(f.show_if, {"answers": {}, "item": {}, "property": {"on_state_highway": on_highway}})
    assert (result is not False) is shown


def test_all_entries_start_as_drafts(forms):
    for form in forms.values():
        statuses = {s.status for s in form.sections} | {f.status for _, f in form.fields()}
        assert statuses == {"draft"}
        assert form_drafts(form)


def test_form_keys_match_applications_yaml():
    apps = yaml.safe_load((DEFS_DIR / "applications.yaml").read_text())
    assert set(FORM_KEYS) == {a["key"] for a in apps if a["in_portal"]}


def test_every_question_has_plain_help_or_short_label(forms):
    # One idea per screen: a question label is a single sentence of reasonable length.
    for form in forms.values():
        for _, f in form.fields():
            if f.is_question:
                assert len(f.label) <= 140, f.id
                # Uploads and map points are instructions; compass sliders are named by wall.
                assert f.label.rstrip().endswith("?") or f.type in ("upload", "point") or f.control == "slider", f.id


BUILDING_SECTIONS = ("building", "building_location", "building_details", "building_mass", "building_windows")


@pytest.mark.parametrize("kinds,asked", [
    (["site"], False), (["nonconforming"], False), (["site", "renovation"], True),
    (["new_building"], True), (["addition"], True), (None, True),
])
def test_building_form_only_when_the_work_includes_a_building(forms, kinds, asked):
    # Chair's ruling, 2026-10-23: site-only work is not asked building questions.
    from portal_api.forms.answers import Current, applicable

    form = forms["small_project_plan"]
    answers = {} if kinds is None else {("work_kinds", None): kinds}
    cur = Current(answers=answers, items=[("b1", "building", 0)], property={"on_state_highway": False})
    sections = {s.id for s, _, _ in applicable(form, cur)}
    assert bool(sections & set(BUILDING_SECTIONS)) is asked



# ---- The redesign (chair-approved brief, 2026-10-23) ----

START_AND_REVIEW = 4  # Your project, Your property, What you'll need; Review and sign


@pytest.mark.parametrize("key,steps", [("use_permit", 9), ("small_project_plan", 9), ("entrance_permit", 10)])
def test_step_counts(forms, key, steps):
    assert len(forms[key].steps) + START_AND_REVIEW == steps


def test_cover_steps_come_first(forms):
    for form in forms.values():
        assert [s.title for s in form.steps[:2]] == ["Your lot", "About you"]


def test_every_question_has_a_step_and_repeat_questions_a_page(forms):
    for form in forms.values():
        for s, f in form.fields():
            if f.is_question:
                assert form.step_of(f.id), f.id


def building_questions(sp):
    return [f.id for s, f in sp.fields() if s.repeat and s.repeat.kind == "building" and f.is_question]


def test_building_starts_with_its_type(forms):
    # A detached garage or shed is chosen by type, so the wizard asks the type first (wizard brief,
    # section 4); the printed Building Form keeps the paper form's order.
    sp = forms["small_project_plan"]
    first = [fid for fid in building_questions(sp) if sp.field(fid)[1].ask_first]
    assert first == ["building_class", "dwelling_units"]
    assert building_questions(sp)[0] == "building_name"  # print order unchanged


def test_front_facing_before_walls(forms):
    sp = forms["small_project_plan"]
    order = [f.id for _, f in sp.fields()]
    for facing, first_wall in (("front_facing", "windows_north"), ("component_front_facing", "component_windows_north")):
        assert order[order.index(facing) + 1] == first_wall, facing
        _, f = sp.field(facing)
        assert f.type == "choice" and [o.official for o in f.options] == ["North", "East", "South", "West"]
        assert f.status == "draft" and f.allow_unknown
    assert sp.field("component_front_facing")[1].show_if == sp.field("component_windows_north")[1].show_if


def test_groupings(forms):
    def screen_of(form, fid):
        sec, f = forms[form].field(fid)
        lay = {x.id: x.layout for x in sec.screens}
        return f.screen, lay.get(f.screen)
    pairs = [("cover_sheet_host", "deed_book", "deed_page"), ("small_project_plan", "mass_width", "mass_depth"),
             ("small_project_plan", "component_width", "component_depth"),
             ("entrance_permit", "sight_distance_left", "sight_distance_right"),
             ("entrance_permit", "homes_single_family", "homes_two_family")]
    for form, a, b in pairs:
        form = "small_project_plan" if form == "cover_sheet_host" else form
        assert screen_of(form, a)[0] is not None and screen_of(form, a) == screen_of(form, b), (a, b)
    assert {screen_of("small_project_plan", f) for f in ("setback_front", "setback_side_1", "setback_side_2", "setback_rear")} \
        == {("setbacks", "lot-diagram")}
    assert len({screen_of("small_project_plan", f"windows_{w}") for w in ("north", "east", "south", "west")}) == 1
    assert screen_of("small_project_plan", "windows_north")[1] == "compass"


def test_attached_garage_is_an_addition(forms):
    sp = forms["small_project_plan"]
    _, kind = sp.field("component_kind")
    garage = next(o for o in kind.options if o.value == "garage")
    assert garage.label == "An attached garage" and garage.official == "Garage (attached)"


def test_no_garage_attached_question(forms):
    with pytest.raises(KeyError):
        forms["small_project_plan"].field("garage_attached")


def test_roof_slope_options(forms):
    for fid in ("roof_slope", "component_roof_slope"):
        _, f = forms["small_project_plan"].field(fid)
        assert f.type == "choice" and f.control == "picker"
        assert [o.value for o in f.options] == ["flat", *[f"{n}_12" for n in range(2, 13)], "steeper"]
        assert next(o for o in f.options if o.value == "8_12").official == "8/12"
        assert f.options[0].label == "Flat (under 2/12)" and f.options[-1].label == "Steeper than 12/12"


def test_finish_chips_have_an_other_field(forms):
    sp = forms["small_project_plan"]
    for fid, other in (("exterior_finish", "exterior_finish_other"), ("component_finish", "component_finish_other")):
        _, f = sp.field(fid)
        assert f.type == "multichoice" and f.control == "chips"
        assert [o.official for o in f.options] == [
            "Clapboard", "Wood shingle", "Vinyl siding", "Fibre-cement siding", "Brick", "Stone",
            "Board-and-batten", "Metal siding", "Asphalt shingle roof", "Metal roof", "Slate roof", "Other"]
        _, o = sp.field(other)
        assert {"has": [f"item.{fid}", "other"]} in [o.show_if, *o.show_if.get("all", [])]


def test_switch_defaults(forms):
    want = {"applicant_is_owner": True, "has_agent": False, "renovation_only": False,
            "component_renovation_only": False, "shared_driveway": False}
    seen = {}
    for form in forms.values():
        for _, f in form.fields():
            if f.control == "switch":
                seen[f.id] = f.default
    assert seen == want


def test_pickers_for_buildings_and_roads(forms):
    assert forms["small_project_plan"].field("attached_to")[1].control == "building-picker"
    assert forms["entrance_permit"].field("entrance_street")[1].control == "street-picker"
    assert forms["small_project_plan"].field("building_class")[1].control == "building-type"


def test_window_walls_are_sliders(forms):
    sp = forms["small_project_plan"]
    for wall in ("north", "east", "south", "west"):
        _, f = sp.field(f"windows_{wall}")
        assert f.control == "slider" and f.step_size == 5 and (f.min, f.max) == (0, 100)
        assert f.label == f"{wall.capitalize()} wall"


def test_changed_entries_are_drafts(forms):
    for form in forms.values():
        assert {f.status for _, f in form.fields()} == {"draft"}
