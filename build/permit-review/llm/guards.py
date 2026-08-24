"""The LLM output guards (W5 item 3 -- CONTRACT.md §1's safety posture
applied to model-generated prose). Three were the original W5 scope;
`check_residual_placeholders` (guard 4) was added in the post-gate repair
pass that fixed critic findings A3.1/A2.1/A4.3 -- see its own docstring.

CONTRACT.md never says a model may draft a document unsupervised, and this
project's whole design reframe is that it never will: the app produces the
working draft the Board marks up, it never concludes and it never signs
(README task brief; see also findings_nodes.conclusion, which is nullable
and ships NULL -- CONTRACT.md §3.6). Every sentence an `LLMClient` provider
returns is a *request*, not a fact. These functions are the guarantee
that sits between that request and anything a reader sees:

  1. `check_numeral_grounding`  -- every numeral in the text must already be
     a known fact. An ungrounded numeral is a fabrication risk, full stop.
  2. `strip_and_rerender_citations` -- a citation is never trusted from the
     model. Whatever citation-shaped text the model wrote is stripped; the
     real citation (if any) is re-rendered from `app/citation.py`, the
     project's ONLY citation renderer (CONTRACT.md §5.1). Case-insensitive
     (A3.1): a lowercase "article 7, section 15.d" is stripped exactly like
     "Article 7, Section 15.D" -- a model's casing choice is not a safety
     boundary.
  3. `check_conclusion_verbs` -- language that asserts compliance/non-
     compliance ("complies", "is consistent with", "fails to meet", ...)
     downgrades the node to a Board flag. The app has no `met`/`not_met`
     value anywhere (CONTRACT.md §3.6); this guard is what keeps that true
     even when the sentence came out of a model instead of a human. The
     modal-obligation exclusion ("must comply with ...") is scoped to the
     CLAUSE, not the whole sentence (A2.1): a modal earlier in a compound
     sentence must not swallow a real conclusion in a later clause.
  4. `check_residual_placeholders` -- a `[REDACTED_..._N]` placeholder still
     present in text AFTER `llm/redact.py`'s restore step (A4.3) means the
     model referenced a redacted token this call gave it no real grounds to
     use; the node is flagged rather than let through as clean prose.

Each guard is silent on a clean paragraph and loud on a bad one -- see
tests/test_guards.py, which tests every guard BOTH directions, plus one
paragraph that must clear all four untouched. Over-flagging is the safe
failure (a human looks at one more node); under-flagging is not (a false
"complies" reaches the Board). Where a rule below had to pick a side, it
picked over-flagging -- each such call is logged in this module's comments
where the ambiguity actually is, not buried in a commit message.

WHY THIS FILE HAS NO DEPENDENCY ON `llm/`'s OTHER MODULES (`LLMClient`,
providers, `redact.py`, cassette replay, few-shot indexing, vision). This
module takes plain `str` in and structured results out; it does not know or
care whether the text came from the `null` provider, a `recorded` cassette,
or (eventually) `anthropic`. That is deliberate -- the guard must work
identically on every provider.

ORDER MATTERS: run citation stripping BEFORE numeral grounding. An
unstripped "Article 7, Section 15.D" contains the bare numerals 7 and 15,
which are almost never in a case's fact set and would spuriously flag the
sentence for the wrong reason. `run_guards()` below enforces this order;
call the two functions separately in the other order at your own risk.

THE NINE REAL DECISIONS. The conclusion-verb list and the modal-exclusion
rule were both read off the actual language of the nine sample Findings of
Fact & Conclusions of Law in `docs/Findings of Fact and Conclusions of
Law/` (Buehner, Verney, Blood & Sons, Midcoast Solar, Shattuck, Profenno,
Uberoi, Morrissey, Academy Hill -- Dalton and Stantec are applications only,
held out with no matching decision yet, per BUILD-STATE.md's W8 eval plan).
Two house-style facts came directly out of that reading:
  - "is/are consistent with" is the Board's dominant conclusion phrasing
    (Shattuck's Conclusions of Law repeats it once per Article/standard --
    "Motion: To conclude that the application is consistent with Article 2
    of the Core Zoning Code.") -- more common in this corpus than "complies".
  - "must comply with" / "must meet the ... standards" is common Code-
     quotation phrasing ("All primary buildings must comply with required
     front, side, and rear setback standards.", "Driveways must comply with
     the Roads, Driveways and Entrances Ordinance.") and is NOT a conclusion
     -- it is the requirement being stated, not an assertion that this
     application meets it. The modal-exclusion rule below exists because of
     these exact sentences.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Sequence

from app.citation import Citation, render as render_citation

__all__ = [
    "NumeralFinding",
    "GroundingResult",
    "check_numeral_grounding",
    "CitationStripResult",
    "strip_and_rerender_citations",
    "ConclusionMatch",
    "ConclusionGuardResult",
    "check_conclusion_verbs",
    "ResidualPlaceholderMatch",
    "ResidualPlaceholderResult",
    "check_residual_placeholders",
    "GuardReport",
    "run_guards",
]


# --------------------------------------------------------------------------- #
# Shared: a decimal-point-safe sentence splitter
# --------------------------------------------------------------------------- #

# A private-use codepoint stands in for a decimal '.' while we look for
# sentence boundaries, so "The setback is 74.2 ft. This complies." does not
# split into "...74" / "2 ft. This complies." -- the substitution is exactly
# one character for one character, so every offset below still lines up with
# the ORIGINAL text (we always slice `text`, never the protected copy).
_DECIMAL_GUARD = ""
_DECIMAL_DOT_RE = re.compile(r"(?<=\d)\.(?=\d)")
_SENTENCE_BOUNDARY_RE = re.compile(r"[.!?]+(?:\s+|$)")


def _split_sentences(text: str) -> list[tuple[str, int, int]]:
    """Return (sentence_text, start, end) triples covering `text`. Sentence
    text is stripped of surrounding whitespace; start/end are offsets into
    the ORIGINAL (unmodified) `text`."""
    protected = _DECIMAL_DOT_RE.sub(_DECIMAL_GUARD, text)
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _SENTENCE_BOUNDARY_RE.finditer(protected):
        end = m.end()
        spans.append((start, end))
        start = end
    if start < len(text):
        spans.append((start, len(text)))
    out = []
    for s, e in spans:
        seg = text[s:e].strip()
        if seg:
            out.append((seg, s, e))
    return out


def _sentence_for(sentences: list[tuple[str, int, int]], offset: int) -> tuple[str, int, int]:
    for seg, s, e in sentences:
        if s <= offset < e:
            return seg, s, e
    # Fall back to the last sentence span if a match somehow lands outside
    # every one (shouldn't happen -- _split_sentences covers [0, len(text))).
    return sentences[-1] if sentences else ("", 0, 0)


# --------------------------------------------------------------------------- #
# Guard 1 -- numeral grounding
# --------------------------------------------------------------------------- #

# `(?<![A-Za-z])` on the left keeps this from matching digits glued to a
# letter code -- "D1", "S2", "L053", "M002" are identifiers, not numerals a
# fact set would ever hold, and treating "1" out of "D1" as an ungrounded
# numeral would flag every sentence that names a district or a tax lot.
# Longer alternatives are tried first so "74 1/2" and "1,330.50" match whole
# rather than fragmenting into "74" + "1/2" or "1" + ",330.50".
NUMERAL_TOKEN_RE = re.compile(
    r"""
    (?<![A-Za-z])
    (?:
        \d+\s+\d+/\d+                     # mixed fraction: 74 1/2
      | \d+/\d+                           # bare fraction: 1/2
      | \d{1,3}(?:,\d{3})+(?:\.\d+)?      # thousands-grouped: 1,330 / 1,330.50
      | \d+\.\d+                          # decimal: 74.2
      | \d+                               # integer
    )
    """,
    re.VERBOSE,
)

_MIXED_FRACTION_RE = re.compile(r"^(\d+)\s+(\d+)/(\d+)$")
_FRACTION_RE = re.compile(r"^(\d+)/(\d+)$")


def _normalize_numeral(raw: str) -> Decimal:
    """Parse one NUMERAL_TOKEN_RE match into a Decimal, handling the three
    formatting variances this guard is required to handle honestly: a
    thousands separator (1,330 -> 1330), a trailing zero (74.20 == 74.2,
    which Decimal equality already gives us for free), and a foot-inch
    fraction (74 1/2 -> 74.5, 1/2 -> 0.5)."""
    raw = raw.strip()
    m = _MIXED_FRACTION_RE.match(raw)
    if m:
        whole, num, den = m.groups()
        return Decimal(whole) + Decimal(num) / Decimal(den)
    m = _FRACTION_RE.match(raw)
    if m:
        num, den = m.groups()
        return Decimal(num) / Decimal(den)
    return Decimal(raw.replace(",", ""))


def _extract_fact_numerals(fact_set: Iterable[Any]) -> set[Decimal]:
    """The fact set is whatever mix of raw numbers and fact strings the
    caller has on hand for this case (dimensional field values, application
    figures, ...) -- e.g. `["2.1 Acres", "~650 ft", 50, Decimal("74.5")]`.
    Every numeral token found anywhere in it, by the same extraction rule
    used on the model's text, becomes a grounding fact. This is deliberately
    permissive about WHERE a fact came from (a plain number or a sentence
    with a number embedded in it) and NOT permissive about matching (no
    tolerance, no rounding -- see `check_numeral_grounding`)."""
    facts: set[Decimal] = set()
    for item in fact_set:
        s = str(item)
        for m in NUMERAL_TOKEN_RE.finditer(s):
            try:
                facts.add(_normalize_numeral(m.group(0)))
            except InvalidOperation:
                continue
    return facts


@dataclass(frozen=True)
class NumeralFinding:
    raw: str
    value: Decimal
    start: int
    end: int
    grounded: bool
    sentence: str


@dataclass(frozen=True)
class GroundingResult:
    findings: tuple[NumeralFinding, ...]
    ungrounded_sentences: tuple[str, ...]
    unresolved: bool  # True iff at least one numeral in `text` is not in `fact_set`


def check_numeral_grounding(text: str, fact_set: Iterable[Any] = ()) -> GroundingResult:
    """CONTRACT.md's S10 ("anything derivable is computed, never typed in")
    applied to model prose: every numeral the model wrote must already exist
    in the fact set the app handed it. A numeral that doesn't ground is not
    corrected or dropped -- the whole SENTENCE it's in is flagged, and the
    caller is expected to set `unresolved=1` on the node (CONTRACT.md §3.6)
    rather than let the sentence stand. Run this AFTER
    `strip_and_rerender_citations` -- see the module docstring."""
    facts = _extract_fact_numerals(fact_set)
    sentences = _split_sentences(text)
    findings: list[NumeralFinding] = []
    ungrounded_sentences: list[str] = []
    for m in NUMERAL_TOKEN_RE.finditer(text):
        raw = m.group(0)
        try:
            value = _normalize_numeral(raw)
        except InvalidOperation:
            continue
        grounded = value in facts
        sent, _, _ = _sentence_for(sentences, m.start())
        findings.append(NumeralFinding(raw, value, m.start(), m.end(), grounded, sent))
        if not grounded and sent not in ungrounded_sentences:
            ungrounded_sentences.append(sent)
    return GroundingResult(tuple(findings), tuple(ungrounded_sentences), unresolved=bool(ungrounded_sentences))


# --------------------------------------------------------------------------- #
# Guard 2 -- citation stripping
# --------------------------------------------------------------------------- #

# Matches the citation-shaped substrings a model might emit, in the exact
# forms `app/citation.py` itself renders (see its module docstring and
# CONTRACT.md §5.5's golden strings) plus the bare "Section N" / "§N" forms
# a model is just as likely to produce. Deliberately does NOT try to catch a
# bare district code ("D1") or a use label -- those are plain data values,
# not a citation to Code TEXT, and app/citation.py's own golden forms never
# render a district alone without an "Article N" anchor.
#
# re.IGNORECASE (critic finding A3.1): a model is not guaranteed to emit
# "Article"/"Section"/"Table"/"Exhibit" title-cased -- "article 7, section
# 15.d" is exactly as much a model-authored citation as "Article 7, Section
# 15.D" and CONTRACT.md §5.1 ("a model-authored string that looks like a
# citation is a bug") does not carve out an exception for casing. Without
# this flag a lowercase citation sailed straight through unstripped.
CITATION_SHAPE_RE = re.compile(
    r"""
    (?:Article|Art\.)\s*\d+                                        # Article 7 / Art. 7
    (?:\s*,\s*(?:Section|Sec\.)\s*\d+(?:\.[A-Za-z0-9]+)*)?          # , Section 12.b / , Sec. 3.B
    (?:\s*,\s*Standard\s+[A-Za-z0-9]+\.?(?:\s*\([^()]*\))?)?        # , Standard n. (Flood Areas)
    |
    §\s*\d+(?:\.[A-Za-z0-9]+)*                                     # §12.b
    |
    \bTable\s+\d+\.\d+\b                                           # Table 3.5
    |
    \bExhibit\s+\d+\.\d+\b                                         # Exhibit 3.1
    |
    \b(?:Section|Sec\.)\s*\d+(?:\.[A-Za-z0-9]+)*\b                 # bare "Section 12.b" (no "Article" prefix)
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _cleanup_after_strip(s: str) -> str:
    """Removing a citation leaves punctuation debris behind ("...required by
    Article 7, Section 15.D." -> "...required by ."); this is a plain text
    tidy-up, not a re-parse of anything."""
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\(\s*\)", "", s)          # empty parens ("(Flood Areas)" fully consumed)
    s = re.sub(r"\s+([,.;:])", r"\1", s)   # no space before punctuation
    s = re.sub(r"(,\s*)+([.;:])", r"\2", s)  # ", ." / ", ," -> "."
    s = re.sub(r"([,;:])(\s*\1)+", r"\1", s)  # collapse repeated punctuation
    s = re.sub(r"^\s*[,.;:]\s*", "", s)    # leading stray punctuation
    return s.strip()


