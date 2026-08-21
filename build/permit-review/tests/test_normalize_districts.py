"""Tests ruleset_build/build_districts.py against CONTRACT.md §4.1/§4.2.

Offline, no network, no LLM, no PII — reads the real, committed
source/article-02-data.json (repo baseline, read-only) and either the real,
committed overrides/dimension-qualifiers.json (whose two entries —
DECISIONS-NEEDED.md D-0001/D-0002 — were resolved by the Planning Board Chair
on 2026-08-21) or a throwaway tmp_path copy (to exercise the fail-loud path on
synthetic unresolved entries without touching the real, human-owned overrides
file).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.build_districts import (  # noqa: E402
    AmbiguousDimension,
    build_districts,
    normalize_dimension,
)
from ruleset_build.slugs import DISTRICT_KEYS  # noqa: E402

REPO_ROOT = APP_ROOT.parent.parent
SRC = REPO_ROOT / "source" / "article-02-data.json"
REAL_OVERRIDES = APP_ROOT / "overrides" / "dimension-qualifiers.json"

NULL_MATRIX_DISTRICT_KEYS = {"sd-conserve", "sd-campus", "sd-marine"}


def _resolved_overrides_path(tmp_path: Path) -> Path:
    """A tmp_path copy of the real overrides file with the two currently-open
    blocking entries (D-0001, D-0002) filled in, so tests can exercise the
    full happy path without writing a fake resolution into the real,
    human-owned overrides/dimension-qualifiers.json."""
    doc = json.loads(REAL_OVERRIDES.read_text(encoding="utf-8"))
    doc = copy.deepcopy(doc)
    for key in (
        "sd-historic:primary_building_placement.frontage_zone_setback",
        "sd-marine:building_placement.frontage_zone_setback",
    ):
        entry = doc["entries"][key]
        entry["qualifier"] = "min"
        entry["decided_by"] = "test-fixture"
        entry["decided_at"] = "2026-08-20"
        entry["basis"] = "synthetic resolution for test coverage only — not a real Board decision"
    out = tmp_path / "dimension-qualifiers.resolved.json"
    out.write_text(json.dumps(doc), encoding="utf-8")
    return out


@pytest.fixture()
def resolved_overrides(tmp_path: Path) -> Path:
    return _resolved_overrides_path(tmp_path)


@pytest.fixture()
def districts_doc(resolved_overrides: Path) -> dict:
    return build_districts(SRC, resolved_overrides, "adopted")


# ---------------------------------------------------------------------------
# The REAL overrides file — D-0001/D-0002 resolved by a human (2026-08-21)
# ---------------------------------------------------------------------------
#
# This test previously asserted the OPPOSITE: that the committed overrides file
# was unresolved and the build raised AmbiguousDimension. That was correct while
# D-0001/D-0002 were OPEN. Both were resolved on 2026-08-21 by the Planning Board
# Chair (frontage zone setback "20 ft" = a MINIMUM), so the assertion is inverted
# here rather than deleted.
#
# The fail-loud guarantee it used to cover is NOT lost: it is covered
# independently, and without depending on the real file's current state, by
# test_unqualified_value_with_no_override_entry_at_all_raises and
# test_unresolved_override_entry_still_raises below.


def test_real_overrides_are_resolved_by_a_human_not_by_the_machine() -> None:
    """D-0001/D-0002 are RESOLVED, so the real build must now succeed — and the
    resolution must carry human provenance. CONTRACT.md §4.2.4: a qualifier
    alone never resolves an entry; decided_by and basis must both be present, so
    a machine-written qualifier can never satisfy this test."""
    doc = build_districts(SRC, REAL_OVERRIDES, "adopted")

    seen = {}
    for district in doc["districts"]:
        for dim in district["dimensions"]:
            if "frontage_zone_setback" in dim["field_key"] and district[
                "district_key"
            ] in ("sd-historic", "sd-marine"):
                seen[district["district_key"]] = dim

    assert set(seen) == {"sd-historic", "sd-marine"}, "both D-0001/D-0002 fields must exist"

    for district_key, dim in seen.items():
        assert dim["raw"] == "20 ft"
        assert dim["unresolved"] is False, district_key
        constraints = dim["constraints"]
        assert len(constraints) == 1, district_key
        (constraint,) = constraints
        assert constraint["qualifier"] == "min", district_key
        assert constraint["value"] == 20.0, district_key
        assert constraint["unit"] == "ft", district_key
        # source="override" is what makes the provenance reach the printed
        # worksheet — a value derived any other way would not be traceable to
        # the person who decided it.
        assert constraint["source"] == "override", district_key
        assert any("decided_by=" in n and "basis=" in n for n in dim["notes"]), district_key


def test_real_overrides_entries_carry_human_decision_fields() -> None:
    """Guards the file itself, not just the build: if anyone (or any script)
    ever sets a qualifier without recording WHO decided it and on what basis,
    that is a machine-made legal determination and must fail here."""
    entries = json.loads(REAL_OVERRIDES.read_text())["entries"]
    assert entries, "overrides file must not be empty"
    for key, entry in entries.items():
        assert entry["qualifier"] in ("min", "max"), key
        assert entry["decided_by"], key
        assert entry["decided_at"], key
        assert entry["basis"], key


def test_unqualified_value_with_no_override_entry_at_all_raises() -> None:
    """A field/district combination with NO entry whatsoever in overrides
    (not even a null one) must also raise, not silently pass through."""
    with pytest.raises(AmbiguousDimension):
        normalize_dimension(
            "some-district", "lot_dimensions", "Some Field", "42 ft", overrides={}
        )


def test_unresolved_override_entry_still_raises() -> None:
    """qualifier: null is NOT a resolution (CONTRACT.md §4.2.4) even when an
    entry exists — only a non-null qualifier + decided_by + basis resolves it."""
    overrides = {
        "d1:lot_dimensions.width": {
            "qualifier": None,
            "decided_by": None,
            "basis": None,
        }
    }
    with pytest.raises(AmbiguousDimension):
        normalize_dimension("d1", "lot_dimensions", "Width", "100 ft", overrides)


# ---------------------------------------------------------------------------
# The happy path — resolved overrides, full 13-district build
# ---------------------------------------------------------------------------


def test_all_13_districts_parse(districts_doc: dict) -> None:
    assert districts_doc["counts"]["districts"] == 13
    assert len(districts_doc["districts"]) == 13


def test_district_keys_are_unique(districts_doc: dict) -> None:
    keys = [d["district_key"] for d in districts_doc["districts"]]
    assert keys == DISTRICT_KEYS
    assert len(set(keys)) == 13


def test_d1_primary_frontage_line_length_normalizes_to_250_ft_min(districts_doc: dict) -> None:
    d1 = next(d for d in districts_doc["districts"] if d["district_key"] == "d1")
    dim = next(
        dim
        for dim in d1["dimensions"]
        if dim["field_key"] == "lot_dimensions.primary_frontage_line_length"
    )
    assert dim["raw"] == "250 ft min"
    assert dim["applicability"] == "established"
    assert dim["unit"] == "ft"
    assert dim["constraints"] == [
        {"qualifier": "min", "value": 250.0, "unit": "ft", "footnote_ref": None, "source": "literal"}
    ]
    assert dim["unresolved"] is False


def test_d1_lot_dimensions_full_shape(districts_doc: dict) -> None:
    """The exact D1 LOT DIMENSIONS output: Width 100 ft min, Depth n/a,
    Lot Area n/a, Primary Frontage Line Length 250 ft min."""
    d1 = next(d for d in districts_doc["districts"] if d["district_key"] == "d1")
    lot_dims = [dim for dim in d1["dimensions"] if dim["panel_key"] == "lot_dimensions"]
    by_label = {dim["label"]: dim for dim in lot_dims}

    assert set(by_label) == {"Width", "Depth", "Lot Area", "Primary Frontage Line Length"}

    assert by_label["Width"]["constraints"] == [
        {"qualifier": "min", "value": 100.0, "unit": "ft", "footnote_ref": None, "source": "literal"}
    ]
    assert by_label["Width"]["applicability"] == "established"

    for label in ("Depth", "Lot Area"):
        assert by_label[label]["applicability"] == "not_established"
        assert by_label[label]["constraints"] == []
        assert by_label[label]["unit"] is None

    assert by_label["Primary Frontage Line Length"]["constraints"][0]["value"] == 250.0


def test_three_null_matrix_districts_handled_as_finding(districts_doc: dict) -> None:
    by_key = {d["district_key"]: d for d in districts_doc["districts"]}
    for key in NULL_MATRIX_DISTRICT_KEYS:
        d = by_key[key]
        assert d["building_matrix"] is None
        absent = d["building_matrix_absent"]
        assert absent is not None
        assert absent["unresolved"] is True
        assert "does not establish building dimensional standards" in absent["finding"]
        assert d["display_name"] in absent["board_question"]

    # every other district has a real matrix, not an absence finding
    for d in districts_doc["districts"]:
        if d["district_key"] in NULL_MATRIX_DISTRICT_KEYS:
            continue
        assert d["building_matrix"] is not None
        assert d["building_matrix_absent"] is None


def test_percent_dimension_normalizes_with_min_max() -> None:
    """'20% min, 80% max' -> {min:0.20,max:0.80,unit:'pct'} (CONTRACT.md §4.2.2's
    grammar coverage claim). This exact raw string occurs in the source only
    inside DESIGN STANDARDS ("Windows & Doors"), which is a PROSE panel
    (§4.1.3) — so normalize_dimension is exercised directly here rather than
    through build_districts, which correctly never parses it (see
    test_design_standards_percent_values_stay_verbatim_in_panels below)."""
    dim = normalize_dimension(
        "d2", "design_standards", "Windows & Doors", "20% min, 80% max", overrides={}
    )
    assert dim["applicability"] == "established"
    assert dim["unit"] == "pct"
    values = {(c["qualifier"], c["value"]) for c in dim["constraints"]}
    assert values == {("min", 0.20), ("max", 0.80)}


def test_design_standards_percent_values_stay_verbatim_in_panels(districts_doc: dict) -> None:
    """DESIGN STANDARDS is prose (§4.1.3): 'Windows & Doors' = '20% min, 80%
    max' is carried through panels[] untouched and never appears in
    dimensions[] (which is scoped to the four §4.1.3 panel titles only)."""
    d2 = next(d for d in districts_doc["districts"] if d["district_key"] == "d2")
    design_panel = next(p for p in d2["panels"] if p["title"] == "DESIGN STANDARDS")
    body_by_label = dict(design_panel["body"])
    assert body_by_label["Windows & Doors"] == "20% min, 80% max"
    assert all(dim["raw"] != "20% min, 80% max" for dim in d2["dimensions"])


def test_footnote_only_dimensions_are_unresolved_not_blocking(districts_doc: dict) -> None:
    """'1000 ft min (1)' and '0 ft min (4) , 5 ft max (5)' are known (footnote
    text missing, D-0003/D-0004) — resolvable numbers, unresolved=True, and
    they do NOT raise."""
    flagged = [
        dim
        for d in districts_doc["districts"]
        for dim in d["dimensions"]
        if dim["footnote_refs"]
    ]
    assert flagged, "expected at least one footnote-flagged dimension"
    for dim in flagged:
        assert dim["unresolved"] is True
        assert dim["notes"]


def test_use_standards_items_coerced_to_uniform_shape(districts_doc: dict) -> None:
    """Gotcha 2: bare strings (most districts) and {'text','sub'} dicts (D1,
    SD-Rural Highway, SD-Campus) both normalize to {'text': str, 'sub': list}."""
    saw_any_items = False
    for d in districts_doc["districts"]:
        for item in d["use_standards"]["items"]:
            saw_any_items = True
            assert set(item.keys()) == {"text", "sub"}
            assert isinstance(item["text"], str)
            assert isinstance(item["sub"], list)
    assert saw_any_items

    # SD-Conservation and SD-Fabrication have empty use_standards (gotcha 2)
    by_key = {d["district_key"]: d for d in districts_doc["districts"]}
    assert by_key["sd-conserve"]["use_standards"]["items"] == []
    assert by_key["sd-fab"]["use_standards"]["items"] == []


def test_d1_two_design_standards_panels_get_key_suffix(districts_doc: dict) -> None:
    """D1's right[] has two panels titled DESIGN STANDARDS; the second gets
    panel_key 'design_standards_2' (CONTRACT.md §4.1.2)."""
    d1 = next(d for d in districts_doc["districts"] if d["district_key"] == "d1")
    design_panels = [p for p in d1["panels"] if p["title"] == "DESIGN STANDARDS"]
    assert len(design_panels) == 2
    assert [p["panel_key"] for p in design_panels] == ["design_standards", "design_standards_2"]


def test_description_and_purpose_lifted_to_top_level(districts_doc: dict) -> None:
    d1 = next(d for d in districts_doc["districts"] if d["district_key"] == "d1")
    assert isinstance(d1["description"], str) and d1["description"]
    assert isinstance(d1["purpose"], list) and len(d1["purpose"]) == 3
    # still present verbatim in panels[] too
    assert any(p["title"] == "DESCRIPTION" for p in d1["panels"])
    assert any(p["title"] == "PURPOSE" for p in d1["panels"])
