from portal_api.standards_audit import render_audit


def test_audit_groups_bare_numbers_into_one_question_per_row():
    md = render_audit("2026-10-30")
    assert md.count("Is Building Width in the Permitted Buildings tables a maximum?") == 1
    assert "Total Stories" in md


def test_audit_lists_districts_without_a_buildings_table():
    md = render_audit("2026-10-30")
    for name in ("SD - Conservation", "SD - Campus", "SD - Marine"):
        assert name in md


def test_audit_quotes_every_shoreland_mention():
    md = render_audit("2026-10-30")
    assert md.count("shoreland") + md.count("Shoreland") >= 8   # 8 nodes mention it today


def test_audit_shows_no_bound_for_a_bare_number():
    md = render_audit("2026-10-30")
    row = next(l for l in md.splitlines() if "| Residential | Total Stories | 2 |" in l)
    assert "needs_qualifier" in row and "max" not in row.split("| 2 |")[1]
