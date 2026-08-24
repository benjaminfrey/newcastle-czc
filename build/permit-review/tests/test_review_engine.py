"""Tests for engine/review.py -- the W6 review engine core: numeric
comparison, the exception escape hatch, judgement questions, and condition
wiring.

Run offline: `cd build/permit-review && .venv/bin/python -m pytest
tests/test_review_engine.py -v`

THE CORE INVARIANT under test: the engine can never emit a conclusion.
`test_disposition_set_has_no_verdict` enumerates every member of
`Disposition` -- the complete, closed set of things this engine can ever
produce -- and asserts none of them is a verdict, mechanically (substring
checks + the same conclusion-verb guard `llm/guards.py` uses on LLM output,
CONTRACT.md §9.4). `test_no_rendered_text_is_a_verdict` runs every
human-facing string this module can actually render (board_question,
fact-sentence, exception reason, condition reason, not-applicable note)
through the identical check.

The Buehner reproduction (`test_buehner_setback_reproduction`) uses the
REAL numbers from docs/Findings of Fact and Conclusions of Law/4.A2. M004,
L071 (156 Sheepscot Rd, Buehner) Shoreland Only FoF & CoL 2025.03.18.pdf:
proposed setback 180 ft against a 250 ft standard (Shoreland Zoning III.B),
under the I.M Special Exceptions pathway, which excepts "structure setback
requirements" from its own demonstration list. The real Conclusions of Law
in that decision are a verbatim 9-item list mirroring I.L's procedure
standards; none of the 9 says anything about the setback distance. This
test asserts the engine reproduces that shape: the raw shortfall is
recorded as a fact, the exception fires, and no disposition anywhere is a
verdict.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from engine import review as rv  # noqa: E402
from llm.guards import check_conclusion_verbs  # noqa: E402


# --------------------------------------------------------------------------- #
# THE core invariant: the disposition set is never a verdict.
# --------------------------------------------------------------------------- #


# Mechanical, not aspirational: every disposition this engine can ever
# produce, enumerated once here so a new member is forced through this same
# check. If this tuple and Disposition's actual membership ever diverge,
# that is itself a bug this test catches (see the membership-completeness
# assertion below).
_ALL_DISPOSITIONS = tuple(rv.Disposition)

_VERDICT_WORD_FRAGMENTS = (
    "met", "not_met", "compliant", "noncompliant", "violat", "deficient",
    "approve", "denied", "denial", "pass", "fail", "satisf", "conclu",
    "verdict", "decision",
)


def test_disposition_set_is_complete_and_enumerated():
    """Guards the mechanical enumeration itself: if someone adds a
    Disposition member without updating this test file, this fails loudly
    rather than the coverage silently narrowing."""
    assert set(_ALL_DISPOSITIONS) == set(rv.Disposition)
    assert len(_ALL_DISPOSITIONS) == 7, (
        "Disposition gained or lost a member -- update this test's expected "
        "count (and re-review every member for verdict language) rather "
        "than just bumping the number."
    )


@pytest.mark.parametrize("disposition", _ALL_DISPOSITIONS)
def test_disposition_set_has_no_verdict(disposition: rv.Disposition):
    """Enumerates every disposition the engine can produce and asserts none
    of them is a verdict -- both the enum's programmatic .value and its
    .name, checked against a blunt fragment list AND against the same
    conclusion-verb guard the LLM layer is held to."""
    haystack = f"{disposition.name} {disposition.value}".lower()
    for frag in _VERDICT_WORD_FRAGMENTS:
        assert frag not in haystack, (
            f"Disposition.{disposition.name} ({disposition.value!r}) contains "
            f"the verdict fragment {frag!r} -- the engine must never be able "
            f"to emit a conclusion."
        )
    guard = check_conclusion_verbs(haystack)
    assert guard.board_flag is False, (
        f"Disposition.{disposition.name} tripped the conclusion-verb guard: {guard.matches!r}"
    )


def test_disposition_docstrings_have_no_verdict():
    """The module docstring text sitting above each Disposition member
    (captured here by reading the source, since Python doesn't expose enum
    member comments at runtime) is checked separately below via the
    rendered-text tests; this test instead re-asserts the same over the
    class docstring block that IS introspectable -- Disposition.__doc__ --
    so at least the class-level documentation is covered mechanically too."""
    doc = (rv.Disposition.__doc__ or "").lower()
    for frag in ("not_met", "compliant", "violat", "deficient", "approved", "denied"):
        assert frag not in doc


# --------------------------------------------------------------------------- #
# Numeric comparison -- record, never a verdict.
# --------------------------------------------------------------------------- #


def test_numeric_comparison_emits_record_not_verdict():
    record = rv.compare_numeric(
        label="Structure setback", proposed=180.0, required=250.0, unit="ft",
        comparator=">=", citation="Shoreland Zoning III.B",
    )
    # It is a RECORD: proposed, required, unit, citation are all present verbatim.
    assert record.proposed == 180.0
    assert record.required == 250.0
    assert record.unit == "ft"
    assert record.citation == "Shoreland Zoning III.B"
    # raw_satisfied is the ONLY boolean anywhere on this record, and it is
    # explicitly the raw arithmetic fact, not a legal conclusion (180 >= 250
    # is False -- there is no other field that could be mistaken for a verdict).
    assert record.raw_satisfied is False
    assert not hasattr(record, "conclusion")
    assert not hasattr(record, "verdict")
    assert not hasattr(record, "compliant")
    # The rendered fact sentence states both numbers and stops.
    sentence = record.as_fact_sentence()
    assert "180" in sentence and "250" in sentence
    guard = check_conclusion_verbs(sentence)
    assert guard.board_flag is False, guard.matches


def test_numeric_comparison_direction_matters():
    # A MAXIMUM standard (spaghetti-lot ratio, <=) with a proposed value
    # that satisfies it raw-arithmetically.
    ok = rv.compare_numeric(
        label="Lot depth to shore frontage ratio", proposed=2.88, required=5.0,
        unit="ratio", comparator="<=", citation=None,
    )
    assert ok.raw_satisfied is True
    # And one that does not.
    over = rv.compare_numeric(
        label="Lot depth to shore frontage ratio", proposed=6.1, required=5.0,
        unit="ratio", comparator="<=", citation=None,
    )
    assert over.raw_satisfied is False


def test_evaluate_numeric_criterion_without_exception_still_never_concludes():
    """No exception pathway is active -- the engine still only records a
    fact and asks the Board; it does not decide."""
    finding = rv.evaluate_numeric_criterion(
        label="Primary Frontage Line Length", rule_category="frontage",
        proposed=418.0, required=250.0, unit="ft", comparator=">=",
        citation="Article 2, D1 - Rural",
    )
    assert finding.disposition == rv.Disposition.FACT_RECORDED
    assert finding.unresolved is True
    assert finding.numeric is not None and finding.numeric.raw_satisfied is True
    assert finding.exception is None
    assert finding.board_question is not None
    for text in (finding.body, finding.board_question):
        guard = check_conclusion_verbs(text)
        assert guard.board_flag is False, (text, guard.matches)


# --------------------------------------------------------------------------- #
# The Buehner reproduction -- the exception escape hatch.
# --------------------------------------------------------------------------- #


def _buehner_context() -> rv.ReviewContext:
    """The real Buehner posture: proceeding under Shoreland I.M Special
    Exceptions, whose own preamble reads 'In addition to the criteria
    specified in Section I.L: Procedure For Administering Permits,
    EXCEPTING STRUCTURE SETBACK REQUIREMENTS, the Planning Board may
    approve a permit for a single-family residential structure...' --
    i.e. 'setback' is the one category this pathway excepts."""
    return rv.ReviewContext(
        review_path="special_exception",
        excepted_categories=frozenset({"setback"}),
        exception_citation="Shoreland Zoning I.M Special Exceptions",
    )


def test_buehner_setback_reproduction():
    finding = rv.evaluate_numeric_criterion(
        label="Principal structure setback",
        rule_category="setback",
        proposed=180.0,
        required=250.0,
        unit="ft",
        comparator=">=",
        citation="Shoreland Zoning III.B Principal and Accessory Structures",
        context=_buehner_context(),
    )

    # The raw shortfall is a preserved FACT ...
    assert finding.numeric is not None
    assert finding.numeric.proposed == 180.0
    assert finding.numeric.required == 250.0
    assert finding.numeric.raw_satisfied is False  # 180 < 250, the real shortfall

    # ... but the exception escape hatch fired, and the disposition is a
    # FLAG, not a verdict on the setback.
    assert finding.disposition == rv.Disposition.EXCEPTION_FLAGGED
    assert finding.exception is not None
    assert finding.exception.excepted is True
    assert finding.exception.citation == "Shoreland Zoning I.M Special Exceptions"

    # Exactly the real decision's shape: NO conclusion of law is rendered for
    # this standard (no board_question asking whether the setback "passes" --
    # in fact no board_question at all, matching the real decision's silence).
    assert finding.board_question is None

    # And, mechanically, nothing in the rendered body is a verdict.
    assert finding.body is not None
    assert "180" in finding.body and "250" in finding.body
    guard = check_conclusion_verbs(finding.body)
    assert guard.board_flag is False, guard.matches
    assert rv.contains_banned_verdict_language(finding.body) is None


def test_exception_escape_hatch_is_a_noop_off_the_exception_pathway():
    """The same 180-vs-250 shortfall, but WITHOUT the special-exception
    context -- the escape hatch must not fire, and the ordinary
    fact-plus-question path is used instead. Proves the hatch is
    category-and-pathway-scoped, not a blanket suppressor."""
    finding = rv.evaluate_numeric_criterion(
        label="Principal structure setback", rule_category="setback",
        proposed=180.0, required=250.0, unit="ft", comparator=">=",
        citation="Shoreland Zoning III.B",
        context=None,
    )
    assert finding.disposition == rv.Disposition.FACT_RECORDED
    assert finding.exception is None
    assert finding.board_question is not None


def test_exception_escape_hatch_is_category_scoped():
    """The Buehner pathway excepts 'setback' only -- a different category
    standard reviewed under the SAME special-exception context must NOT be
    swept up by the hatch."""
    context = _buehner_context()
    finding = rv.evaluate_numeric_criterion(
        label="Total footprint", rule_category="footprint",
        proposed=2328.0, required=1500.0, unit="sf", comparator="<=",
        citation="Shoreland Zoning I.M.4",
        context=context,
    )
    assert finding.disposition == rv.Disposition.FACT_RECORDED
    assert finding.exception is None


def test_check_exception_escape_hatch_directly_is_a_noop_by_default():
    result = rv.check_exception_escape_hatch("setback", rv.ReviewContext())
    assert result.excepted is False
    assert result.reason is None


# --------------------------------------------------------------------------- #
# Judgement criteria -> a first-person question, unresolved=1.
# --------------------------------------------------------------------------- #


def test_judgement_tells_detects_the_brief_s_list():
    text = (
        "Pollution: The proposed subdivision will not result in undue water "
        "or air pollution."
    )
    tells = rv.judgement_tells_found(text)
    assert "undue" in tells


def test_judgement_criterion_renders_first_person_question_unresolved():
    finding = rv.evaluate_judgement_criterion(
        rule_category="pollution",
        subject="the proposed subdivision",
        code_text=(
            "Pollution: The proposed subdivision will not result in undue "
            "water or air pollution."
        ),
        citation_display="Article 7, Section 12, Standard c. (Pollution)",
    )
    assert finding.disposition == rv.Disposition.BOARD_QUESTION
    assert finding.unresolved is True
    assert finding.numeric is None
    assert finding.body is None  # no stated fact -- a judgement call is not a fact the engine has
    assert finding.board_question is not None
    assert "?" in finding.board_question
    # It quotes the Code verbatim rather than paraphrasing it.
    assert "undue water" in finding.board_question
    guard = check_conclusion_verbs(finding.board_question)
    assert guard.board_flag is False, guard.matches


# --------------------------------------------------------------------------- #
# Condition wiring -- criterion n. fires on every subdivision, verbatim.
# --------------------------------------------------------------------------- #


_REAL_FLOOD_CONDITION_SENTENCE = (
    "All principal structures proposed on any lot within the subdivision "
    "shall be constructed with their lowest floor, including the basement, "
    "at least three feet above the 100-year flood elevation."
)


def test_flood_condition_text_is_verbatim():
    """This sentence appears, word for word, in BOTH real subdivision
    Findings of Fact in docs/ (Shattuck 2025.12.18 condition 1; Uberoi
    2024.08.15 DRAFT condition 1) -- checked here character-for-character
    against a copy transcribed directly from those PDFs."""
    assert rv.FLOOD_CONDITION_TEXT == _REAL_FLOOD_CONDITION_SENTENCE


def test_flood_condition_fires_unconditionally():
    """No case facts are accepted by fire_flood_condition() -- it cannot be
    made to NOT fire, matching the W6 brief's 'fire it automatically on
    every subdivision.'"""
    cond = rv.fire_flood_condition(rule_id="rule-art7-12-f-1-n")
    assert cond.text == rv.FLOOD_CONDITION_TEXT
    assert cond.mandatory is True
    assert cond.rule_id == "rule-art7-12-f-1-n"


