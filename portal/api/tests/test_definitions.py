import pytest

from portal_api.forms.definitions import DefinitionError, load_definitions, validate_entries
from portal_api.ruleset import load_ruleset

VERDICT_WORDS = ("approved", "denied", "compliant", "meets", "fails", "violates")


@pytest.fixture(scope="module")
def defs():
    return load_definitions(load_ruleset())


def test_every_use_is_in_exactly_one_group(defs):
    seen = [u.use_key for g in defs.groups for u in g.uses]
    assert sorted(seen) == sorted(u["use_key"] for u in load_ruleset().uses)
    assert len(seen) == len(set(seen))


def test_every_use_has_its_code_definition(defs):
    r = load_ruleset()
    for g in defs.groups:
        for u in g.uses:
            assert u.definition_key in r.definitions, u.use_key


def test_every_citation_resolves(defs):
    r = load_ruleset()
    for x in [*defs.applications.values(), *defs.rules]:
        assert r.cite(x.cite)


def test_every_clock_exists(defs):
    r = load_ruleset()
    for a in defs.applications.values():
        for k in a.clock_keys:
            assert k in r.clocks


def test_rules_reference_known_applications(defs):
    for rule in defs.rules:
        if rule.outcome.get("kind") == "application":
            assert rule.outcome["application"] in defs.applications


def test_no_verdict_words_in_applicant_text(defs):
    texts = [a.plain for a in defs.applications.values()]
    texts += [r.outcome.get("text", "") for r in defs.rules]
    texts += [u.example for g in defs.groups for u in g.uses] + [g.plain for g in defs.groups]
    for t in texts:
        assert not any(w in t.lower() for w in VERDICT_WORDS), t


def test_every_entry_is_approved_by_the_chair(defs):
    # The chair approved every entry in chat on 2026-10-20 ("i approve the screener entries").
    assert defs.drafts() == []
    entries = [*defs.applications.values(), *defs.rules, *(u for g in defs.groups for u in g.uses)]
    for e in entries:
        assert (e.status, e.approved_by, str(e.approved_on)) == ("approved", "Ben Frey, Planning Board chair", "2026-10-20"), e


def test_a_bad_condition_names_the_entry():
    with pytest.raises(DefinitionError, match="rules.yaml: bad-rule"):
        validate_entries("rules.yaml", [{"id": "bad-rule", "order": 1, "when": {"between": ["a", 1]},
                                         "outcome": {"kind": "note", "text": "x"}, "cite": "8.10.b.1",
                                         "status": "draft"}], load_ruleset())


def test_approval_needs_who_and_when():
    with pytest.raises(DefinitionError, match="approved_by"):
        validate_entries("rules.yaml", [{"id": "r", "order": 1, "when": {"all": []},
                                         "outcome": {"kind": "note", "text": "x"}, "cite": "8.10.b.1",
                                         "status": "approved"}], load_ruleset())


def test_an_unresolvable_citation_names_the_entry():
    with pytest.raises(DefinitionError, match="rules.yaml: r.*8.99"):
        validate_entries("rules.yaml", [{"id": "r", "order": 1, "when": {"all": []},
                                         "outcome": {"kind": "note", "text": "x"}, "cite": "8.99.a.1",
                                         "status": "draft"}], load_ruleset())