@dataclass(frozen=True)
class CitationStripResult:
    text: str                        # citation-shaped text removed, real citation(s) appended
    stripped_raw: tuple[str, ...]    # the exact substrings removed -- audit only, never shown to a reader
    had_model_citation: bool
    rendered: tuple[str, ...]        # what app/citation.py rendered in their place (empty if none supplied)


def strip_and_rerender_citations(
    text: str,
    citations: Sequence[Citation] = (),
    *,
    style: str = "long",
) -> CitationStripResult:
    """CONTRACT.md §5.1: 'The LLM layer MUST NOT emit citation text ... a
    model-authored string that looks like a citation is a bug.' This
    function is the enforcement: it removes every citation-shaped substring
    the model wrote (`stripped_raw`, kept only for an audit trail -- never
    reassembled or trusted), then appends the REAL citation(s) for this node
    -- rendered exclusively by `app.citation.render()`, never reconstructed
    from what was stripped. `citations` must come from the app's own rule/
    fact data (the Citation struct the engine already built for this node),
    never inferred from the model's text -- there is nothing here that
    parses a stripped string back into a Citation, on purpose."""
    stripped_raw: list[str] = []

    def _strip(m: re.Match[str]) -> str:
        stripped_raw.append(m.group(0))
        return " "

    cleaned = CITATION_SHAPE_RE.sub(_strip, text)
    cleaned = _cleanup_after_strip(cleaned)

    rendered = tuple(render_citation(c, style=style) for c in citations)
    if rendered:
        cleaned = f"{cleaned} ({'; '.join(rendered)})" if cleaned else "; ".join(rendered)

    return CitationStripResult(
        text=cleaned,
        stripped_raw=tuple(stripped_raw),
        had_model_citation=bool(stripped_raw),
        rendered=rendered,
    )


