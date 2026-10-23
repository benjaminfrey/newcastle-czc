import json
from pathlib import Path

import pytest

from portal_api.forms.expr import shown

FIXTURES = json.loads((Path(__file__).resolve().parents[2] / "web/src/forms/applicability-fixtures.json").read_text())


@pytest.mark.parametrize("case", FIXTURES, ids=[c["name"] for c in FIXTURES])
def test_shared_shown_fixture(case):
    assert shown(case["show_if"], case["data"]) is case["shown"]
