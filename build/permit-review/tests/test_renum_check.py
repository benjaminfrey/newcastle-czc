"""The adopted->draft article map must keep describing the two rulesets.

The invariant: mapping an adopted article number lands on the draft article
with the SAME NAME. These tests pose a post-adoption world by injection rather
than by building a ruleset, so they stay offline and fast.
"""
from app import renum_check
from app.citation import RENUM_ADOPTED_TO_DRAFT, RENUM_V1_0_TO_DRAFT, SCHEME_TO_DRAFT

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


def test_the_2020_map_stays_shifted_forever():
    """The 2020 Code was superseded on September 14, 2026, but decided cases
    cite it. Its map is a fact about that document and must never be reset --
    resetting it would renumber those cases' citations."""
    assert RENUM_ADOPTED_TO_DRAFT == SHIFTED


def test_the_v1_0_map_is_identity():
    """CZC v1.0, adopted September 14, 2026, IS the nine-article numbering."""
    assert RENUM_V1_0_TO_DRAFT == IDENTITY
    assert SCHEME_TO_DRAFT["adopted-v1.0"] == IDENTITY


def test_every_binding_ruleset_on_disk_is_checked_through_its_own_map():
    keys = {k: m["article_scheme"] for k, m in renum_check.binding_rulesets()}
    assert keys == {"adopted": "adopted", "adopted-v1.0": "adopted-v1.0"}
    assert renum_check.ruleset_articles("adopted-v1.0")[3] == "Thoroughfares"
    assert renum_check._norm(renum_check.ruleset_articles("adopted")[3]) == "site standards"


def test_the_code_in_force_maps_by_identity():
    from app.rulesets import current_binding_key
    key = current_binding_key()
    manifest = dict(renum_check.binding_rulesets())[key]
    assert key == "adopted-v1.0"
    assert SCHEME_TO_DRAFT[manifest["article_scheme"]] == IDENTITY


def test_a_binding_ruleset_with_no_map_is_caught():
    """A future adoption whose ruleset was built but whose scheme was never
    added to SCHEME_TO_DRAFT: its citations cannot be numbered at all."""
    found = renum_check.edition_problems("adopted-v9.0", {"article_scheme": "adopted-v9.0"}, NINE, NINE)
    assert found and "no adopted-Code map" in found[0]


def test_a_nine_article_code_read_through_the_2020_map_is_caught():
    found = renum_check.edition_problems("adopted-v1.0", {"article_scheme": "adopted"}, NINE, NINE)
    assert any("Thoroughfares" in p and "Site Standards" in p for p in found)


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
    assert "12. every adopted Code's article map matches the draft by name" in src


def test_run_returns_zero_on_the_shipped_state():
    assert renum_check.run(quiet=True) == 0