# --------------------------------------------------------------------------- #
# Guard 3 -- conclusion-verb downgrade
# --------------------------------------------------------------------------- #

# A modal-obligation word ('must', 'shall', 'should', 'needs to', 'is
# required to') immediately before a conclusion-shaped phrase, IN THE SAME
# CLAUSE, means the clause is stating a REQUIREMENT ("Driveways must
# comply with the Roads, Driveways and Entrances Ordinance.") -- not
# asserting that this application satisfies it. Both quoted sentences are
# real, verbatim, from the Blood & Sons and Verney decisions.
#
# WIDENED 2026-08-24 (W8 over-conclusion round) to also cover "will be
# required to" / "was required to" / etc, not just the bare "is/are
# required to" the guard previously matched. Real corpus trigger: Shattuck
# and Uberoi both write "...future development of the proposed lots will be
# required to conform with all State and local regulations..." -- a
# requirement statement about FUTURE development, not this application's
# own compliance -- and the new "conform_to"/"conformance_conformity"
# conclusion patterns below would otherwise false-positive on it every
# time, exactly the false-alarm-fatigue failure mode this file's own
# docstring warns against.
_MODAL_RE = re.compile(
    r"\b(?:must|shall|should|needs?\s+to|will\s+need\s+to|"
    r"(?:is|are|was|were|will|would)\s+(?:be\s+)?required\s+to)\b",
    re.IGNORECASE,
)

