"""The adopted->draft article map must keep describing the two rulesets.

The invariant: mapping an adopted article number lands on the draft article
with the SAME NAME. These tests pose a post-adoption world by injection rather
than by building a ruleset, so they stay offline and fast.
"""
from app import renum_check
from app.citation import RENUM_ADOPTED_TO_DRAFT

# The 2020 Code as the adopted ruleset holds it today: eight articles.
ADOPTED_2020 = {
    1: "GENERAL STANDARDS", 2: "DISTRICT STANDARDS", 3: "SITE STANDARDS",
    4: "BUILDING STANDARDS", 5: "DESIGN STANDARDS", 6: "USE STANDARDS",
    7: "ADMINISTRATION", 8: "DEFINITIONS",
}
# The draft, and what the adopted ruleset becomes once the draft is adopted:
# nine articles, Thoroughfares inserted at 3.
NINE = {
    1: "General Standards", 2: "District Standards", 3: "Thoroughfares",
    4: "Site Standards", 5: "Building Standards", 6: "Design Standards",
    7: "Use Standards", 8: "Administration", 9: "Definitions",
}
SHIFTED = {1: 1, 2: 2, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8, 8: 9}
IDENTITY = {n: n for n in range(1, 10)}


# --- the real, shipped state -------------------------------------------------

def test_the_shipped_map_matches_the_shipped_rulesets():
    assert renum_check.problems() == []


def test_the_shipped_map_is_still_the_shifted_one():
    """Pins the premise: while the adopted Code is the 2020 eight-article
    version, the map is a shift, not identity. When this fails, the adoption
    happened and the rest of the rollover is due."""
    assert RENUM_ADOPTED_TO_DRAFT == SHIFTED


def test_definitions_is_found_even_though_the_draft_splits_it_out():
    """The draft keeps Definitions in definitions.json, not articles.json.
    Reading only articles.json made this check cry wolf about Article 9."""
    draft = renum_check.draft_articles()
    assert 9 in draft
    assert renum_check._norm(draft[9]) == "definitions"


# --- the failure the guard exists for ----------------------------------------

def test_a_stale_map_after_adoption_is_caught():
    """The adopted ruleset is rebuilt from the adopted Code (nine articles) but
    nobody reset the map. Every article from 3 on now points at the wrong one."""
    found = renum_check.problems(renum=SHIFTED, adopted=NINE, draft=NINE)
    assert found, "a stale post-adoption map produced no complaint"
    assert any("Thoroughfares" in p and "Site Standards" in p for p in found)


def test_resetting_the_map_too_early_is_caught():
    """The other direction: identity while the adopted Code is still 2020's.
    Adopted Article 3 (Site Standards) would resolve to draft Thoroughfares."""
    found = renum_check.problems(renum=IDENTITY, adopted=ADOPTED_2020, draft=NINE)
    assert found, "an early reset produced no complaint"
    assert any("SITE STANDARDS" in p and "Thoroughfares" in p for p in found)


def test_the_correct_post_adoption_map_passes():
    """Identity, once the adopted ruleset really is the nine-article Code."""
    assert renum_check.problems(renum=IDENTITY, adopted=NINE, draft=NINE) == []


def test_an_unmapped_adopted_article_is_caught():
    found = renum_check.problems(
        renum={k: v for k, v in SHIFTED.items() if k != 8},
        adopted=ADOPTED_2020, draft=NINE)
    assert any("has no entry" in p for p in found)


def test_a_map_pointing_off_the_end_is_caught():
    found = renum_check.problems(
        renum={**SHIFTED, 8: 12}, adopted=ADOPTED_2020, draft=NINE)
    assert any("does not exist" in p for p in found)


# --- names compare by words, not formatting ----------------------------------

def test_case_and_punctuation_do_not_matter():
    """The two rulesets render the same article differently by design --
    'SITE STANDARDS' against 'Site Standards'. That is not a mismatch."""
    assert renum_check.problems(
        renum=IDENTITY,
        adopted={1: "GENERAL   STANDARDS"},
        draft={1: "General Standards"}) == []


# --- wiring ------------------------------------------------------------------

def test_selftest_runs_the_check():
    """Otherwise the module is a test-only ornament and the guard never fires
    where an operator would see it."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent / "app" / "main.py").read_text()
    assert "renum_check" in src
    assert "12. RENUM_ADOPTED_TO_DRAFT" in src


def test_run_returns_zero_on_the_shipped_state():
    assert renum_check.run(quiet=True) == 0
