#!/usr/bin/env python3
"""Normalisation for a baseline redline diff.

WHY. Measured 2026-08-24 across the seven mappable article pairs: the raw diff
is 1,261 changed lines; after heading-case + cross-reference renumbering +
re-wrapping it was 243. Article 1 goes from 30 to ZERO, Article 7 Use
Standards from 298 to 2. Those 1,018 lines are heading-case churn and
paragraph re-wrapping -- neither of which reaches the rendered page, because
the Typst template styles headings itself.

A follow-up pass the same day (Task 2b) found ~90 of the remaining 243 were
STILL only renumbering, in two forms the first three rules didn't recognise:
table captions/cross-references (`TABLE 4.1` / `Table 4.1` / `table 4.1`,
whose leading number is an article number, same as a heading) and frontmatter
`article-number: "N"`. Rules 4 and 5 below close that gap; the total is now
151. Articles 1, 5, 6, and 7 report ZERO substantive changes.

Without this, the document meant to show voters what changed buries 151 real
changes under over a thousand invisible ones.

THE DANGER, and the rule that governs this file: a normaliser that is too
aggressive silently removes a real amendment from the redline, and an omission
from a redline is invisible to the reader. So:

  * Every rule is narrow and separately tested, in BOTH directions -- it
    suppresses the cosmetic case, AND a real change of the same shape survives.
  * Normalisation NEVER touches numerals, defined terms, shall/may/must, or any
    word not covered by a rule below.
  * If you are tempted to add a rule that "cleans up" anything semantic, don't.
    A noisier redline is recoverable; a redline missing an amendment is not.

RENDER SAFETY -- added after a Task 3 review finding (2026-08-24). `normalize()`
(all five rules, including `_rewrap`) is COMPARISON-ONLY: it decides what
counts as a difference, and its output must never be fed to a renderer.
`redline-text.py --source` is line-based and emits the lines it is handed, so
if normalised text reaches it, normalisation stops being invisible cosmetics
and becomes a silent rewrite of the document -- `_rewrap` collapses indented
sub-clause continuations into run-on prose. Measured on the real baseline
build: article-08-administration.md's 211 indented sub-clause lines fell to 4,
and body pages dropped 113 -> 110. `normalize_old_side()` below is the
render-safe alternative (heading case + all three renumbering rules, no
rewrap) for the side that a baseline redline actually renders; it costs
nothing -- the marked-line count across all seven pairs is 151 either way,
with or without rewrap.
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

# Rule 4. `TABLE 4.1 …` / `Table 4.1 …` / `table 4.1 …` -> the same word ->
# `… 5.1 …`. Table numbers follow the article number they live in, so a
# table's leading digits shift exactly the way `amap.article_numbers` says
# the article shifted. Only the article-number component (before the dot) is
# touched; the table's own sequence number (after the dot) and everything
# following it -- including a changed title -- is untouched. All three
# casings occur in the corpus: article captions use all-caps `TABLE 4.1`,
# most body cross-references use title-case `Table 4.2`, and a few body
# cross-references use lowercase `table 5.1`. Matched case-insensitively;
# the matched word's original case is preserved in the output (group(1) is
# the literal matched text, unaffected by the IGNORECASE flag).
#
# CONTEXT ANCHOR (added after a review finding, 2026-08-24). Bare `table N.M`
# is not unique to captions/cross-references -- "seasonal high water table
# 5.2 feet" contains it too, as an ordinary compound noun ("water table")
# followed by an unrelated measurement. Renumbering that would silently
# suppress a real amendment to a groundwater depth. This is not hypothetical:
# "water table" is standard septic/soils/groundwater language and a Shoreland
# article is planned (see CLAUDE.md Phase 9), so the phrase is very likely to
# appear followed by a depth in feet.
#
# The chosen anchor requires what immediately FOLLOWS the number to look like
# a real caption/reference continuation, not requiring anything about what
# precedes it: every `table N.M` in this corpus (both the v0.1-baseline and
# the current source, checked exhaustively at 2026-08-24) is followed either
# by a clause/sentence boundary (`:` `.` `,` `;` or end of line) or by the
# start of the table's title, which always begins with a capital letter (all-
# caps caption or Title Case reference: "TABLE 4.1 SCREENING FORMULA", "Table
# 5.2: Additional Structures", "table 6.1 Design Standards By District"). A
# compound noun like "water table" is instead followed by an ordinary
# lowercase word -- a unit, a verb, a preposition -- which this anchor does
# not accept.
#
# This was chosen over a precedes-instead-of-follows anchor (e.g. excluding
# "water"/"ground"/"high" before "table") because that is exactly the kind of
# blocklist-by-guesswork the module's own rule against it warns against: it
# would need to enumerate every possible compound-noun modifier rather than
# rely on one structural fact that already holds for 100% of the real corpus.
#
# The anchor is deliberately NARROW rather than broad: a genuine reference
# this pattern fails to match (e.g. "Table 3.2 for the higher design speed",
# present in Article 3, which is new-at-adoption and not diffed against the
# baseline) simply stays unsuppressed -- a recoverable false "still differs".
# The failure this module cannot recover from is the opposite one: a real
# amendment suppressed because it merely resembled a table reference.
#
# NOTE the case-insensitivity is scoped to the word "table" only -- `(?i:...)`
# -- rather than applied to the whole pattern via re.IGNORECASE. A prior draft
# used a pattern-wide IGNORECASE flag, which also made the `[A-Z]` in the
# lookahead accept lowercase letters, silently defeating the anchor it exists
# to provide (it would have renumbered "water table 5.2 feet" after all,
# since "f" satisfied `[A-Z]` under that flag). Scoping the flag to just the
# word keeps the title-case signal in the lookahead genuinely case-sensitive.
_TABLE_NUM = re.compile(
    r"\b(?P<word>(?i:table))\s+(\d+)\.(\d+)(?=[:.,;]|\s+[A-Z]|\s*$)",
    re.MULTILINE,
)

# Rule 5. Frontmatter `article-number: "6"` -> `article-number: "7"`. Every
# article file's YAML frontmatter states its own number; that number shifts
# with the article, same map as Rule 4 and the cross-reference renumbering.
_FRONTMATTER_ARTICLE_NUMBER = re.compile(r'^(article-number:\s*")(\d+)(")', re.MULTILINE)


def _heading_case(text: str) -> str:
    return _HEADING_LETTER.sub(lambda m: m.group(1) + m.group(2).lower() + m.group(3), text)


def _rewrap(text: str) -> str:
    # A single newline followed by indentation is a wrap; a blank line is not.
    return _SPACES.sub(" ", _WS_RUN.sub(" ", text))


def _renumber_tables(text: str, amap) -> str:
    def repl(m: re.Match) -> str:
        word, article, table_num = m.group(1), int(m.group(2)), m.group(3)
        new_article = amap.article_numbers.get(article, article)
        return f"{word} {new_article}.{table_num}"

    return _TABLE_NUM.sub(repl, text)


def _renumber_frontmatter(text: str, amap) -> str:
    def repl(m: re.Match) -> str:
        old_article = int(m.group(2))
        new_article = amap.article_numbers.get(old_article, old_article)
        return f"{m.group(1)}{new_article}{m.group(3)}"

    return _FRONTMATTER_ARTICLE_NUMBER.sub(repl, text)


def normalize(text: str, *, amap, is_baseline_side: bool) -> str:
    """Normalise one side of the diff.

    COMPARISON-ONLY. NOT render-safe. This includes `_rewrap`, which collapses
    indented continuation lines -- fine for computing a diff, but ruinous if
    the result is ever fed to a line-based renderer (as `redline-text.py
    --source` is): it flattens the Code's lettered sub-clause hierarchy into
    run-on prose. Measured: article-08-administration.md 211 indented
    sub-clause lines -> 4, body pages 113 -> 110. A caller that emits this
    function's output into the rendered document -- rather than only using it
    to decide what differs -- will damage the document. Use
    `normalize_old_side` for the side that gets rendered.

    `is_baseline_side` matters: cross-reference renumbering, table-number
    renumbering, and frontmatter `article-number` renumbering all map
    baseline -> current, so all three are applied to the OLD side only.
    Applying them to both would double-shift every reference and corrupt the
    comparison silently.
    """
    out = _heading_case(text)
    if is_baseline_side:
        out = amap.renumber(out)
        out = _renumber_tables(out, amap)
        out = _renumber_frontmatter(out, amap)
    return _rewrap(out)


def normalize_old_side(text: str, *, amap) -> str:
    """Render-SAFE normalisation for the OLD side of a redline.

    Heading case, cross-reference renumbering, table-number renumbering, and
    frontmatter `article-number` renumbering only -- NO re-wrapping. All four
    rewrite only digits/letters in narrow, fixed positions (a heading's
    leading letter, an `Article N` reference, a `TABLE N.x` caption, the
    frontmatter field), so none of them touches line structure.

    WHY NO REWRAP. redline_source() is line-based and EMITS the lines it is
    given, so anything done here reaches the rendered PDF. _rewrap() collapses
    indented continuations, which flattens the Code's lettered hierarchy into
    run-on prose -- measured: article-08-administration.md 211 sub-clause lines
    -> 4, body pages 113 -> 110. And it buys nothing: across all seven
    comparable pairs the marked-line count is the same with or without rewrap.
    Normalisation is legitimate for COMPARISON; feeding normalised text to the
    RENDERER is not.
    """
    out = amap.renumber(_heading_case(text))
    out = _renumber_tables(out, amap)
    out = _renumber_frontmatter(out, amap)
    return out


def changed_line_count(old: str, new: str, *, amap) -> int:
    """How many lines the redline will MARK for this article pair.

    ONE definition, shared by the operator-facing breakdown
    (build/adoption_breakdown.py) and provably matching what the packet
    renders. It deliberately mirrors the RENDER path exactly:

        old side  ->  normalize_old_side(old)   (what redline_resolve.py writes)
        new side  ->  verbatim                  (the staged working-tree file)

    Before this existed, the breakdown computed its number with `normalize()`
    on BOTH sides -- which rewraps -- while the redline rendered with
    `normalize_old_side()` on one side and nothing on the other. The two agreed
    (151, and identically per article) but only by coincidence of the corpus,
    and nothing asserted it. A number an operator reads as "this is what is in
    the packet" must be computed the way the packet is computed, or it can
    drift silently from what the packet shows. See
    build/tests/test_normalize_for_diff.py for the test that pins the
    agreement.
    """
    import difflib

    o = normalize_old_side(old, amap=amap).splitlines()
    n = new.splitlines()
    return sum(1 for line in difflib.unified_diff(o, n, n=0)
               if line[:1] in "+-" and line[:3] not in ("+++", "---"))


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