# Clause boundary for the modal-exclusion scope (critic finding A2.1): a
# comma, semicolon, or colon inside the CURRENT sentence starts a new
# clause. Restricting the search to the same SENTENCE (the original
# design) was already right for "The application must be complete. It
# complies with the setback standard." (two sentences -- "must" must NOT
# reach across the period) but was still too wide inside one sentence: "The
# driveway must meet the required standards, but the application does not
# meet the required setback." is ONE sentence with TWO clauses -- the modal
# governs only the Code-requirement clause before the comma, and the
# conclusion after it must still fire. Searching the whole sentence prefix
# let an earlier, unrelated modal silently swallow a real conclusion later
# in the same sentence.
#
# Protects thousands-separated numerals the same way `_split_sentences`
# protects decimal points above: "1,200" must never be misread as a clause
# boundary between "1" and "200 sq ft", which would spuriously narrow the
# search window and flip an otherwise-excluded modal sentence into a false
# positive.
_THOUSANDS_COMMA_RE = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_CLAUSE_BOUNDARY_RE = re.compile(r"[,;:]")


def _modal_governs(text: str, sent_start: int, match_start: int) -> bool:
    """True iff a modal-obligation word governs the CLAUSE immediately
    preceding `match_start` (bounded below by `sent_start`, the enclosing
    sentence's own start -- a modal never reaches across a sentence
    boundary either)."""
    preceding = text[sent_start:match_start]
    protected = _THOUSANDS_COMMA_RE.sub(_DECIMAL_GUARD, preceding)
    last_boundary = 0
    for m in _CLAUSE_BOUNDARY_RE.finditer(protected):
        last_boundary = m.end()
    clause = preceding[last_boundary:]
    return bool(_MODAL_RE.search(clause))

