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


# --- The report --------------------------------------------------------------

def test_report_counts_each_rule_separately():
    old = "### A. PURPOSE\n1. See Article 7."
    new = "### a. PURPOSE\n1. See Article 8."
    r = nz.report(old, new, amap=AMAP)
    assert r["heading_case"] >= 1
    assert r["renumber"] >= 1
