from portal_api.forms.__main__ import review_sheet
from portal_api.forms.definitions import load_definitions
from portal_api.ruleset import load_ruleset


def test_the_sheet_lists_every_draft_with_its_code_text():
    r = load_ruleset()
    defs = load_definitions(r)
    sheet = review_sheet(r, defs)
    for d in defs.drafts():
        assert f"`{d.id}`" in sheet, d.id
    assert r.cite("8.10.b.1") in sheet
    assert "status: approved" in sheet and "approved_by:" in sheet


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