def test_flood_condition_criterion_disposition():
    finding = rv.evaluate_flood_condition_criterion(rule_id="rule-art7-12-f-1-n")
    assert finding.disposition == rv.Disposition.CONDITION_ATTACHED
    assert finding.unresolved is False
    assert finding.condition is not None
    assert finding.condition.text == rv.FLOOD_CONDITION_TEXT
    guard = check_conclusion_verbs(finding.body or "")
    assert guard.board_flag is False


# --------------------------------------------------------------------------- #
# Not-applicable / applicability-unknown -- facts and questions, never verdicts.
# --------------------------------------------------------------------------- #


def test_not_applicable_is_a_fact_not_a_verdict():
    finding = rv.evaluate_not_applicable(
        rule_category="spaghetti_lots",
        subject="lot depth to shore frontage ratio",
        citation_display="Article 7, Section 12",
    )
    assert finding.disposition == rv.Disposition.NOT_APPLICABLE
    assert finding.unresolved is False
    assert "do not apply" in finding.body
    guard = check_conclusion_verbs(finding.body)
    assert guard.board_flag is False, guard.matches


def test_applicability_unknown_never_suppresses_and_asks():
    finding = rv.evaluate_applicability_unknown(
        rule_category="storm_water",
        code_text="Storm Water: The proposed subdivision will provide for adequate storm water management ...",
        citation_display="Article 7, Section 12, Standard q. (Storm Water)",
    )
    assert finding.disposition == rv.Disposition.APPLICABILITY_UNKNOWN
    assert finding.unresolved is True
    assert finding.board_question is not None  # UNKNOWN never suppresses the node -- it still renders and asks
    guard = check_conclusion_verbs(finding.board_question)
    assert guard.board_flag is False, guard.matches


