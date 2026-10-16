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
