"""The browser's applicability rules (web/src/forms/applicability.ts) and the API's
(forms/answers.py) give the same answers on one shared fixture form."""

import json
from pathlib import Path

import pytest
import yaml

from portal_api.forms.answers import Current, applicable, missing, printed
from portal_api.forms.formdefs import load_form
from portal_api.ruleset import load_ruleset

FIXTURES = json.loads((Path(__file__).resolve().parents[2] / "web/src/forms/form-fixtures.json").read_text())


@pytest.fixture(scope="module")
def form(tmp_path_factory):
    root = tmp_path_factory.mktemp("forms")
    (root / "fixture-form.v1.yaml").write_text(yaml.safe_dump(FIXTURES["form"]))
    return load_form("fixture_form", 1, load_ruleset(), root=root)


@pytest.mark.parametrize("case", FIXTURES["cases"], ids=[c["name"] for c in FIXTURES["cases"]])
def test_shared_form_fixture(form, case):
    raw = case["current"]
    cur = Current(answers={(f, i): v for f, i, v in raw["answers"]}, items=[tuple(i) for i in raw["items"]],
                  property=raw["property"], account=raw["account"])
    assert [[f.id, i] for _, f, i in applicable(form, cur)] == case["applicable"]
    assert [[f, i] for f, i in missing(form, cur)] == case["missing"]
    assert [[s.id, i, [[f.id, v] for f, v in rows]] for s, i, rows in printed(form, cur)] == case["printed"]
