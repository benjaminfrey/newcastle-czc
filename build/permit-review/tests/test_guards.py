"""Tests llm/guards.py -- the three output guards (W5 item 3).

Offline, no network, no LLM, no PII: every guard here is a pure function
over plain strings and structured fact/citation data the test constructs by
hand. Every guard is tested BOTH directions (fires on the bad case, silent
on the good one), plus one clean paragraph that must clear all three
untouched.

Several "should fire" and "should NOT fire" examples are lifted verbatim (or
near-verbatim) from the nine real Findings of Fact & Conclusions of Law in
`docs/Findings of Fact and Conclusions of Law/` -- see llm/guards.py's
module docstring for the citations. That is deliberate: the guard has to
survive this project's OWN house style, not just a hypothetical bad
sentence.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.citation import Citation, render as render_citation  # noqa: E402
from llm import guards  # noqa: E402


# --------------------------------------------------------------------------- #
# Guard 1 -- numeral grounding
# --------------------------------------------------------------------------- #


def test_grounding_silent_when_every_numeral_is_a_known_fact():
    text = "The lot is 2.1 Acres with 650 ft of frontage and a 50 ft setback."
    fact_set = ["2.1 Acres", "650 ft (along Sheepscot Rd)", "50 ft min"]
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is False
    assert result.ungrounded_sentences == ()
    assert all(f.grounded for f in result.findings)


def test_grounding_fires_on_an_unfamiliar_numeral():
    text = "The lot is 2.1 Acres with 900 ft of frontage."
    fact_set = ["2.1 Acres", "650 ft (along Sheepscot Rd)"]
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is True
    assert len(result.ungrounded_sentences) == 1
    assert "900" in result.ungrounded_sentences[0]
    ungrounded = [f for f in result.findings if not f.grounded]
    assert len(ungrounded) == 1
    assert ungrounded[0].raw == "900"
    assert ungrounded[0].value == Decimal("900")


def test_grounding_never_widens_by_dropping_a_real_mismatch():
    # A close-but-wrong numeral (899 vs the fact 900) must still fail --
    # "handle formatting variance honestly ... but NEVER by loosening until
    # everything passes" (task brief). No tolerance, no rounding.
    text = "Frontage is 899 ft."
    fact_set = ["900 ft"]
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is True


def test_grounding_handles_thousands_separator_variance():
    text = "The parcel contains 1,330 sq ft of impervious surface."
    fact_set = ["1330 sq ft"]  # fact stored WITHOUT the comma
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is False


def test_grounding_handles_trailing_zero_variance():
    text = "The measured setback is 74.2 ft."
    fact_set = ["74.20 ft"]  # fact stored with a trailing zero
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is False


def test_grounding_handles_mixed_fraction_variance():
    text = "The height is 74 1/2 inches."
    fact_set = ["74.5 in"]
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is False


def test_grounding_does_not_flag_a_district_code_glued_to_its_letter():
    # "D1" (no space) is an identifier, not a numeral a fact set would ever
    # hold -- a bare grounding check that ignored this would flag nearly
    # every sentence naming a district.
    text = "The property is in the D1 District."
    result = guards.check_numeral_grounding(text, fact_set=())
    assert result.unresolved is False
    assert result.findings == ()


def test_grounding_still_checks_a_space_separated_tax_map_or_lot_number():
    # Unlike a glued code, "Map 004, Lot 036" (space before the digits, the
    # real citation form used throughout docs/Findings of Fact and
    # Conclusions of Law/) IS a genuine numeral token -- it just needs to be
    # in the fact set like any other, which a real case's project-information
    # block would supply.
    text = "This concerns Tax Map 004, Lot 036."
    grounded = guards.check_numeral_grounding(text, fact_set=["Map 004", "Lot 036"])
    assert grounded.unresolved is False
    ungrounded = guards.check_numeral_grounding(text, fact_set=())
    assert ungrounded.unresolved is True


def test_grounding_dedupes_repeated_ungrounded_sentence():
    text = "The setback is 900 ft and 900 ft again."
    result = guards.check_numeral_grounding(text, fact_set=())
    assert len(result.ungrounded_sentences) == 1


def test_grounding_splits_sentences_without_breaking_on_a_decimal_point():
    text = "The setback is 74.2 ft. This is a second sentence with 900 ft."
    fact_set = ["74.2 ft"]
    result = guards.check_numeral_grounding(text, fact_set)
    assert result.unresolved is True
    assert len(result.ungrounded_sentences) == 1
    assert result.ungrounded_sentences[0].startswith("This is a second sentence")


# --------------------------------------------------------------------------- #
# Guard 2 -- citation stripping
# --------------------------------------------------------------------------- #


def test_citation_strip_fires_on_a_model_written_citation():
    text = "The Board reviewed this as required by Article 7, Section 15.D."
    result = guards.strip_and_rerender_citations(text)
    assert result.had_model_citation is True
    assert result.stripped_raw == ("Article 7, Section 15.D",)
    assert "Article 7" not in result.text
    assert "Section 15" not in result.text


def test_citation_strip_catches_the_full_real_standard_letter_form():
    # The exact form app/citation.py's render_citation() produces for a
    # lettered standard (CONTRACT.md §5's Citation.standard_letter comment).
    text = "This falls under Article 7, Section 12, Standard n. (Flood Areas), which applies here."
    result = guards.strip_and_rerender_citations(text)
    assert result.had_model_citation is True
    assert "Article 7" not in result.text
    assert "Standard n" not in result.text
    assert "Flood Areas" not in result.text  # the whole parenthetical goes with it


def test_citation_strip_catches_bare_section_table_exhibit_and_section_symbol():
    for text, missing in [
        ("See Section 12.b for the standard.", "Section 12"),
        ("See §12.b for the standard.", "12.b"),
        ("Values appear in Table 3.5 of the ruleset.", "Table 3.5"),
        ("The inventory is Exhibit 3.1.", "Exhibit 3.1"),
    ]:
        result = guards.strip_and_rerender_citations(text)
        assert result.had_model_citation is True, text
        assert missing not in result.text, result.text


def test_citation_strip_silent_on_text_with_no_citation():
    text = "The applicant proposes a single accessory building on the lot."
    result = guards.strip_and_rerender_citations(text)
    assert result.had_model_citation is False
    assert result.stripped_raw == ()
    assert result.text == text


def test_citation_strip_does_not_touch_a_bare_district_mention():
    # A district code alone is a data value, not a citation to Code text --
    # app/citation.py's own golden forms never render a district without an
    # "Article N" anchor, so this guard should not either.
    text = "The property is in the D1-Rural District."
    result = guards.strip_and_rerender_citations(text)
    assert result.had_model_citation is False
    assert result.text == text


def test_citation_strip_re_renders_only_through_app_citation_render():
    # The real §5.5 golden: Article 2, D1-Rural District, Lot Dimensions:
    # Primary Frontage Line Length. Whatever the model wrote is discarded;
    # what reaches `.text` must be byte-identical to citation.render()'s own
    # output for the SAME struct -- proving this guard calls the real
    # renderer rather than reimplementing citation text.
    c = Citation(
        "adopted", "adopted", 2,
        district_code="D1", district_name="Rural",
        panel_title="LOT DIMENSIONS", label="Primary Frontage Line Length",
    )
    text = "This is governed by Art. 2 Sec. 5 somewhere in the Code."
    result = guards.strip_and_rerender_citations(text, citations=[c])
    expected = render_citation(c, style="long")
    assert result.rendered == (expected,)
    assert expected in result.text
    assert "Sec. 5" not in result.text  # the model's own citation is gone


def test_citation_strip_with_no_citations_supplied_appends_nothing():
    text = "As described in Article 7, Section 15.D, the Board reviewed the plan."
    result = guards.strip_and_rerender_citations(text, citations=())
    assert result.rendered == ()
    assert "Article 7" not in result.text
    assert "(" not in result.text  # nothing appended, no dangling parenthetical


def test_citation_strip_catches_a_lowercase_citation():
    # Critic finding A3.1: CITATION_SHAPE_RE was case-sensitive, so a model
    # that emitted lowercase citation-shaped text sailed through unstripped.
    # A model's casing choice is not a safety boundary -- CONTRACT.md §5.1's
    # "a model-authored string that looks like a citation is a bug" does not
    # carve out an exception for casing.
    text = "the board reviewed this as required by article 7, section 15.d."
    result = guards.strip_and_rerender_citations(text)
    assert result.had_model_citation is True
    assert "article 7" not in result.text.lower()
    assert "section 15" not in result.text.lower()


def test_citation_strip_catches_lowercase_table_and_section_symbol_forms():
    for text, missing in [
        ("see §12.b for the standard.", "12.b"),
        ("values appear in table 3.5 of the ruleset.", "table 3.5"),
        ("the inventory is exhibit 3.1.", "exhibit 3.1"),
    ]:
        result = guards.strip_and_rerender_citations(text)
        assert result.had_model_citation is True, text
        assert missing not in result.text.lower(), result.text


# --------------------------------------------------------------------------- #
# Guard 3 -- conclusion-verb downgrade
# --------------------------------------------------------------------------- #

# "Bad" cases -- must fire (board_flag True). Several are real sentences
# (or near-verbatim) from the nine sample decisions.
_CONCLUSION_BAD_CASES = [
    ("comply_negative", "This structure does not comply with the required side setback."),
    ("comply_positive", "The application complies with all applicable standards."),
    ("compliance_state",
     "This height would be in compliance with the allowed heights for a single-story building."),
    ("satisfy", "The proposed pier satisfies the standards for a Small Project Plan."),
    ("fails_to", "This proposal fails to meet the required setback."),
    ("not_meet", "This lot split does not meet the definition of a Subdivision."),
    ("meets_standard",
     "The solar arrays will meet the Primary Building and Accessory Building setback requirements."),
    ("consistent", "The application is consistent with Article 2 of the Core Zoning Code."),
    ("inconsistent", "The proposal is inconsistent with the adopted Comprehensive Plan."),
    ("conclude", "The Board concludes that the application is consistent with the standards."),
    ("adversely_affect",
     "The proposed subdivision will not adversely affect the quality of that body of water."),
]


def test_conclusion_verbs_fire_on_every_bad_case():
    for label, text in _CONCLUSION_BAD_CASES:
        result = guards.check_conclusion_verbs(text)
        assert result.board_flag is True, f"{label}: expected a flag on {text!r}"
        assert len(result.matches) >= 1, label


# "Good" cases -- must stay silent (board_flag False). These are the modal-
# obligation form ("must comply with", "must meet") that states what the
# Code REQUIRES rather than concluding this application achieves it. Both
# quotes below are real, verbatim, from the Blood & Sons decision.
_CONCLUSION_GOOD_CASES = [
    ("Blood & Sons — building setbacks",
     "All primary buildings must comply with required front, side, and rear setback standards."),
    ("Blood & Sons — driveways",
     "Driveways must comply with the Roads, Driveways and Entrances Ordinance."),
    ("common form — frontage",
     "The width of a lot at the frontage must meet the lot requirements of the district where the lot is located."),
    ("plain factual description, no compliance language",
     "The lot is 2.1 acres with 650 ft of frontage along Sheepscot Rd and one existing accessory building."),
]


def test_conclusion_verbs_silent_on_every_good_case():
    for label, text in _CONCLUSION_GOOD_CASES:
        result = guards.check_conclusion_verbs(text)
        assert result.board_flag is False, f"{label}: unexpected flag on {text!r} -- matches: {result.matches}"
        assert result.matches == ()


def test_conclusion_verb_modal_exclusion_is_scoped_to_its_own_sentence():
    # The modal word "must" belongs to the FIRST sentence; it must not
    # suppress a real conclusion in the second one.
    text = "The application must be complete. It complies with the setback standard."
    result = guards.check_conclusion_verbs(text)
    assert result.board_flag is True
    assert any(m.category == "comply_positive" for m in result.matches)


def test_conclusion_verb_modal_exclusion_is_scoped_to_the_clause_not_the_whole_sentence():
    # Critic finding A2.1: the modal-exclusion window was the whole SENTENCE
    # prefix, not the clause. "The driveway must meet the required
    # standards" (a Code-requirement clause, correctly excluded) and "the
    # application does not meet the required setback" (a real conclusion
    # about a DIFFERENT complement) are two clauses of ONE sentence -- the
    # modal in the first clause must not swallow the conclusion in the
    # second just because they share a sentence.
    text = (
        "The driveway must meet the required standards, but the application "
        "does not meet the required setback."
    )
    result = guards.check_conclusion_verbs(text)
    assert result.board_flag is True
    assert any(m.category == "not_meet" for m in result.matches)
    # The first clause's "must meet the required standards" is still
    # correctly excluded -- it's the modal's own clause.
    assert not any(m.category == "meets_standard" for m in result.matches)


def test_conclusion_verb_modal_exclusion_still_covers_its_own_one_clause_sentence():
    # No comma at all -- the whole sentence is one clause, and the modal
    # governs the conclusion-shaped phrase that follows it, same as before
    # the clause-scoping fix.
    text = "The width of a lot at the frontage must meet the lot requirements of the district."
    result = guards.check_conclusion_verbs(text)
    assert result.board_flag is False
    assert result.matches == ()


def test_conclusion_verb_modal_exclusion_not_broken_by_thousands_separator_comma():
    # A comma inside a thousands-grouped numeral ("1,200") must not be
    # mistaken for a clause boundary -- that would wrongly narrow the modal
    # search window and flip a correctly-excluded, single-clause sentence
    # into a false positive.
    text = "The lot must contain at least 1,200 sq ft and complies with the setback requirement."
    result = guards.check_conclusion_verbs(text)
    assert result.board_flag is False
    assert result.matches == ()


def test_conclusion_verb_bare_meets_with_no_standard_complement_is_not_flagged():
    # A purely geometric, non-compliance use of "meets" ("meets the road")
    # must not fire -- the trigger requires a standard/requirement/
    # definition complement, not the bare verb.
    text = "The new driveway meets the existing road at a shallow angle."
    result = guards.check_conclusion_verbs(text)
    assert result.board_flag is False


# --------------------------------------------------------------------------- #
# Guard 4 -- residual redaction placeholder (critic finding A4.3)
# --------------------------------------------------------------------------- #


def test_residual_placeholder_fires_on_a_leftover_bracket():
    # A placeholder the model referenced but that isn't in this call's
    # token_map (mangled, or outright hallucinated) is left untouched by
    # restore_text() by design -- this guard is what catches the leftover
    # bracket instead of letting it reach a reader silently.
    text = "The owner, [REDACTED_NAME_2], has not applied for a permit."
    result = guards.check_residual_placeholders(text)
    assert result.unresolved is True
    assert len(result.matches) == 1
    assert result.matches[0].matched_text == "[REDACTED_NAME_2]"


def test_residual_placeholder_fires_on_every_class_shape():
    text = (
        "Contact [REDACTED_NAME_1] at [REDACTED_ADDRESS_1], "
        "[REDACTED_PHONE_1], or [REDACTED_EMAIL_1]; see [REDACTED_DEEDREF_1]."
    )
    result = guards.check_residual_placeholders(text)
    assert result.unresolved is True
    assert len(result.matches) == 5


def test_residual_placeholder_silent_on_fully_restored_text():
    # The normal case: restore_text() replaced every placeholder it knew
    # about, so no bracket-shaped text remains.
    text = "The owner, Robert Shattuck, has not applied for a permit."
    result = guards.check_residual_placeholders(text)
    assert result.unresolved is False
    assert result.matches == ()


def test_residual_placeholder_silent_on_text_with_no_brackets_at_all():
    text = "The lot is 2.1 acres with 650 ft of frontage."
    result = guards.check_residual_placeholders(text)
    assert result.unresolved is False
    assert result.matches == ()


# --------------------------------------------------------------------------- #
# Orchestrator -- ordering + the one paragraph that must clear all four
# --------------------------------------------------------------------------- #


def test_run_guards_strips_citations_before_grounding_so_article_numbers_are_not_flagged():
    text = "Per Article 7, Section 15.D, the setback is 50 ft."
    # Note: 7 and 15 are NOT in fact_set -- if grounding ran on the raw text
    # first, this would spuriously flag the sentence for the citation's own
    # numbers.
    result = guards.run_guards(text, fact_set=["50 ft"])
    assert result.citation_result.had_model_citation is True
    assert result.grounding_result.unresolved is False
    assert result.unresolved is False
    assert result.board_flag is False


def test_run_guards_clean_paragraph_passes_all_four_guards_untouched():
    # Renamed from "...passes_all_three..." when guard 4
    # (check_residual_placeholders) was added in the A4.3 repair pass --
    # the assertions on the first three guards are unchanged, only the
    # residual-placeholder assertion and the docstring/name are new.
    text = (
        "The applicant proposes a 24 ft by 36 ft accessory building with a "
        "50 ft side setback and 650 ft of frontage along Sheepscot Rd. "
        "The lot is 2.1 acres."
    )
    fact_set = ["24 ft", "36 ft", "50 ft", "650 ft (along Sheepscot Rd)", "2.1 acres"]
    result = guards.run_guards(text, fact_set=fact_set)
    assert result.citation_result.had_model_citation is False
    assert result.grounding_result.unresolved is False
    assert result.conclusion_result.board_flag is False
    assert result.residual_placeholder_result.unresolved is False
    assert result.unresolved is False
    assert result.board_flag is False
    assert result.text == text  # nothing touched -- no citation to strip, whitespace already clean


def test_run_guards_flags_unresolved_on_a_residual_placeholder_alone():
    # A paragraph clean on citations/numerals/conclusion verbs must still
    # be routed to a Board flag if a redaction placeholder never got
    # restored -- residual_placeholder_result drives `unresolved` even when
    # the other three guards are silent.
    # fact_set includes the bare "3" so the placeholder's own index number
    # doesn't ALSO trip the numeral-grounding guard -- this test isolates
    # the residual-placeholder guard, it doesn't need grounding's help.
    text = "The applicant is [REDACTED_NAME_3] and the lot is 2.1 acres."
    result = guards.run_guards(text, fact_set=["2.1 acres", "3"])
    assert result.citation_result.had_model_citation is False
    assert result.grounding_result.unresolved is False
    assert result.conclusion_result.board_flag is False
    assert result.residual_placeholder_result.unresolved is True
    assert result.unresolved is True


def test_run_guards_flags_a_dirty_paragraph_on_every_axis():
    text = (
        "Per Article 7, Section 15.D, the application complies with the "
        "900 ft frontage standard."
    )
    fact_set = ["650 ft"]  # 900 is not a known fact
    result = guards.run_guards(text, fact_set=fact_set)
    assert result.citation_result.had_model_citation is True
    assert result.grounding_result.unresolved is True
    assert result.conclusion_result.board_flag is True
    assert result.unresolved is True
    assert result.board_flag is True
