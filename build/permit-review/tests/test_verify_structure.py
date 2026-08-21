"""Tests for ruleset_build/verify_structure.py -- the W2 gate hardening.

Exercises the mechanical assertions directly (not just "the whole run
prints ALL OK") so a future regression that flips one check green-to-red
(or vice versa) fails at the right test, not just at the summary line.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.verify_structure import (  # noqa: E402
    DECLARED_CRITERIA_TABLE,
    SUBDIVISION_LABEL_SPOT_CHECKS,
    RulesetLoadError,
    _is_contiguous,
    adopted_item_text,
    adopted_letters_at,
    draft_item_text,
    draft_letters_at,
    load_adopted_by_id,
    load_draft_nodes,
    run_checks,
)

try:
    ADOPTED = load_adopted_by_id()
except RulesetLoadError:
    ADOPTED = None

try:
    DRAFT = load_draft_nodes()
except RulesetLoadError:
    DRAFT = None

pytestmark = pytest.mark.skipif(
    ADOPTED is None or DRAFT is None, reason="rulesets/adopted or rulesets/draft-v0.22 not built"
)

_ALPHABET = "abcdefghijklmnopqrstuvwxyz"


def test_subdivision_is_exactly_a_through_u_in_both_rulesets() -> None:
    """The headline Defect-1 regression: 21 letters, not 17 (a-q, which is
    the SUBSECTION count one tree level up -- the exact conflation that let
    the original defect through a prose 'discrepancy note')."""
    expected = list(_ALPHABET[:21])
    assert expected == list("abcdefghijklmnopqrstu")

    got_adopted = adopted_letters_at(ADOPTED, article=7, section="12",
                                      subsection_heading="APPROVAL STANDARDS", digit_path=["1"])
    got_draft = draft_letters_at(DRAFT, article=8, section_name="SUBDIVISION",
                                  subsection_name="APPROVAL STANDARDS", digit_path=["1"])
    assert got_adopted == expected
    assert got_draft == expected


def test_subsection_count_is_seventeen_a_through_q_a_different_number() -> None:
    """The number the original defect's gate observation actually read (17,
    a-q) is a real, correct fact -- about SECTION 12's direct SUBSECTIONS,
    not about the APPROVAL STANDARDS letters. Both are true; they answer
    different questions. Asserted here so nobody re-conflates them."""
    sec = ADOPTED["art7.12"]
    subsection_letters = sorted(
        c.get("number") for c in sec.get("children") or [] if c.get("kind") == "subsection"
    )
    assert subsection_letters == list(_ALPHABET[:17])  # a..q
    assert subsection_letters != list(_ALPHABET[:21])  # NOT the same as a..u


def test_pollution_criterion_has_exactly_five_roman_sub_items() -> None:
    expected = ["i", "ii", "iii", "iv", "v"]
    got_adopted = adopted_letters_at(ADOPTED, article=7, section="12",
                                      subsection_heading="APPROVAL STANDARDS", digit_path=["1", "c"])
    got_draft = draft_letters_at(DRAFT, article=8, section_name="SUBDIVISION",
                                  subsection_name="APPROVAL STANDARDS", digit_path=["1", "c"])
    assert got_adopted == expected
    assert got_draft == expected


def test_nested_romans_are_excluded_from_the_top_level_letter_set() -> None:
    """Direct regression for Defect 2's root cause: the multi-character
    roman markers ('ii', 'iii', 'iv') can never be top-level letters at
    all, so their presence in the top-level set would be unambiguous proof
    of the nested-roman collision. 'i' and 'v' DO legitimately appear in
    BOTH sets (as real top-level letters AND as the single-character roman
    numerals i./v.) -- that coincidence of spelling is exactly what made
    Defect 2 possible, so this test checks the unambiguous markers, not a
    naive full-set disjointness (which would be a false assertion, not a
    regression guard)."""
    top = set(adopted_letters_at(ADOPTED, article=7, section="12",
                                  subsection_heading="APPROVAL STANDARDS", digit_path=["1"]))
    romans = set(adopted_letters_at(ADOPTED, article=7, section="12",
                                     subsection_heading="APPROVAL STANDARDS", digit_path=["1", "c"]))
    assert romans == {"i", "ii", "iii", "iv", "v"}
    unambiguous_romans = {"ii", "iii", "iv"}  # can never be mistaken for a letter
    assert top.isdisjoint(unambiguous_romans)


@pytest.mark.parametrize("letter,expected_prefix", SUBDIVISION_LABEL_SPOT_CHECKS)
def test_label_spot_checks_both_rulesets(letter: str, expected_prefix: str) -> None:
    base_adopted = dict(article=7, section="12", subsection_heading="APPROVAL STANDARDS", digit_path=["1"])
    base_draft = dict(article=8, section_name="SUBDIVISION", subsection_name="APPROVAL STANDARDS", digit_path=["1"])

    text_adopted = adopted_item_text(ADOPTED, letter=letter, **base_adopted)
    text_draft = draft_item_text(DRAFT, letter=letter, **base_draft)

    assert text_adopted is not None, f"adopted: no standard lettered {letter!r}"
    assert text_draft is not None, f"draft: no standard lettered {letter!r}"
    assert text_adopted.strip().casefold().startswith(expected_prefix.casefold())
    assert text_draft.strip().casefold().startswith(expected_prefix.casefold())


@pytest.mark.parametrize("row", DECLARED_CRITERIA_TABLE, ids=lambda r: r["citation"])
def test_declared_cardinality_table_matches_both_rulesets(row: dict) -> None:
    expected = row["expected_letters"]
    got_adopted = adopted_letters_at(ADOPTED, **row["adopted"])
    got_draft = draft_letters_at(DRAFT, **row["draft"])
    assert got_adopted == expected, f"[adopted] {row['citation']}: {row['adopted']}"
    assert got_draft == expected, f"[draft-v0.22] {row['citation']}: {row['draft']}"


def test_variance_item3_and_item4_each_have_their_own_c_no_cross_contamination() -> None:
    """Article 7/8 Section 19.d items 3 (Undue Hardship) and 4 (Practical
    Difficulty) each have their own lettered 'c' -- a second, independent
    letter-reuse collision class from Defect 2's c/c.i romans. Verifies
    they resolve to DIFFERENT, correctly-scoped text, never merged."""
    c3 = adopted_item_text(ADOPTED, article=7, section="19", subsection_heading="APPROVAL STANDARDS",
                            digit_path=["3"], letter="c")
    c4 = adopted_item_text(ADOPTED, article=7, section="19", subsection_heading="APPROVAL STANDARDS",
                            digit_path=["4"], letter="c")
    assert c3 is not None and c4 is not None
    assert c3 != c4
    assert "essential character" in c3.casefold()  # Undue Hardship's own 'c'
    assert "practical difficulty" in c4.casefold()  # Practical Difficulty's own 'c'


@pytest.mark.parametrize(
    "markers,expected_ok",
    [
        (list("abcde"), True),
        (list("abcdefghijklmnopqrstu"), True),
        (["i", "ii", "iii", "iv", "v"], True),
        (["1", "2", "3"], True),
        (list("abd"), False),  # missing 'c' -- the exact shape of Defect 1
        (["i", "ii", "iv"], False),  # missing 'iii'
        (["1", "3"], False),
        (["a"], True),  # length-1 group trivially contiguous
    ],
)
def test_is_contiguous_unit_cases(markers: list[str], expected_ok: bool) -> None:
    ok, _detail = _is_contiguous(markers)
    assert ok is expected_ok


def test_run_checks_reports_all_ok_on_the_committed_rulesets() -> None:
    """End-to-end: the full mechanical gate is green on the rulesets this
    repo actually ships (both defects fixed, both rulesets consistent)."""
    result = run_checks()
    fails = [line for line in result.lines if line.startswith("FAIL")]
    assert result.ok, f"unexpected FAIL lines: {fails}"