# Each pattern is a phrase this project's real decisions (or the task brief
# that commissioned this guard) use to assert a compliance/non-compliance
# merits conclusion. "meets"/"not meet" allow a short word-gap before the
# standard/requirement/definition noun because the real usage does too --
# e.g. Midcoast Solar: "the solar arrays will meet the Primary Building and
# Accessory Building setback requirements." Deliberately does NOT include a
# bare "meets"/"fails"/"finds"/"determines"/"adequate" with no complement --
# see the module docstring and this file's BORDERLINE VERBS note below for
# why each was left out, and what would have to change to add it back.
_CONCLUSION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("comply_negative", re.compile(r"\bdoes?\s+not\s+comply\s+with\b", re.IGNORECASE)),
    ("comply_positive", re.compile(r"\bcomplies\s+with\b", re.IGNORECASE)),
    ("compliance_state", re.compile(
        r"\b(?:is|are|was|were|would\s+be|will\s+be|could\s+be|can\s+be)\s+(?:not\s+)?in\s+compliance\s+with\b",
        re.IGNORECASE)),
    ("satisfy", re.compile(r"\bsatisf(?:y|ies|ied)\b", re.IGNORECASE)),
    ("fails_to", re.compile(r"\bfails?\s+to\s+(?:meet|comply|satisfy)\b", re.IGNORECASE)),
    ("not_meet", re.compile(r"\bdoes?\s+not\s+meet\b", re.IGNORECASE)),
    ("meets_standard", re.compile(
        r"\bmeets?\s+(?:\w+\s+){0,8}?(?:standards?|requirements?|definitions?)\b", re.IGNORECASE)),
    ("consistent", re.compile(r"\b(?:is|are|was|were)\s+(?:not\s+)?consistent\s+with\b", re.IGNORECASE)),
    ("inconsistent", re.compile(r"\binconsistent\s+with\b", re.IGNORECASE)),
    ("conclude", re.compile(r"\bconclude[sd]?\s+that\b", re.IGNORECASE)),
    ("adversely_affect", re.compile(r"\bwill\s+(?:not\s+)?adversely\s+affect\b", re.IGNORECASE)),
    # "will (not) have {a|no} (undue) adverse impact/effect on X" -- the
    # SAME merits-conclusion shape as "adversely_affect" above, different
    # verb ("have ... impact/effect" vs "affect"). Real, verbatim: Buehner
    # ("Will not have an adverse impact on spawning grounds, fish, aquatic
    # life, bird or other wildlife habitat"), Shattuck and Uberoi both
    # ("...will not have an undue adverse effect on the scenic or natural
    # beauty of the area"). The "no" alternative (matching the task brief's
    # own worked example, "will have no adverse impact") is the SAME claim
    # phrased as a determiner instead of a negated verb -- "will have no X"
    # and "will not have an X" assert the identical thing.
    ("have_adverse_impact", re.compile(
        r"\bwill\s+(?:not\s+have|have\s+no)\s+(?:an?\s+)?(?:undue\s+)?adverse\s+(?:impact|effect)s?\s+on\b",
        re.IGNORECASE)),
    # --- Added 2026-08-24 (W8 over-conclusion round) -- read the module
    # docstring's THE NINE REAL DECISIONS section before touching these.
    # Each was found by grepping the real extracted text of all nine
    # decisions (not invented) and confirmed missed by the pre-existing
    # pattern set (2 of 12 real dodge phrasings caught before this pass --
    # see tests/test_over_conclusion_dodges.py, which is the literal proof
    # this docstring claim rests on, not a description of it).
    ("conform_to", re.compile(r"\bconforms?\s+(?:to|with)\b", re.IGNORECASE)),
    # "in conformance with" / "in conformity with" -- real, verbatim, Buehner
    # ("Is in conformance with the provisions of Article III") and the
    # boilerplate opening every one of the nine decisions repeats ("...may
    # be undertaken unless in conformity with this Code"). The second real
    # use is itself a general procedural statement, not a per-application
    # merits conclusion, but it carries no modal this guard can key off of
    # -- flagged here as a genuine, accepted over-flagging risk (the safe
    # failure per this file's own docstring) rather than silently excluded;
    # see BORDERLINE VERBS below.
    ("conformance_conformity", re.compile(r"\bin\s+conform(?:ance|ity)\s+with\b", re.IGNORECASE)),
    # "will (not) cause/result in an unreasonable X" -- the DOMINANT
    # conclusion phrasing in both real subdivision decisions on file
    # (Shattuck, Uberoi repeat "The proposed subdivision will not cause
    # unreasonable soil erosion" / "...an unreasonable burden on..." for
    # SEVEN separate standards each) and structurally identical to the
    # already-included "adversely_affect" pattern just above -- this is the
    # single biggest real gap the pre-existing pattern set had.
    ("cause_or_result_in_unreasonable", re.compile(
        r"\bwill\s+(?:not\s+)?(?:cause|result\s+in)\s+(?:an?\s+)?unreasonable\b", re.IGNORECASE)),
    # Passive-voice reorder of the existing "meets_standard" pattern (which
    # requires the active-voice "meets ... standard" word order and misses
    # its own passive form). Real, verbatim, Academy Hill Z38: "Overview
    # explanation of how applicable standards are met." "satisfied" is
    # already covered by the bare "satisfy" pattern above; "met" was not
    # covered in ANY word order until this pattern.
    ("standard_met_passive", re.compile(
        r"\b(?:standards?|requirements?|criteria)\s+(?:is|are|was|were|has\s+been|have\s+been)\s+met\b",
        re.IGNORECASE)),
)

