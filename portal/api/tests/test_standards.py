import pytest

from portal_api.standards import parse_matrix_cell


@pytest.mark.parametrize("label,raw,status,lo,hi,unit", [
    ("Total Stories", "1 max.", "checkable", None, 1, "stories"),
    ("Total Stories", "2 min. - 3 max.", "checkable", 2, 3, "stories"),
    ("Total Stories", "2", "needs_qualifier", None, None, "stories"),
    ("Building Width", "60 ft", "needs_qualifier", None, None, "ft"),
    ("Building Floor Area", "8,000 sf", "needs_qualifier", None, None, "sf"),
    ("Number of Units", "-", "not_established", None, None, None),
    ("Permitting Authority", "Planning Board", "not_a_number", None, None, None),
])
def test_matrix_cells(label, raw, status, lo, hi, unit):
    p = parse_matrix_cell(label, raw)
    assert (p.status, p.min, p.max, p.unit) == (status, lo, hi, unit)


def test_unitless_area_needs_a_unit():
    p = parse_matrix_cell("Building Floor Area", "12,000")
    assert p.status == "needs_unit" and p.min is None and p.max is None
    assert "unit" in p.note


def test_a_cell_it_cannot_read_is_reported_not_dropped():
    p = parse_matrix_cell("Building Width", "about sixty")
    assert p.status == "unresolved" and p.note
