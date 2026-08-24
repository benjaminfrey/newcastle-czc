"""eval/ground_truth.py -- D3: INDEPENDENT ground truth for the structural
recall metric, derived from the raw decision PDFs in docs/, with ZERO
dependency on rulesets/adopted/articles.json (or anything built from it).

--------------------------------------------------------------------------
WHY THIS MODULE EXISTS -- THE CIRCULARITY IT REPLACES
--------------------------------------------------------------------------
Before this module, eval/metrics.py's structural recall derived "which
subdivision standards did this decision address" by resolving citations in
the decision's text against `rulesets/adopted/articles.json`
(`ruleset_build.verify_citations.build_report()`). That is the SAME
artifact `engine/criteria_seed.py` builds the criteria set from -- i.e. the
"predicted" side of the recall fraction. A node id missing from
articles.json (a parsing gap, a future edit, anything) would silently
shrink BOTH `truth` and `predicted` at once: the citation would fail to
resolve (truth loses the letter) exactly when the criteria set fails to
seed that standard (predicted loses the letter too), so recall would stay
1.0 even though a real standard vanished from the app. An eval that agrees
with itself this way is worse than no eval -- see CLAUDE.md's framing for
this W8 round.

This module breaks that circularity by reading the decision PDF directly.
It never imports `rulesets/adopted/articles.json`, `ruleset_build.slugs`,
`ruleset_build.verify_citations`, or `engine.criteria_seed` -- verified by
`tests/test_ground_truth.py::test_module_has_no_articles_json_dependency`,
which greps this file's own source for those names and fails the build if
one appears.

--------------------------------------------------------------------------
METHOD
--------------------------------------------------------------------------
The two real subdivision decisions on file (Shattuck, Academy Hill -- the
only two matched pairs carrying "subdivision" in `review_types` with a
decision file, per eval/pairs.json) render Article 7 Section 12.f.1's
21 standards as a literal LETTERED LIST inside an "APPROVAL STANDARDS"
section -- e.g. Shattuck p.5: "c.<ZWSP> Pollution: ...", "d.<ZWSP>
Sufficient Water: ...", one paragraph per lettered standard a. through u.,
in strict alphabetical order (hand-verified against the real PDF:
`docs/Findings of Fact and Conclusions of Law/M003, L059 (White Rd,
Shattuck), Subdivision FoF & CoL 2025.12.18.pdf`, pp.4-8; the "<ZWSP>" is a
literal U+200B zero-width space pymupdf extracts from what was originally a
bullet/checkbox glyph in the source document -- confirmed by printing the
raw codepoint, not assumed).

Extraction, in order:

  1. Pull raw per-page text with pymupdf (already a hard dependency of this
     app -- no new one added).
  2. Find every ALL-CAPS heading LINE (`_HEADING_RE`) in the document, in
     reading order -- these are the same heading style the real decisions
     use for every major section ("FINDINGS OF FACT", "APPROVAL STANDARDS",
     "CONCLUSIONS OF LAW", ...).
  3. Locate the "APPROVAL STANDARDS" heading. The STANDARDS REGION is the
     text between the END of that heading line and the START of the NEXT
     heading in the list (whatever it is -- "ROAD, DRIVEWAY, & ENTRANCE
     ORDINANCE" in Shattuck). Bounding the search this way is deliberate:
     scanning the WHOLE document for "a./b./c." markers would also catch
     an unrelated lettered list elsewhere in the same PDF (these decisions
     have at least one other a./b./c.-style list under a different
     heading, confirmed by hand) and wrongly fold it into the standards
     set.
  4. Within that region, find every LINE-STARTING lettered marker
     "<letter>." for letter in a-u (`_LETTER_MARKER_RE`, anchored with
     `(?m)^\\s*`).
  5. Reject false positives from a DIFFERENT, commonly-nested list
     convention the same decisions use inside individual standards (e.g.
     standard c., Pollution, breaks its own test into Roman-numeral
     sub-items i./ii./iii./iv./v.): a bare "i." (the ONLY letter in a-u
     that collides with a Roman numeral -- "v" falls outside a-u
     alphabetically, so it can never collide here) is rejected as a Roman
     sub-item if a genuinely-unambiguous multi-character Roman marker
     ("ii.", "iii.", or "iv." -- none of which can ever be mistaken for a
     single a-u letter, since the regex requires exactly one letter
     character before the period) appears within a bounded character
     window of it (`_ROMAN_WINDOW_CHARS`). Verified directly against
     Shattuck: the region contains exactly one "i." occurrence next to a
     Roman sub-list (correctly rejected) and one genuine standalone "i."
     naming the real standard i. Municipal Solid Waste Disposal
     (correctly kept) -- see test_ground_truth.py.
  6. Return the SET of surviving letters.

Cross-checked against the OLD (circular) method for both decisions on file
(2026-08-24): Shattuck -- both methods agree on the full 21/21 (a-u).
Academy Hill -- both methods agree on 0 (its "CONCLUSIONS OF LAW" section is
a never-filled-in DRAFT template -- literal "Motion: <ellipsis> Moved by:
<ellipsis>" -- so there is genuinely nothing to extract; this module reports
`region_found=False` rather than a misleading empty-but-successful result,
since Academy Hill's document has NO "APPROVAL STANDARDS" heading at all,
unlike Shattuck's). Agreement on both real cases is a sanity check that this
independent method is not obviously wrong, NOT proof the two methods are
the same computation -- test_ground_truth.py's independence test proves the
actual claim (this module's answer does not move when articles.json is
edited or deleted), which the cross-check above cannot.

--------------------------------------------------------------------------
FAILURE MODES -- STATED HONESTLY, NOT PAPERED OVER
--------------------------------------------------------------------------
  - A pure-scan decision PDF (no text layer) yields an empty region and
    `region_found=False`. Callers MUST check `region_found` and report
    "not-computable", never treat an empty letter set as "this decision
    addressed zero standards."
  - A decision that never uses this lettered-paragraph house style (a
    different template, a hand-typed decision) also yields
    `region_found=False` if it lacks an "APPROVAL STANDARDS" heading, or an
    incomplete/empty letter set if it has the heading but a different body
    style underneath. This module cannot distinguish "wrong template" from
    "genuinely addressed only 3 standards" in the second case -- both look
    like a small letter set. Callers should treat an implausibly small,
    non-contiguous letter set as suspect and say so, not report it as a
    clean number. Only two decisions exist to check this against today
    (Shattuck, Academy Hill); this method is unverified on a hypothetical
    third subdivision decision that might format its standards list
    differently.
  - The Roman-numeral filter is a heuristic tuned against the two real
    decisions in hand, not a real outline/list parser. A future decision
    that used "i." as a genuine TOP-LEVEL clause marker immediately
    followed (within `_ROMAN_WINDOW_CHARS`) by an unrelated "ii."-shaped
    string elsewhere would be mis-rejected. No such case exists in the
    current corpus (checked); flagged here so a future maintainer knows
    where to look if standard i. ever silently vanishes from a real run.
  - This module has no semantic understanding of WHICH standard a letter
    names -- only that a location in the text is structurally a top-level
    lettered list item inside the standards region. It cannot detect a
    decision that lists letters out of order, skips one without saying so
    in a way that survives normalization, or double-uses a letter for two
    different things.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_HEADING_RE = re.compile(r"(?m)^([A-Z][A-Z0-9 ,.&/'\-]{5,60})\s*$")
_STANDARDS_HEADING = "APPROVAL STANDARDS"

# Anchored at the start of a line (`(?m)^\s*`): a lone letter a-u followed
# immediately by a period is the house-style marker for one lettered
# standard. This deliberately does NOT match "aa." / "a1." / "(a)" / "a)"
# -- the real corpus uses exactly this one bare form, hand-verified; a
# different decision using a different marker style would correctly yield
# no matches here rather than a guessed one.
_LETTER_MARKER_RE = re.compile(r"(?m)^\s*([a-u])\.")

# A Roman-numeral sub-item marker that can NEVER be confused with a single
# a-u letter (regex requires exactly one letter char before the period, so
# "ii.", "iii.", "iv." never match _LETTER_MARKER_RE on their own) -- its
# presence nearby is what identifies a bare "i." as that same sub-list's
# first member, not the outer standards list's letter i.
_ROMAN_MULTI_RE = re.compile(r"(?m)^\s*(ii|iii|iv)\.")

# How far (in characters, within the bounded standards region only) to look
# for a multi-character Roman marker before treating a bare "i." as part of
# that same Roman sub-list rather than the outer letter list. Chosen large
# enough to span one full sub-item paragraph (Shattuck's longest Roman
# sub-item, c.v, runs ~250 characters) with headroom, small enough that it
# cannot reach into a NEIGHBOURING lettered standard's own text two or
# three letters away.
_ROMAN_WINDOW_CHARS = 700


@dataclass(frozen=True)
class GroundTruthResult:
    decision_filename: str
    region_found: bool  # False = no "APPROVAL STANDARDS" heading located at all
    letters: frozenset[str]
    reason: str | None = None  # set when region_found is False, or letters is empty


def _page_texts(pdf_path: Path) -> list[str]:
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    try:
        return [doc[i].get_text() for i in range(doc.page_count)]
    finally:
        doc.close()


def _find_standards_region(full_text: str) -> str | None:
    """Returns the text between the "APPROVAL STANDARDS" heading (exclusive)
    and the next ALL-CAPS heading line (exclusive), or None if no
    "APPROVAL STANDARDS" heading line exists at all -- callers must treat
    None as "not extractable," never as "zero standards addressed."""
    headings = [(m.start(), m.group(1).strip()) for m in _HEADING_RE.finditer(full_text)]
    starts = [pos for pos, name in headings if name == _STANDARDS_HEADING]
    if not starts:
        return None
    start = starts[0]
    # Advance past the heading line itself.
    line_end = full_text.find("\n", start)
    region_start = line_end + 1 if line_end != -1 else start
    later = [pos for pos, _name in headings if pos > start]
    region_end = min(later) if later else len(full_text)
    return full_text[region_start:region_end]


