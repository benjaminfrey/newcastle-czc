#!/usr/bin/env python3
"""Normalisation applied to BOTH sides before a baseline redline diff.

WHY. Measured 2026-08-24 across the seven mappable article pairs: the raw diff
is 1,261 changed lines; after normalisation it is 243. Article 1 goes from 30 to
ZERO, Article 7 Use Standards from 298 to 2. The remaining 1,018 lines are
heading-case churn and paragraph re-wrapping -- neither of which reaches the
rendered page, because the Typst template styles headings itself.

Without this, the document meant to show voters what changed buries 243 real
changes under 1,018 invisible ones.

THE DANGER, and the rule that governs this file: a normaliser that is too
aggressive silently removes a real amendment from the redline, and an omission
from a redline is invisible to the reader. So:

  * Every rule is narrow and separately tested, in BOTH directions -- it
    suppresses the cosmetic case, AND a real change of the same shape survives.
  * Normalisation NEVER touches numerals, defined terms, shall/may/must, or any
    word not covered by a rule below.
  * If you are tempted to add a rule that "cleans up" anything semantic, don't.
    A noisier redline is recoverable; a redline missing an amendment is not.
"""
from __future__ import annotations

import re

# Rule 1. `### A. PURPOSE` -> `### a. PURPOSE`. ONLY the single leading letter
# of an ATX heading, and only when followed by a period. Body text is untouched.
_HEADING_LETTER = re.compile(r"^(#{1,6}\s+)([A-Za-z])(\.)", re.MULTILINE)

# Rule 3. Collapse runs of whitespace so markdown re-wrapping is invisible.
# Applied per-paragraph, so paragraph BREAKS still count as structure.
_WS_RUN = re.compile(r"[ \t]*\n[ \t]+")
_SPACES = re.compile(r"[ \t]{2,}")


def _heading_case(text: str) -> str:
    return _HEADING_LETTER.sub(lambda m: m.group(1) + m.group(2).lower() + m.group(3), text)


def _rewrap(text: str) -> str:
    # A single newline followed by indentation is a wrap; a blank line is not.
    return _SPACES.sub(" ", _WS_RUN.sub(" ", text))


def normalize(text: str, *, amap, is_baseline_side: bool) -> str:
    """Normalise one side of the diff.

    `is_baseline_side` matters: cross-reference renumbering maps baseline ->
    current, so it is applied to the OLD side only. Applying it to both would
    double-shift every reference and corrupt the comparison silently.
    """
    out = _heading_case(text)
    if is_baseline_side:
        out = amap.renumber(out)
    return _rewrap(out)


def report(old: str, new: str, *, amap) -> dict[str, int]:
    """How many differences each rule suppressed. Printed by the build so the
    normaliser's effect is visible rather than assumed.

    NOTE: the brief's original `heading_case` formula compared match counts
    before/after normalising `old` against itself -- since `_heading_case`
    never changes how many headings match (only their letter's case), that
    count was always zero. Replaced with a direct count of headings on the
    old (baseline) side whose leading letter is uppercase: those are exactly
    the headings this rule rewrites to lowercase, i.e. the ones whose case
    difference against the current side's lowercase convention it suppresses.
    """
    counts = {"heading_case": 0, "renumber": 0, "rewrap": 0}
    counts["heading_case"] = sum(
        1 for m in _HEADING_LETTER.finditer(old) if m.group(2).isupper()
    )
    counts["renumber"] = sum(
        1 for m in re.finditer(r"\bArticle (\d+)\b", old)
        if amap.article_numbers.get(int(m.group(1)), int(m.group(1))) != int(m.group(1))
    )
    counts["rewrap"] = len(_WS_RUN.findall(old)) + len(_WS_RUN.findall(new))
    return counts