# --- BORDERLINE VERBS -- logged, not guessed away ---------------------------
#
# "adequate" / "adequately" -- appears constantly in the real decisions
#   ("Adequate access for emergency vehicles will be provided", "will
#   adequately provide for the disposal of all waste") but ALSO as the
#   Code's own standard wording, quoted verbatim ("Private Roads shall
#   provide and maintain adequate access for emergency vehicles"). A trigger
#   here would fire on a clean paragraph that only quotes the standard by
#   name -- exactly the false-alarm-fatigue failure mode the task brief
#   warns against. EXCLUDED from the default set.
#
# "find" / "finds" / "found" -- the dominant real use is a PROCEDURAL
#   completeness finding ("The Planning Board finds the Application to be
#   complete as of April 17, 2025"), which the app is expected to produce
#   (it is literally the "Findings of Fact" section). A bare "finds" trigger
#   would downgrade routine, correct output. EXCLUDED.
#
# "determine" / "determined" / "determination" -- used constantly for
#   ordinary procedural/factual actions ("the Planning Board must determine
#   if the application is complete", "the subdivider will determine the
#   100-year flood elevation") as well as, occasionally, a merits
#   conclusion ("determined to be in compliance with the Road, Driveway, and
#   Entrance Ordinance"). EXCLUDED as its own trigger -- but nothing is lost:
#   every merits-conclusion use found in the corpus pairs "determine(d)"
#   with a phrase already on the list above ("in compliance with",
#   "consistent with"), so those sentences still fire on that phrase.
#
# "will (not) adversely affect" -- INCLUDED, the one call that went the
#   other way. It is literally the wording of several subdivision standards
#   (Article 2-B water-quality criteria), so a sentence using it is by
#   definition asserting that a specific legal test is met -- exactly the
#   merits conclusion this guard exists to catch, even though catching it
#   means a paragraph that quotes the standard's own name risks a flag too.
#
# "in conformance with" / "in conformity with" -- INCLUDED 2026-08-24, the
#   same call as "adversely affect" above and for the same reason, WITH a
#   known, accepted over-flagging risk logged rather than hidden: every one
#   of the nine real decisions opens its Core Zoning Code Review section
#   with "No development activity contemplated by this Code may be
#   undertaken unless in conformity with this Code" -- boilerplate
#   procedural framing, not a per-application merits conclusion, and it
#   carries no modal word this guard's clause-scoped exclusion can key off
#   of ("may be undertaken unless" is not on _MODAL_RE, and adding it would
#   be too broad -- "unless" governs a huge range of unrelated clauses).
#   This sentence WILL flag under the new pattern. That is the accepted,
#   safe-side failure this file's own docstring names ("over-flagging is
#   the safe failure... under-flagging is not"): one more Board-reviewed
#   node on a sentence that turns out to be boilerplate costs a human one
#   extra glance; silently excluding "in conformance with" to avoid that
#   glance would also silently un-flag Buehner's REAL per-application use
#   ("Is in conformance with the provisions of Article III") -- and that
#   one is exactly what the guard exists to catch. Logged here rather than
#   guessed away, per this section's own header.
#
# Any future verb added to the default set should get the same treatment:
# a real quote showing the conclusory use, and a real quote showing the
# requirement-statement use if one exists, before it goes in.


