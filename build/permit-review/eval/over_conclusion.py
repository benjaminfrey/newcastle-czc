"""eval/over_conclusion.py -- W8 metric 3: OVER-CONCLUSION RATE.

W6/W7 claim the app never concludes (`engine.review.Disposition` is a closed
enum, none of its seven members a verdict; `findings_nodes.conclusion` stays
NULL until a human vote sets it). This module does not trust that claim --
it MEASURES it by scanning REAL RENDERED OUTPUT this app actually produces,
the same node-dict shape `render/findings_to_md.py:render_nodes()` consumes,
built by actually calling the real engine/render code paths below, not by
re-reading engine/review.py's own docstrings or citing test names (BUILD-
STATE.md's Lesson 1/3).

WHAT COUNTS AS "OVER-CONCLUSION" HERE
--------------------------------------
Two independent, real guards are reused rather than re-invented:

  1. `engine.review.contains_banned_verdict_language()` -- the review
     engine's own blunt substring net ("not_met", "compliant", "approved",
     "denied", "satisfied", "verdict", ...).
  2. `llm.guards.check_conclusion_verbs()` -- the LLM-output guard's
     sentence-aware pattern set. This ALREADY includes "is/are consistent
     with" (`_CONCLUSION_PATTERNS["consistent"]`) -- i.e. the exact subtle
     escape the task brief names is not a gap this module has to invent a
     check for; it is already a first-class trigger in the guard this
     module reuses.

Plus FOUR additional, narrower checks this module adds because neither
existing guard covers them (verified by grepping their pattern lists before
writing these -- "no deficiency identified" / roll-up counts / UI badges are
NOT in `_CONCLUSION_PATTERNS` or `_BANNED_VERDICT_SUBSTRINGS`):

  3. `_ESCAPE_PHRASES` -- "no deficiency identified", "no issue(s) found/
     identified", "no violation", "no concerns identified" -- a conclusion
     phrased as an absence-of-problem statement, dodging every verb in (1)
     and (2). NOTE (2026-08-24 W8 round): these exact strings were NOT
     found verbatim in the nine real decisions when grepped for this
     round's audit -- they were written for a plausible dodge shape, not
     lifted from the corpus. Left in place (removing a check narrows
     coverage, the wrong direction), but flagged here as the one part of
     this module NOT built the way #6 below was (from the real decisions'
     own text) -- see DECISIONS-NEEDED.md D-0032 for the judgement call.
  4. `_ROLLUP_RE` -- "N of M standards/criteria (met|satisfied|passed)",
     "N/M met" -- a count that implies a verdict without stating one for
     any single standard.
  5. `_BADGE_RE` -- a standalone status token ("PASS", "APPROVED", "DENIED",
     "COMPLIANT", a checkmark glyph) of the kind a UI badge would render.
  6. `_ABSENCE_RE` -- ADDED 2026-08-24 (W8 over-conclusion round). "No
     significant impact ... is expected", "No adverse effect ... is
     expected", bare "none is expected" -- an absence-of-problem
     conclusion in the SPECIFIC grammatical shape ("no <noun> ... is/are
     expected/anticipated", rather than #3's "no <noun> identified/found")
     that the real decisions actually use repeatedly and that neither #3
     nor `llm.guards.check_conclusion_verbs` caught: real, verbatim,
     Shattuck/Uberoi ("No significant impact is expected on any adjoining
     municipalities"), Uberoi ("no adverse effect on the scenic or natural
     beauty of the area is expected"), Academy Hill Z38 (bare "none is
     expected", answering a checklist item about site impact). Unlike #3,
     every example behind this pattern is a direct quote or near-paraphrase
     of real corpus language -- see tests/test_over_conclusion_dodges.py.

CONTEXT-AWARE, ON PURPOSE -- read this before trusting a "0" from this
module, and read the postscript at the bottom of this docstring first: a
FIRST DRAFT of this scanner, run for real against the real empty-facts
subdivision walk, produced 9 raw hits, and every one of them turned out to
be a false positive from exactly this kind of unhandled context -- which is
exactly why this module buckets by structural context rather than reporting
one flat count. `_motion_render_nodes()` (render/case_findings.py) legitimately
prints "To conclude that the application is consistent with {label}." for
every `type: 'motionblock'` node with a real, human-drafted `motions` row --
this is a DRAFT MOTION for a human Board member to move/second/vote, always
paired with blank Yea/Nay/Abstain/Result slots (`style/findings-template.typ
:#motionblock`) until `engine.meeting.apply_motion()` records a real carried
vote. It is real Board convention -- the real Shattuck adopted decision
(docs/.../2025.12.18.pdf pp.11-14) uses this exact phrase for every carried
motion. A naive scanner would flag this as a violation on every case that
has ever reached a meeting; that would be a FALSE POSITIVE, and burying a
scanner in false positives is its own way of making it untrustworthy (a
gate nobody reads is not a gate). So: hits inside a `motionblock`'s `motion`
field are bucketed SEPARATELY as `motion_hits` (expected, reported, and
independently checked below that the SAME node's vote fields are still
blank -- i.e. no conclusion has actually landed) rather than merged into
`prose_hits` (target: always 0, any nonzero is the real signal). Hits
anywhere else -- `body`, `board_question`, `heading`, `finding` text, a
`kv`/`table` cell, `unresolved` text, `boardq` text, `standard` text, a
`conditions` item, ANY node field that is not a motionblock's own `motion`
slot -- go to `prose_hits` and are never excused.

A SECOND CONTEXT CARVE-OUT, FOUND THE SAME WAY (by running this scanner for
real, not by anticipating it): `standard()` render-nodes carry
`quoted_standard_text` VERBATIM off `rules.code_text` -- the Code's OWN
words, which of course use words like "meet the standards", "violation",
and "will not adversely affect", because that is what a regulatory standard
says. Flagging the Code's own text as an app-authored verdict is a category
error, not a finding -- CONTRACT.md requires this text be quoted verbatim,
so a scanner that penalized quoting it correctly would be training toward
paraphrase, the opposite of the app's own safety design. Bucketed as
`quoted_hits`, never counted toward `prose_hits`.

A THIRD, for the same underlying reason: `boardq()` render-nodes are, by
construction, ALWAYS a first-person question TO the Board --
`engine.review.render_judgement_question()`, `engine.applicability.gate_one()`'s
own UNKNOWN board_question template, and the boolean/numeric fallback
questions are the only three templates that ever populate `board_question`,
and all three quote the standard's own text as PART of asking, which is
exactly how they trip a verb-list guard built for asserted prose (verified
directly: engine.applicability.gate_one's UNKNOWN template literally asks
"...does it, and if so, how does the application meet the standard?" --
a question, grammatically, that happens to contain "meet the standard").
Bucketed as `question_hits`, never counted toward `prose_hits` -- but
STILL SCANNED AND REPORTED, never silently dropped, because a future
template could in principle smuggle a real assertion inside a
`board_question` string, and this module should still be able to see it if
it did.

`prose_hits` is therefore the narrowest, most honest bucket: any hit inside
`finding()` (body), `unresolved()`, `para()`, a `kv`/`table` cell, a
`conditions` item, or a `signaturegrid` name -- the render-node types that
carry the app's OWN asserted content, never a quotation and never a
question. THIS is the bucket whose count must be 0.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parent.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from engine.review import contains_banned_verdict_language  # noqa: E402
from llm.guards import check_conclusion_verbs  # noqa: E402

# --------------------------------------------------------------------------- #
# The two additional checks neither existing guard covers.
# --------------------------------------------------------------------------- #

_ESCAPE_PHRASES: tuple[str, ...] = (
    "no deficiency identified",
    "no deficiencies identified",
    "no deficiency was identified",
    "no issue identified",
    "no issues identified",
    "no issue found",
    "no issues found",
    "no violation identified",
    "no violation found",
    "no concerns identified",
    "no concerns were identified",
)

_ROLLUP_RE = re.compile(
    r"\b\d+\s*(?:of|/)\s*\d+\s*(?:standards?|criteria|conditions?)?\s*"
    r"(?:met|satisfied|passed|in\s+compliance|resolved)\b",
    re.IGNORECASE,
)

# Standalone status tokens a UI badge would render -- word-boundaried so
# "approved" inside "not yet approved" still counts (that IS a verdict-
# shaped claim) but "Draft Issued" / "Under Review" (STATUS_LABELS,
# app/main.py -- process states, not merits verdicts) do not match.
_BADGE_RE = re.compile(
    r"\b(?:PASS(?:ED)?|FAIL(?:ED)?|APPROVED|DENIED|COMPLIANT|NON-?COMPLIANT)\b"
    r"|[✓✔]",  # checkmark glyphs
    re.IGNORECASE,
)

# "No <adverse-shaped noun> ... is/are expected/anticipated" and bare "none
# is/are expected" -- see module docstring check #6. `[^.]{0,80}?` bounds
# the gap between the noun and the verb to roughly one clause, so this does
# not reach across an unrelated sentence boundary and merge two different
# statements into a false hit.
_ABSENCE_RE = re.compile(
    r"\bno\s+(?:significant\s+|adverse\s+|negative\s+)*(?:impact|effect|burden)s?\b"
    r"[^.]{0,80}?\b(?:is|are|was|were)\s+(?:expected|anticipated)\b"
    r"|\bnone\s+(?:is|are)\s+expected\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Hit:
    node_index: int
    node_type: str
    field_name: str
    category: str  # 'banned_substring' | 'conclusion_verb' | 'escape_phrase' | 'rollup' | 'badge' | 'absence'
    matched_text: str
    context_snippet: str
    bucket: str  # 'prose' | 'motion' | 'quoted' | 'question'


def _snippet(text: str, start: int, end: int, pad: int = 40) -> str:
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    return text[lo:hi].replace("\n", " ")


def scan_text(text: str) -> list[tuple[str, str, str]]:
    """Runs every check against one string. Returns (category, matched_text,
    context_snippet) tuples -- real matches, not a boolean. Empty/None-safe."""
    if not text:
        return []
    out: list[tuple[str, str, str]] = []

    banned = contains_banned_verdict_language(text)
    if banned:
        idx = text.lower().find(banned)
        out.append(("banned_substring", banned, _snippet(text, idx, idx + len(banned))))

    guard_result = check_conclusion_verbs(text)
    for m in guard_result.matches:
        out.append(("conclusion_verb", m.matched_text, _snippet(text, m.start, m.end)))

    lowered = text.lower()
    for phrase in _ESCAPE_PHRASES:
        idx = lowered.find(phrase)
        if idx != -1:
            out.append(("escape_phrase", phrase, _snippet(text, idx, idx + len(phrase))))

    for m in _ROLLUP_RE.finditer(text):
        out.append(("rollup", m.group(0), _snippet(text, m.start(), m.end())))

    for m in _BADGE_RE.finditer(text):
        out.append(("badge", m.group(0), _snippet(text, m.start(), m.end())))

    for m in _ABSENCE_RE.finditer(text):
        out.append(("absence", m.group(0), _snippet(text, m.start(), m.end())))

    return out


# Node dict fields that carry human-facing prose, per render/findings_to_md.py
# node constructors (heading, para, kv, table, standard, finding, unresolved,
# boardq, motionblock, conditions, signaturegrid, raw). `raw` (raw Typst) is
# deliberately excluded -- it is not rendered English prose, and the one real
# caller (render/case_findings.py) never puts human sentences there.
_TEXT_FIELDS: tuple[str, ...] = (
    "text", "body", "board_question", "quoted_standard_text", "heading",
    "motion", "discussion",
)


def _iter_node_texts(node: dict[str, Any]):
    """Yields (field_name, text) for every text-bearing field on one
    render-node dict, INCLUDING nested shapes (kv pairs, table cells,
    conditions items, signaturegrid member names) -- a hit hiding inside a
    table cell must not be invisible to this scanner just because it isn't
    a top-level string field."""
    for f in _TEXT_FIELDS:
        v = node.get(f)
        if isinstance(v, str):
            yield f, v
    if node.get("type") == "kv":
        for k, v in node.get("items", []):
            yield "kv", f"{k}: {v}"
    if node.get("type") == "table":
        for row in node.get("rows", []):
            for cell in row:
                yield "table_cell", str(cell)
    if node.get("type") == "conditions":
        for item in node.get("items", []):
            yield "conditions_item", str(item)
    if node.get("type") == "signaturegrid":
        for m in node.get("members", []):
            if isinstance(m, dict):
                yield "signature_name", str(m.get("name", ""))


@dataclass
class ScanReport:
    label: str
    total_nodes: int = 0
    total_text_fields_scanned: int = 0
    prose_hits: list[Hit] = field(default_factory=list)
    motion_hits: list[Hit] = field(default_factory=list)
    quoted_hits: list[Hit] = field(default_factory=list)
    question_hits: list[Hit] = field(default_factory=list)
    motion_nodes_with_nonblank_vote_despite_no_carried_motion: list[int] = field(default_factory=list)

    @property
    def over_conclusion_rate(self) -> float:
        """prose_hits / text fields scanned -- the number that must be 0.
        Motion-bucket hits never enter this ratio (see module docstring)."""
        if self.total_text_fields_scanned == 0:
            return 0.0
        return len(self.prose_hits) / self.total_text_fields_scanned


def scan_nodes(nodes: list[dict[str, Any]], *, label: str) -> ScanReport:
    report = ScanReport(label=label, total_nodes=len(nodes))
    for i, node in enumerate(nodes):
        node_type = node.get("type", "?")
        is_motion = node_type == "motionblock"

        # Structural check on every motionblock: a node with a non-blank
        # 'result' but this scan was never told a real carried vote
        # produced it is itself suspicious -- flag it, don't assume it's
        # fine. (render_case_findings only ever fills these from a real
        # `motions` row, but this module verifies the SHAPE, not the
        # caller's promise.)
        if is_motion and node.get("motion") and node.get("result") not in (None, ""):
            report.motion_nodes_with_nonblank_vote_despite_no_carried_motion.append(i)

        if is_motion:
            bucket = "motion"
        elif node_type == "standard":
            bucket = "quoted"
        elif node_type == "boardq":
            bucket = "question"
        else:
            bucket = "prose"

        target = {
            "motion": report.motion_hits, "quoted": report.quoted_hits,
            "question": report.question_hits, "prose": report.prose_hits,
        }[bucket]

        for field_name, text in _iter_node_texts(node):
            report.total_text_fields_scanned += 1
            hits = scan_text(text)
            for category, matched, snippet in hits:
                target.append(Hit(
                    node_index=i, node_type=node_type, field_name=field_name,
                    category=category, matched_text=matched, context_snippet=snippet,
                    bucket=bucket,
                ))
    return report


def print_report(report: ScanReport) -> None:
    print(f"=== over-conclusion scan: {report.label} ===")
    print(f"  nodes scanned:            {report.total_nodes}")
    print(f"  text fields scanned:      {report.total_text_fields_scanned}")
    print(f"  PROSE hits (target 0):    {len(report.prose_hits)}")
    for h in report.prose_hits:
        print(f"    [{h.category}] node#{h.node_index} ({h.node_type}.{h.field_name}): "
              f"{h.matched_text!r} -- ...{h.context_snippet}...")
    print(f"  motion-block hits (expected, house convention, not counted): {len(report.motion_hits)}")
    for h in report.motion_hits:
        print(f"    [{h.category}] node#{h.node_index}: {h.matched_text!r} -- ...{h.context_snippet}...")
    print(f"  quoted-standard-text hits (verbatim Code language, not counted): {len(report.quoted_hits)}")
    for h in report.quoted_hits:
        print(f"    [{h.category}] node#{h.node_index}: {h.matched_text!r} -- ...{h.context_snippet}...")
    print(f"  board-question hits (a question to the Board, not counted): {len(report.question_hits)}")
    for h in report.question_hits:
        print(f"    [{h.category}] node#{h.node_index}: {h.matched_text!r} -- ...{h.context_snippet}...")
    if report.motion_nodes_with_nonblank_vote_despite_no_carried_motion:
        print("  !! motionblock(s) with a non-blank vote field in this render "
              f"(node indices {report.motion_nodes_with_nonblank_vote_despite_no_carried_motion}) "
              "-- verify these correspond to a REAL carried motion, not a leaked default.")
    print(f"  over_conclusion_rate = prose_hits / text_fields = {report.over_conclusion_rate:.4f}")
    print()


__all__ = [
    "Hit", "ScanReport", "scan_text", "scan_nodes", "print_report",
    "contains_banned_verdict_language", "check_conclusion_verbs",
]
