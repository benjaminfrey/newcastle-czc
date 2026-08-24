"""The review engine core (W6): numeric comparison, the exception escape
hatch, judgement-criterion questions, and condition wiring.

THE ONE RULE THIS MODULE EXISTS TO ENFORCE (CONTRACT.md preamble, "THE
FRAMING RULE"): the app produces the working draft the Board amends, never a
decision. It never concludes and never signs. A shortfall is ALWAYS a Board
flag, never a conclusion.

SCOPE BOUNDARY, same posture as engine/deadlines.py: this is a PURE
COMPUTATION ENGINE. Given a criterion (a `rules` row, or the lightweight
`RuleSpec` shape below) and a case's known facts, it produces a `Finding` --
a stated fact, an exception flag, or a first-person question -- and stops.
It does not write to `findings_nodes` itself; that is the job of whatever
W6 workflow owns turning a `Finding` into a findings_nodes row (rule_id,
citation_json, body, unresolved, board_question, provenance_json). Nothing
here imports `app.db` or opens a connection.

THE CORE INVARIANT: `Disposition` is a closed enum, and every disposition
this engine can produce is a fact-statement or a question, never a verdict.
tests/test_review_engine.py enumerates the whole set and asserts none of it,
and none of the human-facing text this module renders, trips
`llm.guards.check_conclusion_verbs` (the same conclusion-verb list the LLM
output guard uses, CONTRACT.md §9.4) or contains a banned verdict word.

THE EXCEPTION ESCAPE HATCH is modeled on the real Buehner decision
(docs/Findings of Fact and Conclusions of Law/4.A2. M004, L071 (156
Sheepscot Rd, Buehner) Shoreland Only FoF & CoL 2025.03.18.pdf): a 180 ft
setback was proposed against a 250 ft standard (Shoreland Zoning III.B).
Section I.M "Special Exceptions" opens with "In addition to the criteria
specified in Section I.L ..., EXCEPTING STRUCTURE SETBACK REQUIREMENTS, the
Planning Board may approve ...". Because the application proceeded under
that Special Exception pathway, and setback is one of the categories I.M
explicitly excepts from what must be demonstrated, the Board's Conclusions
of Law (a verbatim numbered list mirroring I.L's 9 standards) contain NO
conclusion about the setback distance at all -- the 250 ft standard and the
180 ft proposed distance sit next to each other in the Findings as adjacent
facts, and the analysis simply moves on. `check_exception_escape_hatch()`
below reproduces that shape for any numeric or boolean criterion: it runs
BEFORE any disposition is chosen, and when it fires, the disposition is
EXCEPTION_FLAGGED (a flag, not a verdict) regardless of the raw arithmetic
result.

THE FLOOD CONDITION (criterion n., "Flood Areas", art7.12.f.1.n) is wired
to fire unconditionally on every subdivision review. Its condition text
(the sentence a subdivision's approved plan actually carries) is IDENTICAL,
word for word, in both real subdivision samples in docs/ (Shattuck,
2025.12.18 condition 1; Uberoi, 2024.08.15 DRAFT condition 1) --
`FLOOD_CONDITION_TEXT` below is that sentence, lifted verbatim. Do not
paraphrase it; if it ever needs to change, change it by re-copying the
source sentence, not by editing prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

Comparator = Literal[">=", "<=", ">", "<", "=="]

_COMPARATOR_FNS: dict[Comparator, Any] = {
    ">=": lambda proposed, required: proposed >= required,
    "<=": lambda proposed, required: proposed <= required,
    ">": lambda proposed, required: proposed > required,
    "<": lambda proposed, required: proposed < required,
    "==": lambda proposed, required: proposed == required,
}


# --------------------------------------------------------------------------- #
# The disposition set -- THE CLOSED ENUM.
#
# Every member name and every member value below is worded as a stated fact
# or a question, on purpose. None of them may ever read as a merits verdict
# ("met", "not_met", "compliant", "violates", "deficient", "approved",
# "denied", ...). tests/test_review_engine.py:test_disposition_set_has_no_verdict
# enumerates this set mechanically and fails the build if that ever stops
# being true -- see that test before changing a name here.
# --------------------------------------------------------------------------- #


class Disposition(str, Enum):
    FACT_RECORDED = "fact_recorded"
    # A numeric or boolean comparison was made and is stated as a fact
    # (proposed vs. required, or the raw yes/no of a factual question like
    # "were wetlands identified on the submitted maps"). No verdict is drawn;
    # the Board is asked to make the determination.

    EXCEPTION_FLAGGED = "exception_flagged"
    # The exception escape hatch fired: this standard sits inside a
    # pathway (special exception, waiver, variance) that excepts it from
    # the ordinary demonstration. The raw fact is still recorded, but no
    # disposition beyond "flagged for the Board" is ever drawn from it.

    BOARD_QUESTION = "board_question"
    # A judgement criterion ("undue", "unreasonable", "adequate", ...) --
    # this is not something an engine determines. It renders as a
    # first-person question to the Board, unresolved=1, always.

    CONDITION_ATTACHED = "condition_attached"
    # A mandatory condition of approval was wired in automatically (the
    # flood-elevation condition, criterion n.). Attaching a condition is
    # not a merits verdict on the application -- it is boilerplate that
    # rides along with every subdivision regardless of outcome.

    NOT_APPLICABLE = "not_applicable"
    # The applicability gate determined this standard's subject matter is
    # not present in this application (e.g. no shore frontage, so the
    # spaghetti-lot ratio has nothing to measure). A fact about scope, not
    # a verdict on the merits.

    APPLICABILITY_UNKNOWN = "applicability_unknown"
    # The applicability gate could not determine whether this standard
    # applies. Per the W6 brief: UNKNOWN NEVER SUPPRESSES A NODE. The
    # standard still renders, and the Board is asked to resolve it.

    PROCEDURAL_REFERENCE = "procedural_reference"
    # A pointer standard ("the standards of this Code", "the Newcastle
    # Road, Driveway, and Entrance Ordinance") that folds into the rest of
    # the walk rather than standing on its own -- both real subdivision
    # samples in docs/ handle art7.12.f.1.a/.b exactly this way.


# The banned substrings this module's own rendered text is checked against,
# independent of and in addition to llm.guards.check_conclusion_verbs (which
# is phrase-level and English-sentence-shaped; this is a blunter, cheaper
# safety net over short strings like enum values and templates). Deliberately
# includes the raw pieces a verdict is built from ("met", "compliant", ...)
# so a future member/template can't reintroduce one by combining fragments.
_BANNED_VERDICT_SUBSTRINGS: tuple[str, ...] = (
    "not_met", "not met", "is_met", "compliant", "noncompliant",
    "non-compliant", "violat", "deficient", "approved", "denied",
    "satisfied", "unsatisfied", "conclusion:", "verdict",
)


def contains_banned_verdict_language(text: str) -> str | None:
    """Returns the first banned substring found in `text` (case-insensitive),
    or None. Cheap, mechanical, and deliberately over-inclusive; the English-
    sentence-aware check is llm.guards.check_conclusion_verbs, reused in
    tests/test_review_engine.py against every human-facing string this
    module can render."""
    lowered = text.lower()
    for bad in _BANNED_VERDICT_SUBSTRINGS:
        if bad in lowered:
            return bad
    return None


# --------------------------------------------------------------------------- #
# Numeric comparison -- EMITS A RECORD, NEVER A VERDICT.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class NumericComparisonRecord:
    """States proposed vs. required and stops. `raw_satisfied` is the raw
    arithmetic fact (did the comparator hold) -- NOT a legal conclusion.
    Buehner is the proof this distinction matters: raw_satisfied is False
    (180 < 250) and yet no Conclusion of Law about the setback was ever
    written, because the exception escape hatch (below) intercepted it
    first. Nothing that consumes this record may treat `raw_satisfied` as
    the answer; it is an input to the exception check and, when no
    exception applies, a fact placed before the Board -- never rendered as
    "met"/"not met"."""

    label: str  # "Structure setback", "Lot depth to shore frontage ratio"
    proposed: float
    required: float
    unit: str  # "ft", "ratio", ...
    comparator: Comparator  # the direction the standard requires, e.g. ">=" for a minimum
    citation: Any  # an app.citation.Citation, or any opaque citation token; never interpreted here
    raw_satisfied: bool = field(init=False)

    def __post_init__(self) -> None:
        fn = _COMPARATOR_FNS[self.comparator]
        object.__setattr__(self, "raw_satisfied", bool(fn(self.proposed, self.required)))

    def as_fact_sentence(self) -> str:
        """A plain, verdict-free restatement of the two numbers -- suitable
        for the Findings prose ("The proposed X is Y; the standard requires
        Z."). Never says whether Y satisfies Z."""
        return (
            f"The proposed {self.label} is {self.proposed:g} {self.unit}. "
            f"The standard requires {self.label.lower()} {_comparator_words(self.comparator)} "
            f"{self.required:g} {self.unit}."
        )


def _comparator_words(comparator: Comparator) -> str:
    return {
        ">=": "not less than",
        "<=": "not more than",
        ">": "greater than",
        "<": "less than",
        "==": "equal to",
    }[comparator]


def compare_numeric(
    *,
    label: str,
    proposed: float,
    required: float,
    unit: str,
    comparator: Comparator,
    citation: Any,
) -> NumericComparisonRecord:
    """The one entry point for a numeric comparison. Returns a record, never
    a verdict -- see NumericComparisonRecord's docstring."""
    return NumericComparisonRecord(
        label=label,
        proposed=proposed,
        required=required,
        unit=unit,
        comparator=comparator,
        citation=citation,
    )


# --------------------------------------------------------------------------- #
# The exception escape hatch -- RUNS BEFORE ANY DISPOSITION.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ReviewContext:
    """The parts of a case's review posture the exception escape hatch
    needs. `review_path` names the pathway the application is proceeding
    under (e.g. 'special_exception', 'variance', 'waiver', or None for the
    ordinary track). `excepted_categories` is the set of standard
    categories that pathway's own Code text excepts from demonstration --
    for Buehner, Shoreland I.M's own preamble names exactly one:
    'excepting structure setback requirements'."""

    review_path: str | None = None
    excepted_categories: frozenset[str] = frozenset()
    exception_citation: Any = None
    exception_reason: str | None = None


@dataclass(frozen=True)
class ExceptionCheckResult:
    excepted: bool
    reason: str | None
    citation: Any


def check_exception_escape_hatch(rule_category: str | None, context: ReviewContext) -> ExceptionCheckResult:
    """Models the Buehner pattern (see module docstring). Called BEFORE any
    disposition is computed for a numeric or boolean criterion -- see
    evaluate_numeric_criterion() below, which never lets raw_satisfied alone
    decide anything. Returns excepted=False (a no-op) whenever the case is
    not proceeding under an exception pathway, or the pathway does not
    except this particular category, so it is always safe to call."""
    if rule_category is None or context.review_path is None:
        return ExceptionCheckResult(excepted=False, reason=None, citation=None)
    if rule_category not in context.excepted_categories:
        return ExceptionCheckResult(excepted=False, reason=None, citation=None)
    reason = context.exception_reason or (
        f"This application proceeds under a {context.review_path.replace('_', ' ')} "
        f"pathway that excepts {rule_category} from what must be demonstrated. "
        "The figures above are stated as facts only; no determination is made here."
    )
    return ExceptionCheckResult(excepted=True, reason=reason, citation=context.exception_citation)


# --------------------------------------------------------------------------- #
# Judgement criteria -> a first-person question to the Board, unresolved=1.
# --------------------------------------------------------------------------- #

# The tells this module (and, at ruleset-build time, the kind classifier) use
# to recognize a judgement standard -- CONTRACT/W6 brief's own list.
JUDGEMENT_TELLS: tuple[str, ...] = (
    "undue",
    "unreasonable",
    "unreasonably",
    "adequate",
    "adequately",
    "excessive",
    "harmonious",
    "reasonably be expected",
    "adverse effect",
    "adversely affect",
)

_JUDGEMENT_TELL_RE = re.compile(
    "|".join(re.escape(t) for t in JUDGEMENT_TELLS), re.IGNORECASE
)


def judgement_tells_found(code_text: str) -> tuple[str, ...]:
    """Which of JUDGEMENT_TELLS actually appear in `code_text`, in source
    order, de-duplicated. Used both to classify a rule's `kind` at ruleset-
    build time and, here, to explain to the Board WHY a standard rendered as
    a question rather than a fact."""
    seen: list[str] = []
    for m in _JUDGEMENT_TELL_RE.finditer(code_text):
        tell = m.group(0).lower()
        if tell not in seen:
            seen.append(tell)
    return tuple(seen)


def render_judgement_question(*, subject: str, code_text: str, citation_display: str | None = None) -> str:
    """A first-person question TO the Board, never an answer. `subject` is a
    short noun phrase for what's being asked about ("the proposed
    subdivision", "the proposed lot layout"). The rendered question quotes
    no verdict -- it asks, and it deliberately avoids the guard's own
    conclusion-verb vocabulary ("meets", "satisfies", "consistent with",
    "complies", ...) so a genuine open question never reads as a disguised
    answer. tests/test_review_engine.py checks this against
    llm.guards.check_conclusion_verbs directly."""
    cite = f" ({citation_display})" if citation_display else ""
    return (
        f'The standard{cite} provides: "{code_text}" '
        f"What is the Board's finding on this standard as applied to {subject}, "
        "and what facts in the record support it?"
    )


# --------------------------------------------------------------------------- #
# Condition wiring -- criterion n. (Flood Areas), fired automatically on
# every subdivision.
# --------------------------------------------------------------------------- #

# VERBATIM -- identical, word for word, in both real subdivision samples:
#   docs/Findings of Fact and Conclusions of Law/
#     M003, L059 (White Rd, Shattuck), Subdivision FoF & CoL 2025.12.18.pdf
#       -- "Conditions of Approval," item 1
#     M004, L084 (Uberoi, 130 Lewis Hill Rd), Subdivision FoF & CoL
#       2024.08.15 DRAFT.pdf -- "Conditions of Approval," item 1
# Do not paraphrase. If this sentence is ever wrong, fix it by re-copying
# from the source PDF, not by editing prose here.
FLOOD_CONDITION_TEXT = (
    "All principal structures proposed on any lot within the subdivision "
    "shall be constructed with their lowest floor, including the basement, "
    "at least three feet above the 100-year flood elevation."
)

FLOOD_CRITERION_RULE_KEY = "art7.12.f.1.n"


@dataclass(frozen=True)
class ConditionRecord:
    rule_id: str | None
    text: str
    mandatory: bool
    source: Literal["engine"]
    reason: str


def fire_flood_condition(*, rule_id: str | None = None) -> ConditionRecord:
    """Fires UNCONDITIONALLY on every subdivision review -- per the W6 brief,
    criterion n. (Flood Areas) mandates this condition regardless of the
    specific parcel's mapped flood-hazard extent, and both real subdivision
    decisions in docs/ attach it. This function takes no case facts and asks
    no question, on purpose: it is boilerplate that rides along with every
    subdivision, not a determination about this one."""
    return ConditionRecord(
        rule_id=rule_id,
        text=FLOOD_CONDITION_TEXT,
        mandatory=True,
        source="engine",
        reason=(
            "Criterion n. (Flood Areas) requires the proposed subdivision plan to include "
            "this condition of plan approval; it is attached automatically to every "
            "subdivision review, not determined case by case."
        ),
    )


# --------------------------------------------------------------------------- #
# Finding -- the unifying record a caller turns into a findings_nodes row.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Finding:
    rule_category: str | None
    disposition: Disposition
    unresolved: bool
    numeric: NumericComparisonRecord | None = None
    exception: ExceptionCheckResult | None = None
    condition: ConditionRecord | None = None
    body: str | None = None  # stated-fact prose, when there is one; never a verdict
    board_question: str | None = None  # first-person question, when there is one


def evaluate_numeric_criterion(
    *,
    label: str,
    rule_category: str,
    proposed: float,
    required: float,
    unit: str,
    comparator: Comparator,
    citation: Any,
    context: ReviewContext | None = None,
) -> Finding:
    """The full numeric path: compare_numeric() first, THEN the exception
    escape hatch, THEN (only if no exception applies) a plain stated fact
    with a question to the Board -- raw_satisfied never drives the
    disposition directly (CONTRACT.md framing rule)."""
    record = compare_numeric(
        label=label, proposed=proposed, required=required, unit=unit,
        comparator=comparator, citation=citation,
    )
    ctx = context or ReviewContext()
    exc = check_exception_escape_hatch(rule_category, ctx)
    if exc.excepted:
        return Finding(
            rule_category=rule_category,
            disposition=Disposition.EXCEPTION_FLAGGED,
            unresolved=True,
            numeric=record,
            exception=exc,
            body=record.as_fact_sentence() + " " + exc.reason,
            board_question=None,
        )
    return Finding(
        rule_category=rule_category,
        disposition=Disposition.FACT_RECORDED,
        unresolved=True,
        numeric=record,
        body=record.as_fact_sentence(),
        board_question=(
            f"What is the Board's finding on the proposed {label.lower()} against this standard?"
        ),
    )


def evaluate_judgement_criterion(*, rule_category: str, subject: str, code_text: str, citation_display: str | None = None) -> Finding:
    """A judgement criterion always renders as a first-person question,
    unresolved=1 -- there is no raw fact to compute here at all."""
    return Finding(
        rule_category=rule_category,
        disposition=Disposition.BOARD_QUESTION,
        unresolved=True,
        body=None,
        board_question=render_judgement_question(
            subject=subject, code_text=code_text, citation_display=citation_display
        ),
    )


def evaluate_flood_condition_criterion(*, rule_id: str | None = None) -> Finding:
    """The condition-wiring path for criterion n. Always CONDITION_ATTACHED;
    never a question, never a fact requiring the Board's judgement -- see
    fire_flood_condition()."""
    cond = fire_flood_condition(rule_id=rule_id)
    return Finding(
        rule_category="flood_areas",
        disposition=Disposition.CONDITION_ATTACHED,
        unresolved=False,
        condition=cond,
        body=cond.reason,
        board_question=None,
    )


def evaluate_procedural_reference(*, rule_category: str, note: str) -> Finding:
    """Standards a. and b. (art7.12.f.1.a/.b): pointers to the rest of the
    Code / the Road, Driveway & Entrance Ordinance, not independently
    testable. Both real subdivision samples handle these as a cross-
    reference rather than a standalone finding."""
    return Finding(
        rule_category=rule_category,
        disposition=Disposition.PROCEDURAL_REFERENCE,
        unresolved=False,
        body=note,
        board_question=None,
    )


def evaluate_not_applicable(*, rule_category: str, subject: str, citation_display: str | None = None) -> Finding:
    """The applicability gate (a separate component) determined this
    standard's subject matter is absent from this application. Reuses the
    real house phrasing from the sample decisions where it fits (W6 brief):
    'The standard set forth under {article} do not address, and therefore
    do not apply to, {subject}.'"""
    cite = citation_display or "this Article"
    return Finding(
        rule_category=rule_category,
        disposition=Disposition.NOT_APPLICABLE,
        unresolved=False,
        body=f"The standard set forth under {cite} do not address, and therefore do not apply to, {subject}.",
        board_question=None,
    )


def evaluate_applicability_unknown(*, rule_category: str, code_text: str, citation_display: str | None = None) -> Finding:
    """UNKNOWN NEVER SUPPRESSES A NODE (W6 brief). The standard still
    renders, verbatim, and the Board is asked to resolve applicability
    itself -- this is deliberately the same shape as a judgement question,
    because from the app's point of view both are 'the app cannot answer
    this, so it asks.'"""
    cite = f" ({citation_display})" if citation_display else ""
    return Finding(
        rule_category=rule_category,
        disposition=Disposition.APPLICABILITY_UNKNOWN,
        unresolved=True,
        body=None,
        board_question=(
            f'It could not be determined from the application whether the standard{cite} — '
            f'"{code_text}" — applies to this proposal. Does the Board find that it applies, '
            f"and if so, what is its finding on the record before it?"
        ),
    )


__all__ = [
    "Comparator",
    "Disposition",
    "NumericComparisonRecord",
    "compare_numeric",
    "ReviewContext",
    "ExceptionCheckResult",
    "check_exception_escape_hatch",
    "JUDGEMENT_TELLS",
    "judgement_tells_found",
    "render_judgement_question",
    "FLOOD_CONDITION_TEXT",
    "FLOOD_CRITERION_RULE_KEY",
    "ConditionRecord",
    "fire_flood_condition",
    "Finding",
    "evaluate_numeric_criterion",
    "evaluate_judgement_criterion",
    "evaluate_flood_condition_criterion",
    "evaluate_procedural_reference",
    "evaluate_not_applicable",
    "evaluate_applicability_unknown",
    "contains_banned_verdict_language",
]