@dataclass(frozen=True)
class ConclusionMatch:
    category: str
    matched_text: str
    start: int
    end: int
    sentence: str


@dataclass(frozen=True)
class ConclusionGuardResult:
    matches: tuple[ConclusionMatch, ...]
    board_flag: bool  # True iff `text` contains at least one un-excluded conclusion-verb match


def check_conclusion_verbs(text: str) -> ConclusionGuardResult:
    """The app never concludes (CONTRACT.md §3.6: findings_nodes.conclusion
    is nullable and ships NULL; there is no met/not_met column). Output
    containing 'complies', 'satisfies', 'fails', 'meets the standard', 'does
    not meet' and the house-style equivalents found in the real decisions
    ('is/are consistent with', 'in compliance with', 'concludes that', ...)
    downgrades the node: the caller should set `unresolved=1` and route the
    text to a Board flag rather than let it stand as prose (CONTRACT.md
    §3.6's `board_question` is exactly that routing target). A modal-
    obligation CLAUSE stating what the Code REQUIRES, not what this
    application achieved, is excluded -- see `_MODAL_RE` / `_modal_governs`
    above. The exclusion is scoped to the clause, not the whole sentence: a
    modal in an earlier clause of the same sentence must not swallow a real
    conclusion in a later one."""
    sentences = _split_sentences(text)
    matches: list[ConclusionMatch] = []
    for category, pattern in _CONCLUSION_PATTERNS:
        for m in pattern.finditer(text):
            sent, sent_start, _ = _sentence_for(sentences, m.start())
            if _modal_governs(text, sent_start, m.start()):
                continue
            matches.append(ConclusionMatch(category, m.group(0), m.start(), m.end(), sent))
    matches.sort(key=lambda mm: mm.start)
    return ConclusionGuardResult(tuple(matches), board_flag=bool(matches))


# --------------------------------------------------------------------------- #
# Guard 4 -- residual redaction placeholder (critic finding A4.3)
# --------------------------------------------------------------------------- #

