"""Article 2's batch (library plan 1, task 9): every standard the guide checks has its entry."""

import yaml

from portal_api.guide.content import DIR as GUIDE_DIR
from portal_api.library import load_library
from portal_api.library.render import render, spec_key
from portal_api.ruleset import load_ruleset

LIB = load_library()
A2 = [e for e in LIB.entries.values() if e.batch == "article-02"]
DISTRICTS = [(d["district_key"], list((d.get("building_matrix") or {}).get("cols") or [None]))
             for d in load_ruleset().districts]


def test_every_standard_the_guide_checks_has_an_article_2_entry():
    turns = yaml.safe_load((GUIDE_DIR / "turns.yaml").read_text())
    claimed = {k: e.id for e in A2 for k in e.standards}
    for t in turns:
        if t.get("standard"):
            assert spec_key(t["standard"]) in claimed, t["id"]


def test_every_article_2_entry_claims_a_district_standard():
    assert len(A2) == 18
    assert all(e.kind == "standard" and e.standards for e in A2)


def test_every_article_2_entry_renders_for_some_district():
    for e in A2:
        assert any(render(e, d, b) for d, bs in DISTRICTS for b in bs), e.id


def test_article_2_entries_are_drafts_with_their_open_questions():
    assert {e.status for e in A2} == {"draft"}
    assert len(LIB.open_questions["article-02"]) == 5


def test_article_2_reads_plainly():
    assert not {i: f for i, f in LIB.flags.items() if i in {e.id for e in A2}}