def test_procedural_reference_disposition():
    finding = rv.evaluate_procedural_reference(
        rule_category="code_standards",
        note="See above for any applicable standards set forth in the Core Zoning Code.",
    )
    assert finding.disposition == rv.Disposition.PROCEDURAL_REFERENCE
    assert finding.unresolved is False


# --------------------------------------------------------------------------- #
# Blanket sweep: every human-facing string this module's public functions
# can render, in one place, through the same guard.
# --------------------------------------------------------------------------- #


def test_no_rendered_text_is_a_verdict():
    """Every one of these samples must clear `contains_banned_verdict_language`
    -- that check is a blunt substring net over words like "compliant" /
    "approved" that should never appear ANYWHERE this engine renders,
    quoted Code text included (Article 7's own standards never use those
    exact words for themselves).

    `check_conclusion_verbs` (the sentence-aware guard) is asserted clean
    on every sample's own AUTHORED wrapper text. One sample --
    render_judgement_question()'s real quoted `code_text` -- is checked
    SEPARATELY (2026-08-24, W8 over-conclusion round: see
    engine.review.render_judgement_question's own docstring, "THIS PROMISE
    IS SCOPED TO THE WRAPPER"): a real Article 7 standard's own words can be
    conclusion-shaped ("will not cause unreasonable..."), and now that the
    guard's pattern list is wide enough to catch that real dodge phrasing
    (previously missed -- see tests/test_over_conclusion_dodges.py), it
    correctly fires on the QUOTED portion. That is not a leak: it is the
    guard doing its job on the Code's own text, exactly the case
    eval/over_conclusion.py's `question_hits` bucket exists to record
    rather than assume can never happen. What must still hold, and is
    asserted below, is that the engine's OWN wrapper words around the quote
    ("The standard ... provides: ... What is the Board's finding...")
    never themselves trigger the guard."""
    clean_samples: list[str] = []

    clean_samples.append(
        rv.compare_numeric(
            label="Structure setback", proposed=180.0, required=250.0,
            unit="ft", comparator=">=", citation=None,
        ).as_fact_sentence()
    )
    clean_samples.append(
        rv.check_exception_escape_hatch("setback", _buehner_context()).reason or ""
    )
    clean_samples.append(rv.fire_flood_condition().reason)
    clean_samples.append(
        rv.evaluate_not_applicable(
            rule_category="x", subject="shore frontage", citation_display="Article 7"
        ).body
        or ""
    )
    clean_samples.append(
        rv.evaluate_applicability_unknown(
            rule_category="x", code_text="some standard text", citation_display=None
        ).board_question
        or ""
    )

    for text in clean_samples:
        assert rv.contains_banned_verdict_language(text) is None, text
        guard = check_conclusion_verbs(text)
        assert guard.board_flag is False, (text, guard.matches)

    # render_judgement_question(): check the banned-substring net over the
    # FULL rendered question (quoted Code text included -- Article 7's own
    # words never use these exact banned substrings for themselves), and
    # check the sentence-aware guard against the WRAPPER ALONE by rendering
    # with an inert, non-conclusion-shaped code_text stand-in -- proving the
    # engine's own authored words ("The standard ... provides ... What is
    # the Board's finding...") are what stays clean, independent of
    # whatever real standard text a caller supplies.
    real_code_text = "Erosion: The proposed subdivision will not cause unreasonable soil erosion."
    rendered_with_real_standard = rv.render_judgement_question(
        subject="the proposed subdivision", code_text=real_code_text,
        citation_display="Article 7, Section 12, Standard f. (Erosion)",
    )
    assert rv.contains_banned_verdict_language(rendered_with_real_standard) is None, rendered_with_real_standard

    wrapper_only = rv.render_judgement_question(
        subject="the proposed subdivision", code_text="INERT_PLACEHOLDER_NOT_A_CONCLUSION",
        citation_display="Article 7, Section 12, Standard f. (Erosion)",
    )
    wrapper_guard = check_conclusion_verbs(wrapper_only)
    assert wrapper_guard.board_flag is False, (
        "the engine's OWN wrapper words around a quoted standard must never "
        f"themselves read as a conclusion: {wrapper_only!r} -> {wrapper_guard.matches}"
    )

    # And confirm the guard DOES fire when the real standard's own words are
    # conclusion-shaped (documenting the expected behaviour, not just
    # tolerating it) -- every match must be a real dodge pattern, never the
    # banned-substring net's job duplicated incorrectly.
    real_guard = check_conclusion_verbs(rendered_with_real_standard)
    assert real_guard.board_flag is True
    assert any(m.category == "cause_or_result_in_unreasonable" for m in real_guard.matches)