def _extract_letters(region: str) -> frozenset[str]:
    roman_positions = [m.start() for m in _ROMAN_MULTI_RE.finditer(region)]
    accepted: set[str] = set()
    for m in _LETTER_MARKER_RE.finditer(region):
        letter = m.group(1)
        if letter == "i":
            near_roman_sublist = any(abs(m.start() - rp) <= _ROMAN_WINDOW_CHARS for rp in roman_positions)
            if near_roman_sublist:
                continue
        accepted.add(letter)
    return frozenset(accepted)


def decision_addressed_letters(pdf_path: Path) -> GroundTruthResult:
    """The one entry point. Reads `pdf_path` directly -- no ruleset, no
    articles.json, no citation-resolution step of any kind."""
    decision_filename = pdf_path.name
    pages = _page_texts(pdf_path)
    full_text = "\n".join(pages)

    if not full_text.strip():
        return GroundTruthResult(
            decision_filename=decision_filename, region_found=False, letters=frozenset(),
            reason="empty extracted text -- likely a pure scan with no text layer "
                   "(needs the vision/LLM path, not this module)",
        )

    region = _find_standards_region(full_text)
    if region is None:
        return GroundTruthResult(
            decision_filename=decision_filename, region_found=False, letters=frozenset(),
            reason=f"no {_STANDARDS_HEADING!r} heading line found in this document's text -- "
                   "this decision does not use the lettered-standards house style this module "
                   "reads (or the section was never filled in, e.g. a draft template)",
        )

    letters = _extract_letters(region)
    reason = None if letters else "'APPROVAL STANDARDS' heading found, but zero lettered markers inside it"
    return GroundTruthResult(
        decision_filename=decision_filename, region_found=True, letters=letters, reason=reason,
    )


__all__ = ["GroundTruthResult", "decision_addressed_letters"]
