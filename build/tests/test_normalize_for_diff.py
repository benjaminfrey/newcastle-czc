# build/tests/test_normalize_for_diff.py
"""Normalisation rules for the baseline redline.

Each rule gets TWO tests: it suppresses the cosmetic difference, AND a real
change of the same shape still survives. The second test is the point. A
normaliser that quietly eats a real amendment produces a redline that is
confidently wrong, and nobody reading it can tell.
"""
import sys
from pathlib import Path

BUILD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUILD))

import adoption_map  # noqa: E402
import normalize_for_diff as nz  # noqa: E402

AMAP = adoption_map.load()


def norm_old(t):
    return nz.normalize(t, amap=AMAP, is_baseline_side=True)


def norm_new(t):
    return nz.normalize(t, amap=AMAP, is_baseline_side=False)


# --- Rule 1: heading letter case -------------------------------------------

def test_heading_case_difference_is_suppressed():
    assert norm_old("### A. PURPOSE") == norm_new("### a. PURPOSE")


def test_but_a_changed_heading_WORD_still_differs():
    assert norm_old("### A. PURPOSE") != norm_new("### a. APPLICABILITY")


def test_case_normalisation_does_not_touch_body_text():
    """Only the heading's leading letter is lowered. Body prose keeps its case,
    including defined terms like Driveway and Thoroughfare."""
    body = "1. A Driveway serves no more than two Dwellings."
    assert norm_new(body) == body


# --- Rule 2: cross-reference renumbering ------------------------------------

def test_renumbering_is_suppressed_on_the_baseline_side_only():
    assert norm_old("See Article 7.") == norm_new("See Article 8.")


def test_but_a_reference_to_a_genuinely_different_article_still_differs():
    assert norm_old("See Article 7.") != norm_new("See Article 5.")


def test_the_new_side_is_never_renumbered():
    """Renumbering maps baseline->current. Applying it to the current side too
    would double-shift and silently corrupt every reference."""
    assert norm_new("See Article 7.") == "See Article 7."


# --- Rule 4: table-number renumbering ---------------------------------------

def test_table_number_renumbering_is_suppressed_all_caps():
    assert norm_old("TABLE 6.1 DESIGN STANDARDS BY DISTRICT") == \
        norm_new("TABLE 7.1 DESIGN STANDARDS BY DISTRICT")


def test_table_number_renumbering_is_suppressed_title_case():
    assert norm_old("See Table 4.2 Site Lumens.") == norm_new("See Table 5.2 Site Lumens.")


def test_table_number_renumbering_is_suppressed_lowercase():
    """The real case found in the corpus: article-06-design-standards.md's
    baseline reads 'table 5.1 Design Standards By District' (lowercase)."""
    assert norm_old("designated in table 5.1 Design Standards By District.") == \
        norm_new("designated in table 6.1 Design Standards By District.")


def test_but_a_table_renumbered_for_a_different_reason_still_differs():
    """The article shift predicts TABLE 6.1 -> TABLE 7.1. A table actually
    renumbered to something else (inserted/reordered table) must still show."""
    assert norm_old("TABLE 6.1 DESIGN STANDARDS BY DISTRICT") != \
        norm_new("TABLE 7.3 DESIGN STANDARDS BY DISTRICT")


def test_but_a_renamed_table_title_still_differs():
    assert norm_old("TABLE 6.1 DESIGN STANDARDS BY DISTRICT") != \
        norm_new("TABLE 7.1 DIMENSIONAL STANDARDS BY DISTRICT")


def test_the_new_side_table_numbers_are_never_renumbered():
    assert norm_new("TABLE 7.1 DESIGN STANDARDS BY DISTRICT") == \
        "TABLE 7.1 DESIGN STANDARDS BY DISTRICT"


def test_normalize_old_side_also_renumbers_tables():
    assert nz.normalize_old_side("TABLE 6.1 DESIGN STANDARDS BY DISTRICT", amap=AMAP) == \
        "TABLE 7.1 DESIGN STANDARDS BY DISTRICT"


# --- Rule 4 context anchor: "table" in prose is not a caption/reference -----
#
# Review finding (2026-08-24): the un-anchored rule renumbered ANY "table N.M"
# in prose, including a compound noun like "water table" followed by an
# unrelated measurement. Not hypothetical: "water table" is standard septic/
# soils/groundwater language and a Shoreland article is planned (CLAUDE.md
# Phase 9), so this phrase is very likely to occur followed by a depth in
# feet. A real amendment to that depth must never be silently suppressed.

def test_the_reviewers_water_table_case_is_not_renumbered():
    """THE test for this fix. A genuine numeric amendment inside a phrase that
    merely contains the word 'table' followed by N.M must survive -- not be
    mistaken for a table caption/cross-reference."""
    old = "The seasonal high water table 5.2 feet below grade shall govern."
    new = "The seasonal high water table 6.2 feet below grade shall govern."
    assert norm_old(old) != norm_new(new)


