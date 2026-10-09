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

Rule 6 (added 2026-10-08) covers section renumbering. A section inserted into
an Article shifts every later `## N.` heading and every reference to it. The
map comes from build/section_map.py, which DERIVES it by aligning heading
titles, and it is applied to the OLD side only. A bare or plural reference is
rewritten only when nothing qualifies it; the seven guards are listed once, at
the rule itself (`_SECTION_REF`, below). An explicit `Article N Section M`
resolves against Article N. With no map, nothing changes.

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
(all six rules, including `_rewrap`) is COMPARISON-ONLY: it decides what
counts as a difference, and its output must never be fed to a renderer.
`redline-text.py --source` is line-based and emits the lines it is handed, so
if normalised text reaches it, normalisation stops being invisible cosmetics
and becomes a silent rewrite of the document -- `_rewrap` collapses indented
sub-clause continuations into run-on prose. Measured on the real baseline
build: article-08-administration.md's 211 indented sub-clause lines fell to 4,
and body pages dropped 113 -> 110. `normalize_old_side()` below is the
render-safe alternative (heading case + the four renumbering rules, no
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

# Rule 6. Section renumbering. When a section is inserted into an Article,
# every later `## N.` heading and every reference to it shifts by one. The map
# comes from build/section_map.py, which DERIVES it by aligning heading titles
# -- only an identical, unambiguous, in-order title at a new number is mapped.
#
# Narrowness, in seven guards, for a BARE or plural reference (`Section N`, `§N`,
# `Sections A, B, and C`). The one place they are listed:
#   1. The number is rewritten only if it is a KEY in the containing Article's
#      map. The containing Article is read from the text's own frontmatter.
#   2. Not when a statute token occurs within 40 characters before it.
#   3. Not when a `<word> <number>` qualifier directly precedes it.
#   4. Not when a name and a comma directly precede it (`<name>,`).
#   5. Not when `of <anything>` follows it, except `of this Article`.
#   6. Not when its paragraph names any container other than the containing
#      Article (`_FOREIGN_CONTAINER`, below).
#   7. Not when it is an endpoint of a range whose span the map would change
#      (`_LIST_RANGE`, below): the whole list, or the lone endpoint, stays raw.
# Guard 2 is needed because the map alone is not enough: Article 7 has 66
# sections, so `Subchapter C, §53.11` -- a federal-regulations citation in
# Article 7 -- would collide with a renumbered §53. The token set is the
# MEASURED one (2026-10-08): it includes `Public Law` and `Stat.`, because
# Article 9 cites `Public Law 75-412, 50 Stat. 888, Section 8`, which a guard
# limited to MRSA/M.R.S/Title/U.S.C would have renumbered.
# An EXPLICIT `Article N Section M` / `Article N §M` resolves against Article N's
# map and is not statute-guarded: the `Article N` prefix is decisive, and the
# corpus has lines carrying both kinds (`23 MRSA §3026-A and Article 8 §27`).
_SECTION_REF = re.compile(
    r"(?P<explicit>\bArticle (?P<art>\d+) (?:Section |§))(?P<n1>\d+)"
    r"|(?P<plural>\bSections )(?P<list>\d+[A-Za-z0-9.]*"
    r"(?:(?:,\s*(?:and\s+)?|\s+and\s+|\s+(?:through|thru|to)\s+|\s*[\u2013\u2014]\s*)"
    r"\d+[A-Za-z0-9.]*)*)"
    r"|(?P<bare>\bSection |§)(?P<n2>\d+)"
)
_LIST_NUMBER = re.compile(r"(?<![A-Za-z0-9.])(\d+)")
# A RANGE is renumbered only when its span is unchanged. `Sections 3 through 5`
# names every section from 3 to 5; if a section is inserted at 4, the same words
# now cover a different set of sections, and mapping each endpoint on its own
# (3 stays 3, 5 becomes 6) would turn the old range into `3 through 6` and hide
# that. So a plural list is rewritten only if every range inside it keeps its
# span under the map, and a bare endpoint of a range is never rewritten on its
# own: both stay raw, and the change shows. Ranges written with to, thru or an
# en or em dash are ranges too. Leaving text raw only adds visible noise.
_RANGE_WORD = r"(?:through|thru|to|\u2013|\u2014)"
_LIST_RANGE = re.compile(r"(?<![A-Za-z0-9.])(\d+)[A-Za-z0-9.]*\s*" + _RANGE_WORD + r"\s*(\d+)")
# "to" counts as a range word only after a number ("Section 3 to Section 5"),
# never in "subject to Section 3" / "pursuant to Section 3".
_RANGE_BEFORE = re.compile(r"(?:\b(?:through|thru)|\d[A-Za-z0-9.]*\s+to|[\u2013\u2014])\s*$")
_RANGE_AFTER = re.compile(
    r"(?:[A-Za-z0-9.]*\s*" + _RANGE_WORD + r"\s*(?:Sections?\s+|\u00a7)?\d|-\d)")
_H2_NUMBER = re.compile(r"^(## )(\d+)(\. )", re.MULTILINE)
# A bare or plural reference is rewritten only when NOTHING qualifies it.
# Skipping a reference is always the safe direction -- the old text stays raw,
# so at worst a renumbering shows as a change -- while rewriting a qualified one
# can hide a real amendment.
# A reference qualified by ANY "<word> <number>" directly before it --
# "Article 8, Section 3", "Article 8\nSection 3", the adopted text's own typo
# "Atricle 4 Section 17" -- belongs to something else and is left raw.
_QUALIFIED_BEFORE = re.compile(r"\b[A-Za-z][A-Za-z.]*\s+\d+[A-Za-z0-9.\-]*\s*,?\s*$")
# ...and so does one followed by "of <anything>" other than "of this Article":
# "Section 3 of Article 4", "Sections 3 and 4 of Article 8", and statutes
# cited number-first, "Section 10 of Chapter 40A of the Maine General Laws".
_OF_ELSEWHERE = re.compile(r"[A-Za-z0-9.\-]*\s+of\s+(?!this\s+Article\b)")
# Phrase-by-phrase guards cannot converge on every way of pointing into another
# Article or document, so there is one more, deliberately broad: a bare or plural
# reference is left raw whenever its PARAGRAPH names any container other than the
# containing Article -- another Article, an Ordinance, an Act, a statute. A
# paragraph that mentions one anywhere has its bare references left raw, at the
# cost of some recoverable noise. Leaving a reference raw only adds visible
# noise; it can never hide an amendment. `Article N` for the containing Article
# itself does not count.
_FOREIGN_CONTAINER = re.compile(
    r"\bArticle\s+(?P<num>\d+|[IVXLCDM]+)\b"
    r"|\bArticles\b"
    r"|\b(?:Ordinance|Act|Laws?|Regulations?|Rules|Statutes?|Chapter|Subchapter|Title)\b"
    r"|MRSA|M\.R\.S|U\.S\.C|C\.F\.R|CFR|Public Law|Stat\.")
_PARAGRAPH_BREAK = re.compile(r"\n[ \t]*\n")
# "<Word>, Section 3" -- a name and a comma directly before it qualifies it too.
_NAMED_BEFORE = re.compile(r"[A-Za-z)*]\s*,\s*$")


def _names_a_foreign_container(paragraph: str, containing: int) -> bool:
    for m in _FOREIGN_CONTAINER.finditer(paragraph):
        if m.group("num") is None or m.group("num") != str(containing):
            return True
    return False


def _paragraph_at(text: str, pos: int) -> str:
    start = 0
    for b in _PARAGRAPH_BREAK.finditer(text, 0, pos):
        start = b.end()
    nxt = _PARAGRAPH_BREAK.search(text, pos)
    return text[start:nxt.start() if nxt else len(text)]


_STATUTE_CONTEXT = re.compile(
    r"MRSA|M\.R\.S|Title|U\.S\.C|Public Law|Stat\.|Chapter|Subchapter|C\.F\.R|CFR|Regulations")
STATUTE_LOOKBEHIND = 40


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


def section_renumber(text: str, smap) -> tuple[str, int]:
    """Rule 6, returning the text and how many numbers it actually changed."""
    if not smap:
        return text, 0
    fm = _FRONTMATTER_ARTICLE_NUMBER.search(text)
    containing = int(fm.group(2)) if fm else None
    changed = 0

    def lookup(article, n: int) -> int:
        nonlocal changed
        new = smap.get(article, {}).get(n, n) if article is not None else n
        if new != n:
            changed += 1
        return new

    out = _H2_NUMBER.sub(
        lambda h: f"{h.group(1)}{lookup(containing, int(h.group(2)))}{h.group(3)}", text)

    def statute_before(pos: int) -> bool:
        return bool(_STATUTE_CONTEXT.search(out[max(0, pos - STATUTE_LOOKBEHIND):pos]))

    def repl(r: re.Match) -> str:
        if r.group("explicit"):
            return r.group("explicit") + str(lookup(int(r.group("art")), int(r.group("n1"))))
        if (containing is None or statute_before(r.start())
                or _QUALIFIED_BEFORE.search(out[max(0, r.start() - STATUTE_LOOKBEHIND):r.start()])
                or _OF_ELSEWHERE.match(out, r.end())
                or _NAMED_BEFORE.search(out[max(0, r.start() - STATUTE_LOOKBEHIND):r.start()])
                or _names_a_foreign_container(_paragraph_at(out, r.start()), containing)):
            return r.group(0)
        if r.group("plural"):
            amap = smap.get(containing, {})
            if _RANGE_AFTER.match(out, r.end()) or any(
                    amap.get(int(b), int(b)) - amap.get(int(a), int(a)) != int(b) - int(a)
                    for a, b in _LIST_RANGE.findall(r.group("list"))):
                return r.group(0)
            return r.group("plural") + _LIST_NUMBER.sub(
                lambda k: str(lookup(containing, int(k.group(1)))), r.group("list"))
        if (_RANGE_BEFORE.search(out[max(0, r.start() - STATUTE_LOOKBEHIND):r.start()])
                or _RANGE_AFTER.match(out, r.end())):
            return r.group(0)
        return r.group("bare") + str(lookup(containing, int(r.group("n2"))))

    return _SECTION_REF.sub(repl, out), changed


def normalize_sections_only(text: str, *, smap) -> str:
    """Render-SAFE: Rule 6 alone, for a draft-to-draft redline.

    A draft-to-draft redline normalises nothing else (redline_resolve.py keeps
    that path raw), but a section inserted between two drafts shifts headings
    and references just as one inserted at an adoption does. Rule 6 rewrites
    only digits in fixed positions, so it never touches line structure.
    """
    return section_renumber(text, smap)[0]


def normalize(text: str, *, amap, is_baseline_side: bool, smap=None) -> str:
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

    `is_baseline_side` matters: section, cross-reference, table-number and
    frontmatter `article-number` renumbering all map baseline -> current, so
    all four are applied to the OLD side only.
    Applying them to both would double-shift every reference and corrupt the
    comparison silently.

    Rule 6 (section renumbering) applies the same way when an `smap` is given,
    and runs first because that map is keyed on baseline article numbers.
    """
    out = _heading_case(text)
    if is_baseline_side:
        out = section_renumber(out, smap)[0]   # FIRST: keyed on baseline article numbers
        out = amap.renumber(out)
        out = _renumber_tables(out, amap)
        out = _renumber_frontmatter(out, amap)
    return _rewrap(out)


def normalize_old_side(text: str, *, amap, smap=None) -> str:
    """Render-SAFE normalisation for the OLD side of a redline.

    Heading case, section renumbering (Rule 6, with a map), cross-reference
    renumbering, table-number renumbering, and frontmatter `article-number`
    renumbering only -- NO re-wrapping. All five rewrite only digits/letters in
    narrow, fixed positions (a heading's leading letter, a section number, an
    `Article N` reference, a `TABLE N.x` caption, the frontmatter field), so
    none of them touches line structure.

    WHY NO REWRAP. redline_source() is line-based and EMITS the lines it is
    given, so anything done here reaches the rendered PDF. _rewrap() collapses
    indented continuations, which flattens the Code's lettered hierarchy into
    run-on prose -- measured: article-08-administration.md 211 sub-clause lines
    -> 4, body pages 113 -> 110. And it buys nothing: across all seven
    comparable pairs the marked-line count is the same with or without rewrap.
    Normalisation is legitimate for COMPARISON; feeding normalised text to the
    RENDERER is not.

    Rule 6 (section renumbering) applies when an `smap` is given, and runs
    first because that map is keyed on baseline article numbers.
    """
    out = _heading_case(text)
    out = section_renumber(out, smap)[0]       # FIRST: keyed on baseline article numbers
    out = amap.renumber(out)
    out = _renumber_tables(out, amap)
    out = _renumber_frontmatter(out, amap)
    return out


def _marked(o: list[str], n: list[str]) -> int:
    """How many lines differ between two line lists: the ONE counting rule.

    A non-empty unified diff always begins with exactly two file-header lines
    (`--- ` and `+++ `); every later line starting with `+` or `-` is a changed
    line. The previous filter dropped headers by PREFIX instead, which also
    dropped real changed lines beginning with -- or ++ -- a deleted `---`
    horizontal rule appears as `----`. Found 2026-10-08.
    """
    import difflib

    lines = list(difflib.unified_diff(o, n, n=0))
    return sum(1 for line in lines[2:] if line[:1] in "+-")


def changed_line_count(old: str, new: str, *, amap, smap=None) -> int:
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
    o = normalize_old_side(old, amap=amap, smap=smap).splitlines()
    n = new.splitlines()
    return _marked(o, n)


def report(old: str, new: str | None = None, *, amap, smap=None) -> dict[str, int]:
    """How many differences each rule suppressed, counted from the OLD side.

    Every rule normalize_old_side() applies is counted: heading case, Article
    references, table numbers, frontmatter, and -- when a section map is given
    -- section numbers. `rewrap` compares BOTH sides, so it appears only when
    `new` is given; the resolver has only the old side, and normalize_old_side
    does not rewrap anyway.

    ADOPTION-SPEC.md:155 promises these counts. Until 2026-10-08 the table and
    frontmatter rules were never counted. A suppressed mark is honest only if a
    reader can be shown how many there were.

    NOTE: the heading_case count is the number of baseline headings whose
    leading letter is uppercase -- exactly the ones the rule rewrites. (A count
    of matches before and after normalising `old` against itself was always
    zero, since case never changes how many headings match.)
    """
    def shifted(n: int) -> bool:
        return amap.article_numbers.get(n, n) != n

    counts = {
        "heading_case": sum(1 for m in _HEADING_LETTER.finditer(old) if m.group(2).isupper()),
        "renumber": sum(1 for m in re.finditer(r"\bArticle (\d+)\b", old)
                        if shifted(int(m.group(1)))),
        "tables": sum(1 for m in _TABLE_NUM.finditer(old) if shifted(int(m.group(2)))),
        "frontmatter": sum(1 for m in _FRONTMATTER_ARTICLE_NUMBER.finditer(old)
                           if shifted(int(m.group(2)))),
        "sections": section_renumber(old, smap)[1],
    }
    if new is not None:
        counts["rewrap"] = len(_WS_RUN.findall(old)) + len(_WS_RUN.findall(new))
    return counts
