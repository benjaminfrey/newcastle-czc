import json
from pathlib import Path

import pytest

from portal_api.forms.expr import evaluate, validate

FIXTURES = json.loads((Path(__file__).resolve().parents[2] / "web/src/forms/expr-fixtures.json").read_text())


@pytest.mark.parametrize("case", FIXTURES, ids=[c["name"] for c in FIXTURES])
def test_shared_fixture(case):
    if case.get("invalid"):
        with pytest.raises(ValueError):
            validate(case["expr"])
        return
    validate(case["expr"])
    assert evaluate(case["expr"], case["data"]) == case["expect"]


@pytest.mark.parametrize("bad", [
    {"between": ["a", 1]}, {"eq": ["a"]}, {"all": {"eq": ["a", 1]}}, {"gt": ["a", "x"]},
    {"eq": ["a", 1], "ne": ["a", 2]}, {"known": 3}, {"oneof": ["a", "x"]},
])
def test_malformed_conditions_are_refused(bad):
    with pytest.raises(ValueError):
        validate(bad)
