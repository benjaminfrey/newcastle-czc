from portal_api.forms.__main__ import review_sheet
from portal_api.forms.definitions import load_definitions
from portal_api.ruleset import load_ruleset


def test_the_sheet_lists_every_entry_with_its_approval_and_code_text():
    r = load_ruleset()
    defs = load_definitions(r)
    sheet = review_sheet(r, defs)
    ids = [*defs.applications, *(x.id for x in defs.rules), *(u.use_key for g in defs.groups for u in g.uses)]
    for i in ids:
        assert f"`{i}`" in sheet, i
    assert r.cite("8.10.b.1") in sheet
    assert sheet.count("Approved by Ben Frey, Planning Board chair, on 2026-10-20") == len(ids)


def test_the_sheet_quotes_each_uses_code_definition():
    r = load_ruleset()
    sheet = review_sheet(r, load_definitions(r))
    assert r.definitions["DISPATCH SERVICE"]["definition"] in sheet


def test_the_sheet_records_the_chairs_rulings():
    r = load_ruleset()
    defs = load_definitions(r)
    sheet = review_sheet(r, defs)
    assert "## The chair's rulings (2026-10-18)" in sheet
    assert "Questions from drafting" not in sheet
    rule = next(x for x in defs.rules if x.id == "addition-large")
    assert rule.ruling["text"] in sheet
    assert sheet.count("Ruling (Ben Frey, Planning Board chair, 2026-10-18)") >= 10


def test_the_sheet_shows_each_clock_in_plain_words_with_its_approval():
    from portal_api.forms.__main__ import review_sheet
    from portal_api.forms.definitions import load_definitions
    from portal_api.ruleset import load_ruleset
    r = load_ruleset()
    sheet = review_sheet(r, load_definitions(r))
    spp = sheet[sheet.index("### `small_project_plan`"):]
    assert ("- Applicants read, for `small_project_decision`: “The Code Enforcement Officer decides within 10 days "
            "of accepting your project.” — approved by Ben Frey, Planning Board chair, on 2026-10-28.") in spp
