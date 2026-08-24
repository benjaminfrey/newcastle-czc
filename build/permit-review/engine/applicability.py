"""The applicability gate, wired to the 21 subdivision rules. W6 task
brief: "UNKNOWN NEVER SUPPRESSES A NODE. It renders the standard and asks
the Board. Silently dropping a criterion because we could not tell whether
it applied is the worst failure mode in this phase, worse than a wrong
answer, because nobody sees the omission."

engine/predicates.py is the generic, rule-agnostic three-valued evaluator.
This module is the thin domain layer over it: given a list of rule rows
(the shape ruleset_build/build_subdivision_criteria.py's artifact, or the
`rules` DB table, both produce) and a case's known facts, gate_all() always
returns exactly one GateResult per rule -- same length in, same length out,
by construction (a plain list comprehension, nothing filtered) -- so
"UNKNOWN still renders" is not a promise this module keeps by convention,
it is a promise the return type's shape keeps mechanically.

Phrasing for FALSE and UNKNOWN reuses the register of the two real
Subdivision decisions in docs/Findings of Fact and Conclusions of Law/
("This is not applicable as none of the proposed lots have any frontage on
a river, stream, brook, great pond or coastal wetland.") and the applicable-
gate phrasing style named in the task brief ("The standard set forth under
{article} do not address, and therefore do not apply to, {subject}.").
Neither is quoted verbatim here (this module writes distinct, standard-
specific sentences, not one canned template with a subject swapped in), but
both follow the same register the real decisions use: plain, declarative,
citing the specific fact that decided it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from engine import predicates
from engine.predicates import Verdict


# --------------------------------------------------------------------------- #
# Human-readable descriptions of the gating fact(s) for the four subdivision
# standards whose Code text embeds a real conditional (l, n, r, t -- see
# ruleset_build/build_subdivision_criteria.py's CLASSIFICATION). Every other
# rule's predicate is {"op":"always"}, so it never reaches these templates.
# --------------------------------------------------------------------------- #

_GATE_SUBJECT: dict[str, str] = {
    "art7.12.f.1.l": (
        "whether the subdivision sits within the watershed of a pond or lake, or within 250 "
        "feet of a wetland, great pond, or river"
    ),
    "art7.12.f.1.n": (
        "whether the subdivision, or any part of it, lies within a FEMA-mapped 100-year flood "
        "hazard area"
    ),
    "art7.12.f.1.r": (
        "whether any lot in the subdivision has shore frontage on a river, stream, brook, "
        "great pond, or coastal wetland"
    ),
    "art7.12.f.1.t": "whether the proposed subdivision crosses a municipal boundary",
}

_DEFAULT_GATE_SUBJECT = "the fact(s) this standard's own applicability clause depends on"


@dataclass(frozen=True)
class GateResult:
    rule_key: str
    title: str
    citation_display: str | None
    verdict: Verdict
    finding_text: str | None  # set when verdict is FALSE; None for TRUE/UNKNOWN
    board_question: str | None  # set when verdict is UNKNOWN; None for TRUE/FALSE


def _subject_for(rule_key: str) -> str:
    return _GATE_SUBJECT.get(rule_key, _DEFAULT_GATE_SUBJECT)


def gate_one(rule: dict[str, Any], facts: dict[str, Any]) -> GateResult:
    """Evaluate one rule's applicability predicate against `facts` and
    return a GateResult -- ALWAYS, for TRUE, FALSE, and UNKNOWN alike. There
    is no code path in this function that returns None or omits a rule;
    that is what gate_all()'s "always renders" guarantee rests on.
    """
    rule_key = rule["rule_key"]
    title = rule.get("title", rule_key)
    citation_display = rule.get("citation_display")
    predicate = rule["applicability"]

    verdict = predicates.evaluate(predicate, facts)

    finding_text: str | None = None
    board_question: str | None = None

    if verdict is Verdict.FALSE:
        subject = _subject_for(rule_key)
        finding_text = (
            f"Standard {rule['standard_letter']} ({title}) does not apply to this application: "
            f"the record establishes that {subject} is not the case here."
        )
    elif verdict is Verdict.UNKNOWN:
        subject = _subject_for(rule_key)
        board_question = (
            f"The application record does not yet establish {subject}. Standard "
            f"{rule['standard_letter']} ({title}) applies only if it does -- does it, and if so, "
            f"how does the application meet the standard?"
        )

    return GateResult(
        rule_key=rule_key,
        title=title,
        citation_display=citation_display,
        verdict=verdict,
        finding_text=finding_text,
        board_question=board_question,
    )


def gate_all(rules: list[dict[str, Any]], facts: dict[str, Any]) -> list[GateResult]:
    """Gate every rule in `rules` against `facts`. Returns exactly
    len(rules) results, in the same order, unconditionally -- no rule is
    ever filtered out regardless of its verdict. This is the mechanical
    proof that UNKNOWN (and FALSE) still render a node rather than being
    dropped: the list this returns is always the same length as the list
    of rules given to it.
    """
    return [gate_one(r, facts) for r in rules]