def test_a_second_prose_table_case_is_not_renumbered():
    """A different compound-noun shape, same hazard class: 'rate table 9.1
    percent' is not a table caption or cross-reference either."""
    old = "The applicable tax rate table 9.1 percent applies to this parcel."
    new = "The applicable tax rate table 3.1 percent applies to this parcel."
    assert norm_old(old) != norm_new(new)


def test_but_a_genuine_bare_caption_reference_is_still_suppressed_with_the_anchor():
    """The anchor must not have thrown out real cases along with the hazard:
    a caption/reference immediately followed by sentence punctuation (no
    title text) still suppresses, same as one followed by a title."""
    assert norm_old("See Table 6.1.") == norm_new("See Table 7.1.")
    assert norm_old("per Table 6.1, as applicable.") == norm_new("per Table 7.1, as applicable.")


# --- Rule 5: frontmatter article-number renumbering -------------------------

def test_frontmatter_article_number_renumbering_is_suppressed():
    assert norm_old('article-number: "6"') == norm_new('article-number: "7"')


def test_but_an_unpredicted_frontmatter_article_number_still_differs():
    assert norm_old('article-number: "6"') != norm_new('article-number: "3"')


def test_the_new_side_frontmatter_is_never_renumbered():
    assert norm_new('article-number: "6"') == 'article-number: "6"'


def test_normalize_old_side_also_renumbers_frontmatter():
    assert nz.normalize_old_side('article-number: "6"', amap=AMAP) == 'article-number: "7"'


# --- Rule 3: paragraph re-wrapping ------------------------------------------

def test_rewrapping_is_suppressed():
    wrapped = "1. The proposed subdivision will not\n   result in undue water pollution."
    flat = "1. The proposed subdivision will not result in undue water pollution."
    assert norm_old(wrapped) == norm_old(flat)


def test_but_a_deleted_sentence_still_differs():
    """THE test. If this ever passes trivially the feature is unsafe."""
    keep = "1. Water shall be adequate. Sewage shall be adequate."
    cut = "1. Water shall be adequate."
    assert norm_old(keep) != norm_new(cut)


def test_a_changed_number_still_differs():
    assert norm_old("a 40 ft right-of-way") != norm_new("a 33 ft right-of-way")


def test_shall_to_may_still_differs():
    assert norm_old("The Board shall require") != norm_new("The Board may require")


# --- normalize_old_side: render-safe (no rewrap) ----------------------------
#
# Added after a Task 3 review finding (2026-08-24): the old side of a baseline
# redline is what redline-text.py --source RENDERS, not just compares. Rule 3
# (rewrap) collapses indented continuation lines, which flattens the Code's
# lettered sub-clause hierarchy into run-on prose once it reaches the
# renderer. normalize_old_side applies heading-case + renumbering only.

def test_normalize_old_side_still_suppresses_heading_case():
    assert nz.normalize_old_side("### A. PURPOSE", amap=AMAP) == "### a. PURPOSE"


def test_normalize_old_side_still_renumbers():
    assert nz.normalize_old_side("See Article 7.", amap=AMAP) == "See Article 8."


def test_normalize_old_side_preserves_indentation_on_a_nested_sub_clause_block():
    """THE test for the bug the review caught. A lettered sub-clause list, each
    line indented under its parent, must come out with every line intact --
    not merged into one run-on line the way `normalize()`'s rewrap rule would."""
    block = (
        "1. The reviewing authority may:\n"
        "    a. Determine the application is complete and ready for review.\n"
        "    b. Determine the application is incomplete and deny the application.\n"
        "    c. Determine the application is incomplete and allow withdrawal.\n"
    )
    out = nz.normalize_old_side(block, amap=AMAP)
    assert out == block, "indentation/line structure must be untouched"
    assert out.count("\n") == block.count("\n")


def test_normalize_old_side_does_not_collapse_a_wrapped_paragraph_either():
    """Unlike normalize(), this function must leave line breaks exactly where
    they were -- rewrap is Rule 3 and normalize_old_side never applies it."""
    wrapped = "1. The proposed subdivision will not\n   result in undue water pollution."
    assert nz.normalize_old_side(wrapped, amap=AMAP) == wrapped


def test_normalize_is_not_render_safe_for_the_same_block():
    """Documents the contrast directly: normalize() (comparison-only) DOES
    collapse the block that normalize_old_side (render-safe) leaves alone."""
    block = (
        "1. The reviewing authority may:\n"
        "    a. Determine the application is complete and ready for review.\n"
        "    b. Determine the application is incomplete and deny the application.\n"
    )
    assert norm_old(block) != block
    assert nz.normalize_old_side(block, amap=AMAP) == block


# --- The report --------------------------------------------------------------

def test_report_counts_each_rule_separately():
    old = "### A. PURPOSE\n1. See Article 7."
    new = "### a. PURPOSE\n1. See Article 8."
    r = nz.report(old, new, amap=AMAP)
    assert r["heading_case"] >= 1
    assert r["renumber"] >= 1
