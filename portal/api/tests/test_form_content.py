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
                           "Name of other architectural component", "Building attached to", "Garage attached or detached",
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
                assert f.label.rstrip().endswith("?") or f.type in ("upload", "point"), f.id
