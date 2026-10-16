"""Spec §7: the screener agrees with every cell of the adopted use table."""

import pytest

from portal_api.forms.definitions import load_definitions
from portal_api.forms.screener import run
from portal_api.ruleset import load_ruleset

RULESET = load_ruleset()
DEFS = load_definitions(RULESET)
TRACE_CODE = {d["district_key"]: (d["code"] if d["code"] != "SD" else f"SD-{d['name'].title()}")
              for d in RULESET.districts}
CASES = sorted(RULESET.cells.items())
# Built from the use table's own legend (permit_key), not from the engine's mapping,
# so a wrong mapping in the engine fails here.
APP_FOR_PERMIT_KEY = {"use": "use_permit", "residential_companion": "residential_companion",
                      "special": "special_permit", "expanded_use": "expanded_use"}


def _expected(cell):
    reviews = cell.get("reviews") or ([cell] if cell["code"] else [])
    return {APP_FOR_PERMIT_KEY[r["permit_key"]] for r in reviews}


@pytest.mark.parametrize("key,cell", CASES, ids=[f"{d}/{u}" for (d, u), _ in CASES])
def test_cell(key, cell):
    district_key, use_key = key
    code = TRACE_CODE[district_key]
    result = run({"project": ["use"], "use_key": use_key,
                  "property": {"district_codes": [code], "on_state_highway": False, "civic": False},
                  "building": {}, "division": {}}, RULESET, DEFS)
    expected = _expected(cell)
    assert {o["application"] for o in result["outcomes"]} == expected
    assert bool(result["not_listed"]) == (not expected)