# Mirrors `llm/redact.py:_PLACEHOLDER_RE` exactly (not imported -- see the
# module docstring above on why this file has no dependency on `llm/`'s
# other modules; the shape is a small, stable contract between the two
# files, not a reason to couple them).
#
# WHY THIS GUARD EXISTS. `redact.py:restore_text()` is deliberately
# EXACT-STRING, never fuzzy (CONTRACT.md §1.1 S7): a placeholder the model
# reproduced with the wrong case/spacing, or invented outright (e.g. a case
# with exactly one known NAME, so `token_map` only ever holds
# "[REDACTED_NAME_1]", but the model's answer talks about
# "[REDACTED_NAME_2]"), is left untouched by restore() rather than guessed
# at. That is the right call for restore() itself, but it means the raw
# bracketed placeholder text can otherwise reach a reader completely
# unremarked -- either as literal internal-format junk in a Board document,
# or, more dangerously, silently woven into a sentence that reads as a
# normal, confident assertion once nearby text IS restored around it. A
# residual placeholder is proof the model referenced a redacted token this
# call gave it no real grounds to use, exactly like an ungrounded numeral
# (guard 1) is proof of a number with no real grounds -- so it gets the
# same treatment: flag the node, never let it stand as clean prose.
#
# RUN THIS ON TEXT *AFTER* `RedactionResult.restore()` / `restore_text()`.
# The pre-restore, still-redacted text is EXPECTED to be full of real
# placeholders -- running this guard there would flag every single call.
_RESIDUAL_PLACEHOLDER_RE = re.compile(r"\[REDACTED_[A-Z]+_\d+\]")


@dataclass(frozen=True)
class ResidualPlaceholderMatch:
    matched_text: str
    start: int
    end: int
    sentence: str


@dataclass(frozen=True)
class ResidualPlaceholderResult:
    matches: tuple[ResidualPlaceholderMatch, ...]
    unresolved: bool  # True iff at least one [REDACTED_..._N] placeholder remains in `text`


def check_residual_placeholders(text: str) -> ResidualPlaceholderResult:
    """See the module-level comment above `_RESIDUAL_PLACEHOLDER_RE` for
    why this guard exists and when to call it (post-restore text only)."""
    sentences = _split_sentences(text)
    matches: list[ResidualPlaceholderMatch] = []
    for m in _RESIDUAL_PLACEHOLDER_RE.finditer(text):
        sent, _, _ = _sentence_for(sentences, m.start())
        matches.append(ResidualPlaceholderMatch(m.group(0), m.start(), m.end(), sent))
    return ResidualPlaceholderResult(tuple(matches), unresolved=bool(matches))


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GuardReport:
    text: str  # final text -- citations stripped/re-rendered; NOT further modified by the other guards
    citation_result: CitationStripResult
    grounding_result: GroundingResult
    conclusion_result: ConclusionGuardResult
    residual_placeholder_result: ResidualPlaceholderResult
    unresolved: bool  # True iff any guard requires Board attention
    board_flag: bool  # alias for conclusion_result.board_flag -- see check_conclusion_verbs docstring


def run_guards(
    text: str,
    *,
    fact_set: Iterable[Any] = (),
    citations: Sequence[Citation] = (),
    style: str = "long",
) -> GuardReport:
    """Runs all four guards in the required order (citation stripping
    first -- see the module docstring) and returns one combined report. The
    numeral-grounding, conclusion-verb, and residual-placeholder guards are
    read-only checks over `citation_result.text`; NONE of them rewrite the
    sentence they flag -- flagging, not silent correction, is the entire
    point (a shortfall is always a Board flag, never a conclusion, never a
    quiet fix).

    Callers whose text ever passed through `llm/redact.py` (i.e. anything
    that went to a real provider) MUST call `RedactionResult.restore()` /
    `restore_text()` on the model's raw answer BEFORE handing it to
    `run_guards()` -- the residual-placeholder guard is meaningless on
    still-redacted text (see `check_residual_placeholders`'s docstring)."""
    cit = strip_and_rerender_citations(text, citations, style=style)
    grounding = check_numeral_grounding(cit.text, fact_set)
    conclusion = check_conclusion_verbs(cit.text)
    residual = check_residual_placeholders(cit.text)
    unresolved = grounding.unresolved or conclusion.board_flag or residual.unresolved
    return GuardReport(
        text=cit.text,
        citation_result=cit,
        grounding_result=grounding,
        conclusion_result=conclusion,
        residual_placeholder_result=residual,
        unresolved=unresolved,
        board_flag=conclusion.board_flag,
    )
