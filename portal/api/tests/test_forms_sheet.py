from portal_api.forms.forms_sheet import condition_words, forms_sheet
from portal_api.forms.formdefs import FORM_KEYS, latest_version, load_form
from portal_api.ruleset import load_ruleset


def forms():
    r = load_ruleset()
    return r, [load_form(k, latest_version(k), r) for k in FORM_KEYS]


def test_sheet_lists_every_field_of_every_form():
    r, fs = forms()
    sheet = forms_sheet(r, fs)
    for form in fs:
        assert f"## {form.official_title}" in sheet
        for s, f in form.fields():
            assert f"`{f.id}`" in sheet, f.id
    assert "Cover Sheet (part of every application)" in sheet


def test_sheet_quotes_code_text():
    r, fs = forms()
    sheet = forms_sheet(r, fs)
    assert r.cite("3.12.d.1") in sheet and r.cite("5.7.c.2") in sheet


def test_sheet_renders_conditions_in_words():
    r, fs = forms()
    up = next(f for f in fs if f.key == "use_permit")
    sp = next(f for f in fs if f.key == "small_project_plan")
    ep = next(f for f in fs if f.key == "entrance_permit")
    owner = next(s for s in up.sections if s.id == "owner")
    assert condition_words(up, owner.show_if) == "“Applicant is the Property Owner” is No"
    _, f = sp.field("floor_height_2")
    assert condition_words(sp, f.show_if) == "“Total number of stories” (this building) is 2 or more"
    _, f = sp.field("component_roof_style")
    assert condition_words(sp, f.show_if) == "“Component” (this component) is Addition or Garage (attached)"
    _, f = ep.field("mainedot_permit")
    assert condition_words(ep, f.show_if) == "the lot is not known to be off State roads (on a State road, or unknown)"
    assert condition_words(up, {"between": ["x", 1]}) == "`{'between': ['x', 1]}`"


def test_sheet_records_the_approvals_and_the_chairs_rulings():
    r, fs = forms()
    sheet = forms_sheet(r, fs)
    assert "**Draft — awaiting the chair's approval.**" not in sheet and "**Every entry is approved.**" in sheet
    assert "- Approved by Ben Frey, Planning Board chair, on 2026-10-28." in sheet
    decisions = sheet[sheet.index("## The chair's decisions (2026-10-28)"):sheet.index("## Cover Sheet")]
    assert decisions.count("\n") > 11 and "**A building's name.** Optional" in decisions
    assert "## The chair's rulings (2026-10-23)" in sheet
    assert "## Questions for the chair" not in sheet
    for words in ("Optional", "only when the work includes a building", "Standard Met?", "Special Use Building",
                  "Name", "complete"):
        assert words in sheet, words
    sp = next(f for f in fs if f.key == "small_project_plan")
    building = next(s for s in sp.sections if s.id == "building")
    assert "Printed and asked only when (“Type of project” includes New building or accessory building)" in sheet
    assert building.show_if is not None



def test_sheet_shows_steps_and_controls():
    r, fs = forms()
    sheet = forms_sheet(r, fs)
    assert "- Step: Your lot" in sheet
    assert "- Control: switch (starts on)" in sheet
    assert "- Control: slider" in sheet
    assert "- Card: asked with the others on `walls` (compass drawing)" in sheet
    assert "- Card: asked with the others on `deed`" in sheet
    assert "Add options" not in sheet and "- Pages:" not in sheet


def test_sheet_prints_cards_icons_and_copies():
    r, fs = forms()
    sheet = forms_sheet(r, fs)
    sp = sheet[sheet.index("## Small Project Plan"):]
    name = sp[sp.index("(`building_name`)"):]
    assert "- Card: asked with the others on `about`" in name[:name.index("#### ", 5)]
    work = sp[sp.index("(`work_kinds`)"):]
    assert "- Source: worked out from the project's parts (never asked) — `work_kinds`" in work  # projects brief §4
    roof = sp[sp.index("(`roof_style`)"):]
    assert "- Copied by “Copy Building 1”" in roof[:roof.index("#### ", 5)]


def test_sheet_prints_short_names():
    r, fs = forms()
    sheet = forms_sheet(r, fs)
    width = sheet[sheet.index("(`mass_width`)"):]
    assert "- Short name on its card: “Width”" in width[:width.index("#### ", 5)]


def test_sheet_lists_the_parts_and_the_project_questions():
    from portal_api.forms.parts import load_parts
    r = load_ruleset()
    fs = [load_form(k, latest_version(k), r) for k in (*FORM_KEYS, "project_questions")]
    sheet = forms_sheet(r, fs, load_parts())
    assert "## Project questions" in sheet and "`homes_last_5_years`" in sheet
    parts = sheet[sheet.index("## Parts (`parts.yaml`)"):]
    assert "### A new building (`building`)" in parts
    assert "- Asks: Small Project Plan Application — `building`, `building_location`" in parts
    assert "- Sets for the rules: `building.gross_floor_area_sf` from `floor_area`" in parts
    assert "- **Draft" not in parts
    assert parts.count("- Approved by Ben Frey, Planning Board chair, on 2026-10-28.") == 9  # eight parts and About the work
