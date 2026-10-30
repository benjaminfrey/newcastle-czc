import json
from pathlib import Path

import pytest

from portal_api.standards import (OverrideError, check, load_standards,
                                  missing_buildings_table, parse_matrix_cell, standards_for)


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


_D4_STORIES = {"district_key": "d4", "building": "Residential", "field": "total_stories",
               "qualifier": "max", "decided_by": "Test", "decided_at": "2026-10-30",
               "basis": "test"}


def _overrides(tmp_path: Path, *entries: dict) -> Path:
    (tmp_path / "standards_overrides.json").write_text(json.dumps({"overrides": list(entries)}))
    return tmp_path


def test_every_district_has_standards():
    assert len({s.district_key for s in load_standards()}) == 13


def test_a_checkable_setback():
    s = next(s for s in standards_for("d1") if s.field == "primary_building_placement.side_setback")
    assert (s.status, s.min, s.unit, s.provenance) == ("checkable", 15.0, "ft", "literal")
    assert check(s, 15) == "within" and check(s, 14.5) == "outside"


def test_a_range_is_checked_on_both_sides():
    s = next(s for s in standards_for("d6")
             if s.building == "Residential" and s.field == "total_stories")
    assert (s.status, s.min, s.max) == ("checkable", 2, 3)
    assert check(s, 1) == "outside" and check(s, 2) == "within" and check(s, 4) == "outside"


def test_bare_matrix_number_cannot_be_checked():
    s = next(s for s in standards_for("d4")
             if s.building == "Residential" and s.field == "total_stories")
    assert s.status == "needs_qualifier"
    assert check(s, 3) == "cannot_check" and check(s, 99) == "cannot_check"


def test_unresolved_footnote_cannot_be_checked():
    s = next(s for s in standards_for("d6") if s.field == "primary_building_placement.side_setback")
    assert s.status == "unresolved" and check(s, 3) == "cannot_check"


def test_districts_without_a_buildings_table():
    for key in ("sd-conserve", "sd-campus", "sd-marine"):
        assert standards_for(key)
        assert all(s.source == "dimension" for s in standards_for(key))
        assert "What dimensional standards" in missing_buildings_table(key)
    assert missing_buildings_table("d4") is None


def test_override_turns_a_bare_number_checkable(tmp_path):
    root = _overrides(tmp_path, _D4_STORIES)
    s = next(s for s in load_standards(root)
             if s.district_key == "d4" and s.building == "Residential" and s.field == "total_stories")
    assert (s.status, s.max, s.provenance) == ("checkable", 2, "override")


def test_override_without_provenance_is_refused(tmp_path):
    entry = {k: v for k, v in _D4_STORIES.items() if k != "basis"}
    with pytest.raises(OverrideError, match="basis"):
        load_standards(_overrides(tmp_path, entry))


def test_override_for_a_field_that_does_not_exist_is_refused(tmp_path):
    with pytest.raises(OverrideError, match="matches no"):
        load_standards(_overrides(tmp_path, {**_D4_STORIES, "field": "roof_colour"}))


def test_committed_overrides_are_empty():
    import portal_api.standards as m
    path = Path(m.__file__).parent / "standards_overrides.json"
    assert json.loads(path.read_text()) == {"overrides": []}
