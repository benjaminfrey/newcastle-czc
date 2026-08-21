r"""The W2 citation-verification harness.

Extracts every LOCAL Newcastle Core Zoning Code citation out of the nine real
"Findings of Fact & Conclusions of Law" decisions in
`docs/Findings of Fact and Conclusions of Law/` (the files whose names
contain "FoF & CoL"), resolves each one against the ADOPTED ruleset's node
index, and reports resolved / unresolved with the source document and the
surrounding sentence for every failure.

This module is NOT itself a CONTRACT.md-numbered artifact (CONTRACT.md is a
Phase 0/1 document; this is Phase-2 tooling), but it is disciplined by the
same spirit as CONTRACT.md §5 (citations are structured facts, verified
against real data — never asserted from a regex match alone) and §7
(ambiguity / missing data is reported, never guessed past). In particular:

  "Be rigorous about what counts as resolved: the node must actually exist
  in the adopted ruleset, not merely match a regex."

so a citation only becomes `resolved` when this module can point at the
actual ruleset record it names. Three ruleset sources are used for real
resolution:

  - `rulesets/adopted/articles.json` — a parallel workflow's Article/Section/
    Standard node index over the adopted Code's own prose (parsed directly
    from `docs/Newcastle Core Zoning Code.pdf`), landed partway through this
    module's development. `_resolve_against_articles()` documents its
    verified shape: 8 top-level Articles (1 General Standards ... 8
    Definitions, the true adopted numbering); each Article's direct children
    are lettered/numbered Section nodes; each Section's direct children are
    lettered Subsection nodes; a Subsection headed "APPROVAL STANDARDS" then
    carries its OWN, separately-lettered Standard items (e.g. Article 7,
    Section 12 SUBDIVISION's direct children are 17 subsections a-q (PURPOSE,
    APPLICABILITY, AUTHORITY, ... APPROVAL STANDARDS is 'f', ... ISSUANCE OF
    ZONING PERMITS is 'q'), and its 'f' child — APPROVAL STANDARDS — separately
    has ITS OWN, one-level-deeper lettered standards a-u (21 of them, under a
    lead-in item "1"; node ids `art7.12.f.1.a` .. `art7.12.f.1.u`; verified
    directly against both the adopted PDF and
    source/article-08-administration.md, letter for letter), so
    "Article 7, Section 12, Standard g. (Traffic)" resolves to node
    `art7.12.f.1.g`, not `art7.12.g` and not `art7.12.f.g`. (An earlier
    revision of this docstring said "d-u" here -- a typo for "a-u" -- and
    separately conflated the SUBSECTION count (17, a-q) with the STANDARD
    count (21, a-u) one tree level below it; the W2 gate briefly relied on
    that same conflation and is now hardened by
    `ruleset_build/verify_structure.py`'s mechanical set-equality assertions
    instead of a runner reading this comment.) That APPROVAL STANDARDS
    subsection's own
    letter is NOT stable across sections (confirmed: 'f' for Subdivision) —
    every lookup goes by heading text, never a hard-coded letter, per
    `_find_child_by_heading()`. It has NO 'table' node kind at all, so
    Table N.M citations are reported unresolved with that fact stated
    plainly. This module still treats the file's *absence* as a normal,
    reportable state (`idx.articles is None` → `missing_node_index`, never a
    crash) and wraps every lookup against it in a broad `except Exception`
    that falls back to `unrecognized_node_index_shape` — so if that parallel
    workflow's output shape ever changes, this module degrades to an honest
    "can't resolve this" instead of a traceback or a silent wrong answer.
  - `rulesets/adopted/use-matrix.json` (CONTRACT.md §4.3, built, committed)
    — District x Use cells, so "Industrial, Artisan is a permitted use in
    the SD - Fabrication District" can be checked for real.
  - `ruleset_build.slugs.DISTRICT_TABLE` (already-committed, non-dimensional
    ground truth for which of the 13 districts exist and their code/name —
    CONTRACT.md §4.1.1; this is NOT `districts.json`, which is still blocked
    by DECISIONS-NEEDED.md D-0001/D-0002, and this module never touches that
    blocked file or its dimensional data) — so "Article 2 District Standards
    for the D1 - Rural District" can be checked for real, structurally.

Excluded from the gate entirely (reported separately, never counted as a
citation failure) — verified against the real text of all nine decisions,
not just the task brief's examples:

  - Maine statute citations: any citation carrying "§", "M.R.S.A.", "MRS ",
    or "Title <N>," (30-A MRS §4401, 38 M.R.S.A. section 480-C, Title 12
    Section 8869, Title 23 Section 704).
  - Federal citations: "Section 106 ... National Historic Preservation Act"
    and the like.
  - Shoreland Zoning Ordinance citations: the Roman-numeral namespace
    (I.C, I.L, I.M, II.A.2, II.B, II.C.2, III.A, III.B — naturally excluded,
    since SZO section numbers are Roman and this module's Article/Section
    number groups require `\d`) plus its rarer Arabic-numbered sections
    ("Section 15. Land Use Standards for Piers, Docks...") and "Article III:
    Land Use Standards [of the Shoreland Zoning Ordinance]" — caught by a
    same-sentence "Shoreland Zoning" marker.
  - Road, Driveway & Entrance Ordinance citations — including the surprising
    one where the *number* "Article 2" is the RDEO's own Article 2, not the
    CZC's ("...standards set forth in the Road, Driveway, and Entrances
    Ordnance, and specifically Article 2 Standards, Section 1. Entrances.")
    — caught the same way, by a same-sentence RDEO marker, not by the
    citation text alone.
  - As a bonus (not in the task brief, but real and clearly non-local): a
    Maine Forest Service / DACF administrative-rule citation ("Section 5.
    Exemptions of Chapter 23 Rule ... set forth by the Maine Department of
    Conservation - Maine Forest Service").

Usage:
    python -m ruleset_build.verify_citations [--out PATH] [--quiet]

Also reachable as `python run.py --verify-citations` (app/main.py-adjacent
entry point wired in run.py, per the task brief).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

APP_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_ROOT.parent.parent
sys.path.insert(0, str(APP_ROOT))

from ruleset_build.slugs import DISTRICT_TABLE  # noqa: E402

DOCS_DIR = REPO_ROOT / "docs" / "Findings of Fact and Conclusions of Law"
RULESETS_DIR = APP_ROOT / "rulesets"
DATA_DIR = APP_ROOT / "data"
REPORT_PATH = DATA_DIR / "citation-report.json"

SCHEMA = "newcastle.citation-verification-report/1.0.0"


# --------------------------------------------------------------------------- #
# PDF text extraction
# --------------------------------------------------------------------------- #


class PdfLibraryUnavailable(RuntimeError):
    """pymupdf (fitz) is not importable. Caught at the top level so the tool
    reports cleanly (per the task brief: "code defensively... report cleanly
    rather than crashing") instead of a bare traceback."""


@dataclass
class DocText:
    """One decision PDF's extracted text plus enough bookkeeping to report a
    page number and a source-sentence window for every match found in it."""

    filename: str
    text: str
    page_starts: list[int]  # char offset each page begins at, ascending

    def page_of(self, offset: int) -> int:
        """1-indexed page number containing `offset`."""
        lo, hi = 0, len(self.page_starts) - 1
        page = 0
        for i, start in enumerate(self.page_starts):
            if start <= offset:
                page = i
            else:
                break
        return page + 1


def extract_pdf_text(path: Path) -> DocText:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:  # pragma: no cover - environment-dependent
        raise PdfLibraryUnavailable(
            "pymupdf is not installed (added to requirements.txt for this "
            "module; run `pip install -r requirements.txt` in the app venv)"
        ) from e

    doc = fitz.open(str(path))
    try:
        parts: list[str] = []
        page_starts: list[int] = []
        offset = 0
        for page in doc:
            page_starts.append(offset)
            t = _degunk(page.get_text())
            parts.append(t)
            offset += len(t) + 1  # +1 for the "\n" join below
        text = "\n".join(parts)
        return DocText(filename=path.name, text=text, page_starts=page_starts)
    finally:
        doc.close()


# These decision PDFs use zero-width Unicode characters as bullet-list
# formatting artifacts (observed: "Moved by:​ Scott Shott", "b.​ The
# Newcastle Road..."). Python's `\s` does NOT match them (they are Unicode
# category Cf, not White_Space), so every regex in this module that reasons
# about "is there whitespace here" — including the sentence/scope-window
# boundary detector — silently fails right where one of these characters
# sits. Replaced 1-for-1 with an ordinary space (never deleted) so every
# character offset this module computes (match spans, page_starts, context
# windows) stays valid without any downstream adjustment.
_ZERO_WIDTH_RE = re.compile("[\u200b\u200c\u200d\ufeff]")  # ZWSP, ZWNJ, ZWJ, BOM


def _degunk(t: str) -> str:
    return _ZERO_WIDTH_RE.sub(" ", t)


def find_decision_pdfs() -> list[Path]:
    """The nine real decisions: files under DOCS_DIR whose name contains
    "FoF & CoL" (the task brief's own selector). Sorted for determinism."""
    if not DOCS_DIR.is_dir():
        return []
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_file() and "FoF & CoL" in p.name)


# --------------------------------------------------------------------------- #
# Sentence-window context + exclusion-scope detection
# --------------------------------------------------------------------------- #

# ':' and ';' are always hard boundaries in these documents (they introduce
# or separate CONCLUSIONS OF LAW list items, e.g. "...set forth in the Core
# Zoning Code and the Shoreland Zoning Ordinance, specifically: under Article
# 2 ...; under Article 6 ...; and under Article 7 ..." — without a hard break
# on ':' and ';' regardless of following case, a window walks straight past
# the colon into an unrelated preamble and can pick up a false RDEO/SZO
# exclusion marker that scopes the *other* list, not this citation). '.'
# still requires an upper-case (or '(') follow, since it is heavily overused
# mid-citation ("Section 12.", "Standard g.").
_SENT_BOUNDARY = re.compile(
    r"[.][\"'‘’“”)]*\s+(?=[A-Z(])"  # "...Act.”\nSection 11..." / "...Code.\nArticle 7..."
    r"|\)\s+(?=[A-Z(])"  # a closing parenthetical is its own self-contained unit — a
    #                        trailing "(see review under Road, Driveway, and Entrance
    #                        Ordinance, below) Section 5. Natural Screening" must not let
    #                        the parenthetical's own subject leak into the NEXT heading's
    #                        or citation's scope classification
    r"|[.]\s+(?=[a-z]\.\s)"  # "...outside of Article 7, Section 12. Subdivision. b.​ The
    #                            Newcastle Road, Driveway..." — a lowercase lettered list
    #                            marker ("b.") signals a NEW enumerated item starting, so
    #                            the PRIOR item's citation must not read forward into it
    r"|[:;]\s+|\n\s*\n"
)
# The optional [\"'‘...] run after the period matters: a real sentence
# in these PDFs often ends "...Act.”\n" -- a closing smart quote BEFORE
# the newline -- so a bare "period then whitespace" test misses the
# boundary entirely and a window walks straight through a whole finished
# sentence into the next one (observed: a federal "Section 106 ... National
# Historic Preservation Act.”" sentence bled into the backward-window
# scope check for an unrelated "Section 11. Large Project Plan" heading
# right after it, wrongly excluding a genuine CZC heading as "federal").


def _backward_boundary(text: str, back_limit: int, pos: int) -> int:
    """The offset right after the LAST sentence-ish boundary in
    text[back_limit:pos], or `back_limit` if none. Searched with `endpos =
    pos + 2` rather than bare `pos`: `_SENT_BOUNDARY`'s trailing `(?=[A-Z(])`
    lookahead needs to see the first character AT `pos` (the citation's own
    first letter) to recognize a boundary that ends exactly there (e.g.
    '...Act.”\\nSection 11...' — the boundary IS right before "Section", so
    the lookahead must be able to see the 'S'). `re.finditer(s, pos, endpos)`
    otherwise truncates the string as if it ended at `endpos`, so a
    lookahead needing to peek at `pos` itself silently fails and the
    boundary is missed entirely — this was a real bug during development
    (a whole unrelated federal-citation sentence bled backward into a
    heading's scope-classification window because of exactly this)."""
    w_start = back_limit
    for m in _SENT_BOUNDARY.finditer(text, back_limit, min(len(text), pos + 2)):
        if m.start() < pos:
            w_start = m.end()
    return w_start


def _forward_boundary(text: str, pos: int, fwd_limit: int) -> int:
    """Forward counterpart to _backward_boundary() — the offset of the end
    of the first sentence-ish boundary at or after `pos`, or `fwd_limit` if
    none. `endpos` extended by 2 for the same lookahead reason."""
    m = _SENT_BOUNDARY.search(text, pos, min(len(text), fwd_limit + 2))
    if m and m.start() < fwd_limit:
        return min(m.end(), fwd_limit)
    return fwd_limit


def sentence_window(text: str, start: int, end: int, *, max_back: int = 400, max_fwd: int = 300) -> str:
    """Best-effort "surrounding sentence" for a match at text[start:end] —
    walks back/forward to the nearest sentence-ish boundary within a capped
    window, since these PDFs' extracted text has irregular whitespace and a
    true sentence tokenizer is overkill for a context string."""
    back_limit = max(0, start - max_back)
    fwd_limit = min(len(text), end + max_fwd)
    w_start = _backward_boundary(text, back_limit, start)
    w_end = _forward_boundary(text, end, fwd_limit)
    return _normalize_ws(text[w_start:w_end])


def backward_window(text: str, start: int, *, max_back: int = 400) -> str:
    """Backward-only counterpart to sentence_window(), used ONLY to classify
    the scope of a heading-origin candidate (Candidate.origin == "heading").

    A document heading's own scope is set by what GROUPS it (a preceding
    label like "Road, Driveway, and Entrances Ordnance Review" sitting right
    above the RDEO's own genuine "Article 2 - Standards" / "Section 1.
    Entrances" heading pair) — never by what follows it, which is just the
    body prose the heading introduces and may itself mention an unrelated
    ordinance in passing (a real, observed case: a CZC "Article 3 - Site
    Standards / Section 2. Driveways" heading is immediately followed by the
    parenthetical "(see review under Road, Driveway, and Entrance Ordinance,
    below)" — forward-looking classification wrongly excluded this genuine
    CZC heading and, through context carry-forward, corrupted every bare
    Section heading after it in the same document). Fixed by never looking
    forward past a heading's own matched text for scope classification."""
    back_limit = max(0, start - max_back)
    w_start = _backward_boundary(text, back_limit, start)
    return _normalize_ws(text[w_start:start])


def scope_window(text: str, start: int, end: int, *, max_back: int = 400, max_fwd: int = 300) -> str:
    """Like sentence_window(), but EXCLUDES the citation's own matched text
    [start:end] from the returned string — used only for exclusion-marker
    classification, never for the human-facing "context" field.

    Real, observed case this fixes: "Article 7, Section 12, Standard b. (The
    Newcastle Road, Driveway, and Entrance Ordinance)" is a genuine, in-scope
    CZC citation (Standard b. of Article 7 Section 12 happens to REQUIRE
    RDEO compliance, so the Code's own text names the RDEO as this
    standard's SUBJECT, same shape as "Standard g. (Traffic)" for every
    other lettered standard) — not a citation TO the RDEO. Because the
    parenthetical name is part of THIS citation's own matched span, scanning
    the citation's own text for exclusion markers wrongly excluded it. A
    marker must appear in the surrounding prose, not inside the citation's
    own name/heading text, to mean "this citation belongs to a different
    ordinance"."""
    back_limit = max(0, start - max_back)
    fwd_limit = min(len(text), end + max_fwd)
    w_start = _backward_boundary(text, back_limit, start)
    w_end = _forward_boundary(text, end, fwd_limit)
    return _normalize_ws(text[w_start:start] + " " + text[end:w_end])


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# Exclusion markers, checked against the sentence window. Order doesn't
# matter (first hit wins; they are not expected to co-occur).
_EXCLUSION_MARKERS: list[tuple[str, re.Pattern]] = [
    ("maine_statute", re.compile(r"§|M\.\s*R\.\s*S\.\s*A?\.?|(?<!\w)MRS(?!\w)|\bTitle\s+\d+\b", re.IGNORECASE)),
    ("federal", re.compile(r"National Historic Preservation Act|U\.S\.C\.|\bCFR\b|federal", re.IGNORECASE)),
    ("shoreland_zoning_ordinance", re.compile(r"Shoreland\s+Zoning", re.IGNORECASE)),
    (
        "road_driveway_entrance_ordinance",
        re.compile(r"Road,\s*Driveway,?\s*(?:and|&)\s*Entrances?\s*Ord", re.IGNORECASE),
    ),
    (
        "maine_administrative_rule",
        re.compile(r"Maine Forest Service|Maine Department of|Chapter\s+\d+\s+Rule", re.IGNORECASE),
    ),
]


def classify_scope(window_text: str) -> str | None:
    """Returns the exclusion reason if `window_text` carries a marker for a
    non-local (statute/federal/SZO/RDEO/state-rule) citation, else None (the
    citation is in local-CZC gate scope)."""
    for reason, pat in _EXCLUSION_MARKERS:
        if pat.search(window_text):
            return reason
    return None


# --------------------------------------------------------------------------- #
# Format matchers
#
# Applied in priority order (most specific/longest structural match first) so
# that a citation matched by an earlier, more specific pattern is not also
# re-captured by a later, looser one at the same text position. Each matcher
# returns zero or more parsed sub-citations from one regex match (a "Standard
# g., h., i." list, or an "including Section A..., Section B..." list, each
# expand to one citation per item).
# --------------------------------------------------------------------------- #


@dataclass
class Candidate:
    format: str
    start: int
    end: int
    raw: str
    parsed: dict[str, Any]
    # "heading" = matched from a standalone document heading line (e.g. an
    # "Article N - Name" / "Section M. Name" pair on their own lines, per
    # RE_HEADER_TRAIL / RE_SECTION_PART_TRAIL) — the strong, reliable signal
    # for "what Article/Section is this part of the document under" that
    # later bare citations infer from. "inline" (the default) = matched from
    # ordinary prose, e.g. a supporting cross-reference mid-sentence like
    # "under Article 2 - District Standards for the Rural Highway district,
    # a Level 4 Natural Screen is required..." embedded INSIDE the discussion
    # of a different section. An inline mention must resolve correctly on
    # its own (and does — it always carries an explicit article number), but
    # MUST NOT reset the ambient "current heading" context, or a later bare
    # "Section 8. Fences & Walls" heading a few lines after that aside would
    # be mis-inferred as belonging to the aside's Article instead of the
    # Article the document is actually structured under at that point. This
    # exact failure was observed and fixed during development (see
    # apply_context_carry_forward()).
    origin: str = "inline"
    exclude_reason: str | None = None  # set by classify_scope() before context carry-forward runs


Matcher = Callable[[re.Match], list[Candidate]]


def _trim_name(s: str | None) -> str | None:
    if s is None:
        return None
    # _normalize_ws first: several name-capturing groups allow \s (not just
    # literal space) so they can match across a PDF line-wrap mid-name (e.g.
    # "...for the Rural\nHighway district...") -- collapse that back to a
    # single space before trimming, or a name like "Rural\nHighway" would
    # never casefold-match DISTRICT_TABLE's "RURAL HIGHWAY".
    s = _normalize_ws(s).strip(" .,-")
    return s or None


# ---- F1: header trail — "Article N - Name" / "Section M. Name" / "Part X. Name"
#      each alone on its own line, immediately consecutive (a decision
#      document's own section headings, which double as citations to the
#      Code section they group findings under).
_HEADER_LINE_ART = r"^Article\s+(?P<article>\d{1,2})(?!-)[ \t]*(?:[-–—][ \t]*)?(?P<art_name>[A-Za-z][A-Za-z0-9 &'/.]*?)?[ \t]*$"
_HEADER_LINE_SEC = r"^Section\s+(?P<section>\d{1,3})\.[ \t]*(?P<sec_name>[A-Za-z][A-Za-z0-9 &'/.]*?)[ \t]*$"
_HEADER_LINE_PART = r"^Part\s+(?P<part>[A-Z])\.[ \t]*(?P<part_name>[A-Za-z][A-Za-z0-9 &'/.]*?)[ \t]*$"

RE_HEADER_TRAIL = re.compile(
    _HEADER_LINE_ART + r"\n+" + _HEADER_LINE_SEC + r"(?:\n+" + _HEADER_LINE_PART + r")?",
    re.MULTILINE,
)


def _m_header_trail(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {
        "article": int(g["article"]),
        "article_name": _trim_name(g.get("art_name")),
        "section": g["section"],
        "section_name": _trim_name(g.get("sec_name")),
    }
    fmt = "article_section"
    if g.get("part"):
        parsed["part"] = g["part"]
        parsed["part_name"] = _trim_name(g.get("part_name"))
        fmt = "article_section_part"
    return [Candidate(fmt, m.start(), m.end(), _normalize_ws(m.group(0)), parsed, origin="heading")]


# ---- F2: bare "Section N. Name" immediately followed by "Part X. Name" on
#      the next line, WITHOUT a preceding "Article" header line (the
#      CONTRACT-listed "Section N. Name / Part X. Name" format on its own).
RE_SECTION_PART_TRAIL = re.compile(_HEADER_LINE_SEC + r"\n+" + _HEADER_LINE_PART, re.MULTILINE)


def _m_section_part_trail(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {
        "article": None,  # resolved later from same-document "last article" context
        "section": g["section"],
        "section_name": _trim_name(g.get("sec_name")),
        "part": g["part"],
        "part_name": _trim_name(g.get("part_name")),
    }
    return [Candidate("section_part", m.start(), m.end(), _normalize_ws(m.group(0)), parsed, origin="heading")]


# ---- F2b: bare "Article N - Name" alone on its own line, with NO
#      immediately-following "Section M. Name" line (so RE_HEADER_TRAIL
#      above did not match) -- e.g. a decision that inserts its own caption
#      lines ("1." / "Use Standards, Applicability") between the Article
#      heading and the Section heading it introduces:
#          Article 6 - Use Standards
#          1.
#          Use Standards, Applicability
#          Section 53. Residence
#      Reuses _HEADER_LINE_ART's exact grammar (same restricted character
#      class, anchored start-of-line AND end-of-line) so this still cannot
#      fire on an inline mid-sentence mention -- a genuine aside like "under
#      Article 2 - District Standards for the Rural Highway district, a
#      Level 4 Natural Screen is required..." contains a comma the character
#      class excludes, so it can never satisfy `$` and never matches here.
#      Tried AFTER RE_HEADER_TRAIL/RE_SECTION_PART_TRAIL (so a real paired
#      header still wins the span) and BEFORE RE_ARTICLE_ONLY (the generic
#      inline catch-all), so a genuine standalone Article heading line is
#      tagged origin="heading" instead of falling through to an inline,
#      context-inert match. Format stays "article_only" -- same shape
#      RE_ARTICLE_ONLY would have produced -- only `origin` differs.
RE_ARTICLE_HEADING_ALONE = re.compile(_HEADER_LINE_ART, re.MULTILINE)


def _m_article_heading_alone(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"article": int(g["article"]), "name": _trim_name(g.get("art_name"))}
    return [Candidate("article_only", m.start(), m.end(), _normalize_ws(m.group(0)), parsed, origin="heading")]


# ---- F3: "Article N, Section M, Standard(s) <letter-list>[.] [(Name)]"
#      e.g. "Article 7, Section 12, Standard g. (Traffic)"
#           "Article 7, Section 12, Standards c, d, e, f, h, i, k, l, m, p, q, s, t"
RE_ARTICLE_SECTION_STANDARDS = re.compile(
    r"Article\s+(?P<article>\d{1,2})(?!-)"
    r"(?:\s+(?:[-–—]\s*)?[A-Za-z][A-Za-z0-9 &'/.]*?)?"  # optional Article name, dash before it optional
    r",?\s*Section\s+(?P<section>\d{1,3}),?\s*"
    r"Standards?\s+(?P<letters>[a-z](?:\s*,\s*[a-z])*(?:\s*,?\s*and\s+[a-z])?)\.?"
    r"(?:\s*\((?P<name>[^)]+)\))?"
)


def _m_article_section_standards(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    letters = re.findall(r"[a-z]", g["letters"])
    name = _trim_name(g.get("name"))
    out = []
    for letter in letters:
        parsed = {
            "article": int(g["article"]),
            "section": g["section"],
            "standard": letter,
            "standard_name": name if len(letters) == 1 else None,
        }
        raw = f"Article {g['article']}, Section {g['section']}, Standard {letter}." + (f" ({name})" if name and len(letters) == 1 else "")
        out.append(Candidate("article_section_standard", m.start(), m.end(), raw, parsed))
    return out


# ---- F4: "Article N [Name], including Section A. NameA, Section B. NameB,
#      and Section Z. NameZ" — a list of sections cited under one article.
RE_ARTICLE_INCLUDING_SECTIONS = re.compile(
    r"Article\s+(?P<article>\d{1,2})(?!-)"
    r"(?:\s+(?P<art_name>[A-Za-z][A-Za-z0-9 &'/]*?))?"
    r",?\s+including\s+(?P<list>Section\s+\d{1,3}\.[^;.]*?)(?=[;.](?:\s|$))"
)
_SECTION_ITEM_RE = re.compile(r"Section\s+(?P<section>\d{1,3})\.\s*(?P<name>[A-Za-z][A-Za-z0-9 &'/]*)")


def _m_article_including_sections(m: re.Match) -> list[Candidate]:
    article = int(m.group("article"))
    art_name = _trim_name(m.group("art_name"))
    out = []
    for item in _SECTION_ITEM_RE.finditer(m.group("list")):
        parsed = {
            "article": article,
            "article_name": art_name,
            "section": item.group("section"),
            "section_name": _trim_name(item.group("name")),
        }
        raw = f"Article {article}, Section {item.group('section')}. {_trim_name(item.group('name'))}"
        out.append(Candidate("article_section", m.start(), m.end(), raw, parsed))
    return out


# ---- F5: "Article N, Sec[tion]. M.L[.] Name" — dotted subsection letter.
#      e.g. "Article 2, Sec. 3.B. Applicability"
#           "Article 2, Section 2.D. Nonconforming Lots"
RE_ARTICLE_SEC_DOTTED = re.compile(
    r"Art(?:icle)?\.?\s+(?P<article>\d{1,2})(?!-),?\s*Sec(?:tion|\.)\s+(?P<section>\d{1,3})\.(?P<sub>[A-Z])\.?"
    # NOTE: no digits in the name class, and an explicit "next token is a
    # digit" cutoff -- "Article 7 Section 15.C and 15.D respectively." would
    # otherwise let the name greedily swallow "and 15" right up to the "."
    # of "15.D" (that "." satisfies the [,.;)] lookahead too), corrupting
    # this match AND eating the digits the next citation ("15.D") needs.
    r"(?:\s+(?P<name>[A-Za-z][A-Za-z &',/]*?)(?=[,.;)]|\s+\d|\s*$))?"
)


def _m_article_sec_dotted(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {
        "article": int(g["article"]),
        "section": g["section"],
        "subsection": g["sub"],
        "name": _trim_name(g.get("name")),
    }
    return [Candidate("article_section_subsection", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F6: "Article N.M Name." — dotted Article.Section shorthand with no
#      "Section" keyword at all. e.g. "Article 7.2 General Procedures."
#                                      "Article 7.29 Life Safety."
RE_ARTICLE_DOT_SECTION = re.compile(
    r"Article\s+(?P<article>\d{1,2})\.(?P<section>\d{1,3})\s+(?P<name>[A-Za-z][A-Za-z0-9 &']*?)\."
)


def _m_article_dot_section(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"article": int(g["article"]), "section": g["section"], "section_name": _trim_name(g["name"])}
    return [Candidate("article_section", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F7: "Use Table for <CODE> - <Name> District under Article 2, <Use> is
#      a[n] permitted/prohibited use" — a District x Use citation that
#      resolves against the real, committed use-matrix.json.
RE_ARTICLE2_USE_CELL = re.compile(
    r"Use\s+Table\s+for\s+(?:the\s+)?(?P<dcode>D\d|SD)\s*-?\s*(?P<dname>[A-Za-z][A-Za-z ]*?)\s+District\s+under\s+Article\s+2,\s*"
    r"(?P<use>[A-Za-z][A-Za-z ,]*?)\s+is\s+an?\s+(?P<allowed>not\s+a\s+permitted|permitted|prohibited|not\s+allowed|allowed)\s+use",
    re.DOTALL,
)


def _m_article2_use_cell(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {
        "article": 2,
        "district_code": g["dcode"],
        "district_name": _trim_name(g["dname"]),
        "use_label": _trim_name(g["use"]),
        "allowed_phrase": g["allowed"],
    }
    return [Candidate("article2_use_cell", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F8: "Article N [-] District Standards for the [<CODE> -] <Name>
#      District" (or lowercase "district") — resolves against DISTRICT_TABLE.
RE_ARTICLE2_DISTRICT_REF = re.compile(
    r"Article\s+(?P<article>\d{1,2})(?!-)\s*(?:[-–—]\s*)?District Standards\s+for\s+the\s+"
    # dname allows \s (not just literal space): "...for the Rural\nHighway
    # district..." wraps across a PDF line break mid-name in the real text.
    r"(?:(?P<dcode>D\d|SD)\s*-?\s*)?(?P<dname>[A-Za-z][A-Za-z\s]*?)\s+[Dd]istrict\b"
)


def _m_article2_district_ref(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {
        "article": int(g["article"]),
        "district_code": g.get("dcode"),
        "district_name": _trim_name(g["dname"]),
    }
    return [Candidate("article_district_ref", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F9: "Article N, Section M[.] [Name]" (comma or bare space form,
#      "Section" spelled out; the general workhorse pattern).
RE_ARTICLE_SECTION = re.compile(
    r"Article\s+(?P<article>\d{1,2})(?!-)"
    r"(?:\s+(?:[-–—]\s*)?[A-Za-z][A-Za-z0-9 &'/.]*?)?"  # optional Article name, dash before it optional
    r",?\s+Section\s+(?P<section>\d{1,3})\.?"
    r"(?:\s+(?P<name>[A-Za-z][A-Za-z &',/]*?)(?=[,.;)]|\s+\d|\s*$))?"
)


def _m_article_section(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"article": int(g["article"]), "section": g["section"], "section_name": _trim_name(g.get("name"))}
    return [Candidate("article_section", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F10: bare "Article N" (optionally "- Name" / ", Name"), nothing else
#      bound to it. The catch-all, tried last.
RE_ARTICLE_ONLY = re.compile(
    r"Article\s+(?P<article>\d{1,2})(?!-)"
    r"(?:\s*[-–—,]\s*(?P<name>[A-Za-z][A-Za-z0-9 &'/]*))?"
)


def _m_article_only(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"article": int(g["article"]), "name": _trim_name(g.get("name"))}
    return [Candidate("article_only", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F11: "Table N.M[:] Name"
RE_TABLE = re.compile(
    r"Table\s+(?P<num>\d{1,2}\.\d{1,2}):?\s+(?P<name>[A-Za-z][A-Za-z &',/]*?)(?=[,.;)]|\s+\d|\s*$)"
)


def _m_table(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"table": g["num"], "table_name": _trim_name(g["name"])}
    return [Candidate("table", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F12: bare "Section N. Name" with no preceding Article on the same
#      clause — resolved (if at all) via same-document "last article seen".
RE_SECTION_BARE_INLINE = re.compile(
    r"(?<!Article )Section\s+(?P<section>\d{1,3})\.\s+(?P<name>[A-Za-z][A-Za-z &',/]*?)(?=[,.;)]|\s+\d|\s*$)",
    re.MULTILINE,
)


def _m_section_bare(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"article": None, "section": g["section"], "section_name": _trim_name(g["name"])}
    return [Candidate("section_bare", m.start(), m.end(), _normalize_ws(m.group(0)), parsed)]


# ---- F13: bare dotted "N.L" subsection (e.g. "15.D") standing alone,
#      resolved only via the same-document "last article + last section"
#      context left by a recent explicit citation (e.g. "...follow those of
#      Article 7 Section 15.C and 15.D respectively.").
RE_SECTION_DOTTED_BARE = re.compile(r"(?<![.\d])\b(?P<section>\d{1,3})\.(?P<sub>[A-Z])\b(?!\w)")


def _m_section_dotted_bare(m: re.Match) -> list[Candidate]:
    g = m.groupdict()
    parsed = {"article": None, "section": g["section"], "subsection": g["sub"]}
    return [Candidate("section_subsection_bare", m.start(), m.end(), m.group(0), parsed)]


# Priority order: most specific / structurally richest first.
MATCHERS: list[tuple[re.Pattern, Matcher]] = [
    (RE_HEADER_TRAIL, _m_header_trail),
    (RE_SECTION_PART_TRAIL, _m_section_part_trail),
    (RE_ARTICLE_HEADING_ALONE, _m_article_heading_alone),
    (RE_ARTICLE_SECTION_STANDARDS, _m_article_section_standards),
    (RE_ARTICLE_INCLUDING_SECTIONS, _m_article_including_sections),
    (RE_ARTICLE2_USE_CELL, _m_article2_use_cell),
    (RE_ARTICLE2_DISTRICT_REF, _m_article2_district_ref),
    (RE_ARTICLE_SEC_DOTTED, _m_article_sec_dotted),
    (RE_ARTICLE_DOT_SECTION, _m_article_dot_section),
    (RE_ARTICLE_SECTION, _m_article_section),
    (RE_ARTICLE_ONLY, _m_article_only),
    (RE_TABLE, _m_table),
    (RE_SECTION_BARE_INLINE, _m_section_bare),
    (RE_SECTION_DOTTED_BARE, _m_section_dotted_bare),
]


def _spans_overlap(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def scan_document(text: str) -> list[Candidate]:
    """Runs every matcher over `text` in priority order, claiming spans so a
    later (looser) matcher never re-captures text a more specific matcher
    already consumed."""
    claimed: list[tuple[int, int]] = []
    candidates: list[Candidate] = []
    for pattern, handler in MATCHERS:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if any(_spans_overlap(span, c) for c in claimed):
                continue
            new = handler(m)
            if not new:
                continue
            claimed.append(span)
            candidates.extend(new)
    candidates.sort(key=lambda c: c.start)
    return candidates


# --------------------------------------------------------------------------- #
# "Last article / last section" context carry-forward (for bare Section /
# dotted-subsection citations that omit the Article they belong to, e.g.
# "Article 7 Section 15.C and 15.D respectively" or a "Section 18. Special
# Use Permit" heading that follows an "Article 7 - Administration" heading
# several lines above it without repeating "Article 7").
# --------------------------------------------------------------------------- #


def apply_context_carry_forward(candidates: list[Candidate]) -> None:
    """Two INDEPENDENT context mechanisms, deliberately not shared, because
    they answer different questions:

    1. `last_heading_article` — "what Article is this part of the document
       currently under", used to infer the Article for a bare "Section N.
       Name" or "Section N. Name / Part X. Name" HEADING that omits it.
       Updated ONLY by a document HEADING (Candidate.origin == "heading")
       that is itself in CZC gate scope. An inline cross-reference
       mid-sentence (e.g. "under Article 2 - District Standards for the
       Rural Highway district, a Level 4 Natural Screen is required...")
       must NOT reset this, or a later bare "Section 8. Fences & Walls"
       heading several lines after that aside would be mis-inferred as
       belonging to the aside's Article instead of the Article the document
       is actually structured under at that point. Likewise a heading that
       is itself out-of-gate-scope (the RDEO has its own genuine "Article 2
       - Standards" / "Section 1. Entrances" heading pair, in ITS numbering)
       must not seed the CZC context either — both failure modes were
       observed and fixed during development.

    2. `last_dotted` — "what (article, section) did the immediately
       surrounding text just explicitly cite", used ONLY to resolve a bare
       dotted subsection like "15.D" that trails a same-sentence explicit
       citation ("...follow those of Article 7 Section 15.C and 15.D
       respectively."). This is a much TIGHTER, same-sentence linkage than
       #1, so unlike #1 it IS updated by an inline (non-heading) explicit
       article+section citation — the two mechanisms would give the wrong
       answer for each other's case if merged: an inline aside must not set
       the document's heading context (#1), but an inline "Section 15.C"
       absolutely should be able to hand its article to the "15.D" two words
       later (#2). Gated on the SECTION NUMBER matching (not merely "some
       article was seen recently"), so an unrelated bare "N.L" elsewhere
       (a lot dimension, a percentage) is correctly left unresolved rather
       than guessed at — see the `_plausible_context` check below.
    """
    last_heading_article: int | None = None
    last_heading_article_name: str | None = None
    last_dotted: tuple[int, str] | None = None  # (article, section)

    for c in candidates:
        art = c.parsed.get("article")
        section = c.parsed.get("section")

        if isinstance(art, int) and c.origin == "heading" and c.exclude_reason is None:
            last_heading_article = art
            last_heading_article_name = c.parsed.get("article_name") or c.parsed.get("name")
        elif art is None and c.format in ("section_bare", "section_part"):
            c.parsed["article"] = last_heading_article
            c.parsed["article_name_inferred"] = last_heading_article_name
            c.parsed["article_inferred"] = last_heading_article is not None

        if isinstance(art, int) and section and c.exclude_reason is None:
            last_dotted = (art, section)

        if c.format == "section_subsection_bare":
            # A bare "15.D" is only meaningful right after a matching
            # "...Section 15...."-style citation established section 15 as
            # the active section; otherwise it's almost certainly just a
            # number in unrelated prose (a lot size, a percentage) and MUST
            # NOT be reported as a citation at all.
            if last_dotted is not None and last_dotted[1] == c.parsed["section"]:
                c.parsed["article"] = last_dotted[0]
                c.parsed["article_inferred"] = True
                c.parsed["_plausible_context"] = True
            else:
                c.parsed["article"] = None
                c.parsed["article_inferred"] = False
                c.parsed["_plausible_context"] = False


# --------------------------------------------------------------------------- #
# Node index — resolution against the ADOPTED ruleset
# --------------------------------------------------------------------------- #


@dataclass
class NodeIndex:
    articles: dict[str, Any] | None
    articles_error: str | None
    use_matrix: dict[str, Any] | None
    use_matrix_error: str | None
    manifest: dict[str, Any] | None
    districts_json_present: bool

    use_cells_by_pair: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    use_by_key: dict[str, dict[str, Any]] = field(default_factory=dict)
    use_by_label_cf: dict[str, str] = field(default_factory=dict)  # casefolded label -> use_key
    article_nodes_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)  # "art7.12.f.g" -> node
    article_counts: dict[str, Any] = field(default_factory=dict)  # articles.json's own counts{} block
    tables_by_number: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # "7.1" -> [node, ...]


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"{path.relative_to(REPO_ROOT)} does not exist"
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f), None
    except (json.JSONDecodeError, OSError) as e:
        return None, f"{path.relative_to(REPO_ROOT)} could not be read/parsed: {e}"


def load_node_index(ruleset_key: str = "adopted") -> NodeIndex:
    base = RULESETS_DIR / ruleset_key

    # articles.json — the Article/Section/Standard/Table prose node index.
    # NOT part of CONTRACT.md's Phase-1 schemas; being built by a parallel
    # workflow at the time this module was written. Missing is EXPECTED, not
    # an error: report cleanly, resolve nothing that needs it.
    articles, articles_error = _read_json(base / "articles.json")

    # use-matrix.json — CONTRACT.md §4.3, built and committed.
    use_matrix, use_matrix_error = _read_json(base / "use-matrix.json")

    manifest, _ = _read_json(base / "manifest.json")

    districts_json_present = (base / "districts.json").exists()

    idx = NodeIndex(
        articles=articles,
        articles_error=articles_error,
        use_matrix=use_matrix,
        use_matrix_error=use_matrix_error,
        manifest=manifest,
        districts_json_present=districts_json_present,
    )

    if use_matrix:
        for cell in use_matrix.get("cells", []):
            idx.use_cells_by_pair[(cell["district_key"], cell["use_key"])] = cell
        for use in use_matrix.get("uses", []):
            idx.use_by_key[use["use_key"]] = use
            idx.use_by_label_cf[use["label"].casefold()] = use["use_key"]

    if articles:
        idx.article_counts = articles.get("counts", {})
        for top in articles.get("articles", []):
            _flatten_article_node(top, idx.article_nodes_by_id)
        # "table" node kind (extract_adopted.py's TABLE_CAPTION_RE pass):
        # index every table node by its bare number ("7.1") -- a citation's
        # `table` field carries only the number, never an article (the
        # regex that scans decision text for "Table N.M Name" has no
        # article context to attach), so lookup is by number alone.
        # Some numbers are genuinely reused in the source for two DIFFERENT
        # tables (e.g. "3.1" is both SCREENING FORMULA and SITE LUMENS), so
        # this is a list, disambiguated by title at resolve time.
        for node in idx.article_nodes_by_id.values():
            if node.get("kind") == "table" and node.get("number"):
                idx.tables_by_number.setdefault(node["number"], []).append(node)

    return idx


def _flatten_article_node(node: dict[str, Any], out: dict[str, dict[str, Any]]) -> None:
    """Indexes every node in one Article's tree by its `id` (e.g. "art7",
    "art7.12", "art7.12.f", "art7.12.f.g") so resolution is an O(1) dict
    lookup rather than a tree walk per citation. Recurses through
    `children`, matching articles.json's actual shape (verified against the
    real, now-built rulesets/adopted/articles.json: {kind, article, number,
    heading, text, children, source_ref, id})."""
    node_id = node.get("id")
    if node_id:
        out[node_id] = node
    for child in node.get("children") or []:
        _flatten_article_node(child, out)


# CONTRACT.md §4.1.1's fixed district_key table, reconstructed here (NOT
# re-derived, NOT guessed) so use-matrix lookups can key on `district_key`
# exactly like ruleset_build/build_use_matrix.py does. Kept as a literal,
# ordered mirror of DISTRICT_TABLE, asserted equal-length at import time.
_DISTRICT_KEYS_BY_INDEX = [
    "d1", "d2", "d3", "d4", "d5", "d6",
    "sd-historic", "sd-conserve", "sd-hwy", "sd-rhwy", "sd-campus", "sd-marine", "sd-fab",
]
assert len(_DISTRICT_KEYS_BY_INDEX) == len(DISTRICT_TABLE)


def _slugify_district(name: str) -> str:
    return name.strip().casefold()


def find_district(code: str | None, name: str) -> dict[str, Any] | None:
    """Resolves a (code, name) or (None, name) pair against DISTRICT_TABLE —
    CONTRACT.md §4.1.1's fixed, committed ground truth for which districts
    exist. Exact name match (case-insensitive) disambiguates the seven
    same-`code` "SD" districts, since every district's `name` is unique.
    Returns {index, code, name, district_key} or None if no district in the
    real 13-district table matches."""
    name_cf = _slugify_district(name)
    for i, (idx, c, tname) in enumerate(DISTRICT_TABLE):
        if _slugify_district(tname) != name_cf:
            continue
        if code and c != code:
            continue
        return {"index": idx, "code": c, "name": tname, "district_key": _DISTRICT_KEYS_BY_INDEX[i]}
    return None


_ALLOWED_PHRASES = {"permitted", "allowed"}
_PROHIBITED_PHRASES = {"prohibited", "not allowed", "not a permitted"}


def resolve_candidate(c: Candidate, idx: NodeIndex) -> dict[str, Any]:
    """Returns {"status": "resolved"|"unresolved", "reason": str, "detail": ...}.
    Only ever returns "resolved" when a real ruleset record was found and
    matched — never on the strength of a regex match alone."""

    if c.format == "article_district_ref":
        p = c.parsed
        d = find_district(p.get("district_code"), p["district_name"])
        if d is None:
            return {
                "status": "unresolved",
                "code": "district_not_found",
                "reason": "no district in the adopted 13-district table (CONTRACT.md §4.1.1) "
                f"matches code={p.get('district_code')!r} name={p['district_name']!r}",
                "detail": None,
            }
        return {
            "status": "resolved",
            "code": "resolved",
            "reason": f"matched {d['code']} - {d['name']} (district_key={d['district_key']}) "
            "in ruleset_build.slugs.DISTRICT_TABLE — structural district existence only, "
            "NOT a dimensional-standard check (districts.json itself is still blocked by "
            "D-0001/D-0002)",
            "detail": d,
        }

    if c.format == "article2_use_cell":
        p = c.parsed
        if idx.use_matrix is None:
            return {"status": "unresolved", "code": "missing_node_index", "reason": f"use-matrix.json unavailable: {idx.use_matrix_error}", "detail": None}
        d = find_district(p.get("district_code"), p["district_name"])
        if d is None:
            return {
                "status": "unresolved",
                "code": "district_not_found",
                "reason": f"district {p.get('district_code')!r} {p['district_name']!r} not found in DISTRICT_TABLE",
                "detail": None,
            }
        use_key = idx.use_by_label_cf.get(p["use_label"].casefold())
        if use_key is None:
            return {
                "status": "unresolved",
                "code": "use_not_found",
                "reason": f"use {p['use_label']!r} not found in use-matrix.json uses[] (63 uses)",
                "detail": None,
            }
        cell = idx.use_cells_by_pair.get((d["district_key"], use_key))
        if cell is None:
            return {"status": "unresolved", "code": "cell_not_found", "reason": "no cell for that (district, use) pair in use-matrix.json", "detail": None}
        claimed_allowed = p["allowed_phrase"].casefold() in _ALLOWED_PHRASES
        actual_allowed = bool(cell["allowed"])
        if claimed_allowed != actual_allowed:
            return {
                "status": "unresolved",
                "code": "cell_disagrees",
                "reason": f"cell exists but disagrees with the document: document says "
                f"{p['allowed_phrase']!r}, use-matrix.json cell has allowed={actual_allowed}",
                "detail": cell,
            }
        return {
            "status": "resolved",
            "code": "resolved",
            "reason": f"matched use-matrix.json cell ({d['district_key']}, {use_key}): "
            f"allowed={actual_allowed}, permit={cell.get('permit')!r}",
            "detail": cell,
        }

    if c.format == "section_subsection_bare":
        if not c.parsed.get("_plausible_context"):
            return {
                "status": "unresolved",
                "code": "not_a_citation",
                "reason": "bare 'N.L' with no matching recent 'Section N....' context in this "
                "document — most likely NOT a citation at all (a lot dimension, a percentage); "
                "excluded from the gate count entirely rather than reported as a failure",
                "detail": None,
                "not_a_citation": True,
            }
        # falls through to the generic missing-node-index path below

    if idx.articles is None:
        return {
            "status": "unresolved",
            "code": "missing_node_index",
            "reason": "missing_node_index: rulesets/adopted/articles.json does not exist "
            f"({idx.articles_error}). This citation needs the Article/Section/Standard/Table node "
            "index over the adopted Code's prose Articles to resolve against. Not a failure of "
            "this citation — a gap in the ruleset, reported so it is not lost.",
            "detail": None,
        }

    try:
        return _resolve_against_articles(c, idx)
    except Exception as e:  # defensive: a shape this resolver doesn't expect must not crash the run
        return {
            "status": "unresolved",
            "code": "unrecognized_node_index_shape",
            "reason": f"unrecognized_node_index_shape: resolving against rulesets/adopted/"
            f"articles.json raised {type(e).__name__}: {e}",
            "detail": None,
        }


def _find_child_by_heading(node: dict[str, Any], heading_cf: str) -> dict[str, Any] | None:
    """Finds a direct child of `node` whose `heading` casefolds to
    `heading_cf`. Used to locate the "APPROVAL STANDARDS" subsection of a
    Section — its own letter is NOT stable across sections (Subdivision's is
    'f', Variance's is 'd', per the extraction grammar's own documented
    trap), so it must always be found by heading text, never by a hard-coded
    letter."""
    for child in node.get("children") or []:
        if (child.get("heading") or "").strip().casefold() == heading_cf:
            return child
    return None


def _standard_level_items(appstd: dict[str, Any]) -> list[dict[str, Any]]:
    """Returns the lettered-standards level under an APPROVAL STANDARDS
    subsection: the shallowest depth under `appstd`, breadth-first, at
    which non-digit-numbered items appear. This is DEPTH-SCOPED on purpose
    and deliberately stops at the first lettered frontier it finds — it
    never continues past it into whatever those items' own children are.

    That matters because a citation like "Article 7, Section 12, Standard
    i." means the top-level criterion i (Municipal Solid Waste Disposal),
    never the roman-numeral sub-item i. nested one level deeper under
    criterion "c. Pollution" (art7.12.f.1.c.i .. .c.v). A letter that also
    happens to be a valid lowercase roman numeral (i, v, x, l, c, d, m) can
    collide with such a nested sub-item under first-match-wins,
    depth-first, ANY-depth search — that was the bug (a citation to
    "Standard i." resolving to art7.12.f.1.c.i, the Pollution sub-item,
    instead of art7.12.f.1.i). Stopping at the shallowest lettered frontier
    makes that collision structurally impossible: c.i is one level below
    the frontier this function returns, so it is never a candidate.

    Handles both real subsection shapes seen in articles.json:
      - art7.10.e / .11.e / .13.e / .18.e / art7.12.f (SUBDIVISION): one
        digit-numbered lead-in item "1" (the "...upon verifying consistency
        to the following:" sentence) wrapping the lettered standards one
        level down — the frontier at depth 0 is all-digit ("1"), so this
        descends once and returns the a.. letters found there.
      - art7.19.d (VARIANCE): FOUR digit-numbered items (1-4) at the top,
        none of them itself the standards level — item 2 wraps a-b (general
        grounds), item 3 wraps a-d (Undue Hardship), item 4 wraps a-g
        (Practical Difficulty). This function does not special-case that:
        it keeps descending past every all-digit frontier, so it returns
        the UNION of every one of those lettered lists (13 items, with
        'a'..'d' each appearing twice under DIFFERENT parents). Whether
        that union contains more than one match for a given letter — i.e.
        whether the citation is genuinely ambiguous — is the caller's
        question to ask (see _find_standard_letter), not this function's.
    """
    frontier = [c for c in appstd.get("children") or [] if c.get("kind") == "item"]
    while frontier:
        lettered = [c for c in frontier if not (c.get("number") or "").isdigit()]
        if lettered:
            return lettered
        frontier = [
            g
            for c in frontier
            for g in (c.get("children") or [])
            if g.get("kind") == "item"
        ]
    return []


def _find_standard_letter(appstd: dict[str, Any], letter: str) -> list[dict[str, Any]]:
    """Finds every item AT THE LETTERED-STANDARDS LEVEL (see
    _standard_level_items — never any deeper, never any shallower) under an
    APPROVAL STANDARDS subsection whose `number` casefold-matches `letter`.

    Returns a LIST, not a single node or None — deliberately, so the
    caller can tell "no match" (len 0) apart from "exactly one match"
    (len 1) apart from "genuinely ambiguous" (len > 1, e.g. art7.19.d
    VARIANCE, where letter 'c' matches both the Undue Hardship criterion
    and the Practical Difficulty criterion — two different standards that
    happen to share a letter because they sit under different parent
    items). Callers MUST branch on len() and report >1 as ambiguous
    (CONTRACT.md §1 S7: no silent guessing) rather than take the first."""
    letter_cf = letter.casefold()
    return [
        item
        for item in _standard_level_items(appstd)
        if (item.get("number") or "").casefold() == letter_cf
    ]


def _resolve_against_articles(c: Candidate, idx: NodeIndex) -> dict[str, Any]:
    """Resolves one candidate against the real, built rulesets/adopted/
    articles.json — a tree of {kind, article, number, heading, text,
    children, id} nodes, `id` a dotted path like "art7.12.f.1.g" (verified
    directly against the built file: 8 top-level Articles 1-8 matching the
    adopted Code's own Article names; each Article's direct children are
    lettered/numbered "section" nodes; a section's direct children are
    lettered "subsection" nodes; a subsection like "APPROVAL STANDARDS" then
    has its own, separately-lettered "item" children ONE LEVEL DEEPER than a
    flat reading suggests -- e.g. Article 7, Section 12 (SUBDIVISION)'s direct
    children are 17 subsections a-q, and its 'f' child (APPROVAL STANDARDS) has
    exactly one direct item child ("1", the lead-in "...verifying consistency
    to the following:" sentence), and THAT item's own children are the 21
    lettered standards a-u, so "Article 7, Section 12, Standard g." means
    art7.12.f.1.g, NOT art7.12.g and NOT art7.12.f.g. (A prior revision of this
    docstring said "subsections a-q ... item children d-u", conflating the
    17-subsection count with the 21-standard count one level below it -- see
    `_standard_level_items()` below, which now finds this level generically
    instead of a docstring asserting it.)

    articles.json now carries a 'table' node kind (extract_adopted.py's
    TABLE_CAPTION_RE pass, added once the real Table N.M captions in the
    adopted PDF were found to render in the same font/size/color as a
    subsection heading and were being silently dropped rather than
    captured) — see idx.tables_by_number, keyed by bare table number
    ("7.1") since a Table citation in a decision never carries article
    context of its own.
    """
    by_id = idx.article_nodes_by_id
    p = c.parsed
    article = p.get("article")
    section = p.get("section")
    subsection = p.get("subsection")  # dotted form: "Article 2, Sec. 3.B."
    standard = p.get("standard")  # "Article 7, Section 12, Standard g."
    part = p.get("part")  # header-trail "Part E. Approval Standards"
    table = p.get("table")

    if table is not None:
        table_name = p.get("table_name")
        candidates = idx.tables_by_number.get(table, [])
        if not candidates:
            return {
                "status": "unresolved",
                "code": "no_table_node",
                "reason": f"no Table {table} node in articles.json (tables_by_number has: "
                f"{sorted(idx.tables_by_number)})",
                "detail": None,
            }
        # Disambiguate a reused table number (e.g. "3.1" is genuinely two
        # different tables in the source, SCREENING FORMULA and SITE
        # LUMENS) by title when the citation names one; otherwise, a
        # single candidate is an unambiguous match and multiple candidates
        # with no name to disambiguate by are reported honestly rather than
        # picked arbitrarily.
        match = None
        if table_name:
            name_cf = table_name.strip().casefold()
            match = next(
                (n for n in candidates if (n.get("heading") or "").strip().casefold() == name_cf), None
            )
            if match is None:
                match = next(
                    (n for n in candidates if name_cf in (n.get("heading") or "").strip().casefold()
                     or (n.get("heading") or "").strip().casefold() in name_cf),
                    None,
                )
        if match is None and len(candidates) == 1:
            match = candidates[0]
        if match is None:
            return {
                "status": "unresolved",
                "code": "ambiguous_table_number",
                "reason": f"Table {table} is ambiguous in articles.json — {len(candidates)} tables "
                f"share that number ({[n.get('heading') for n in candidates]!r}) and the citation's "
                f"name {table_name!r} did not disambiguate one",
                "detail": None,
            }
        reason = f"matched {match['id']} (Table {table} {match.get('heading')!r}) in articles.json"
        if table_name and table_name.strip().casefold() != (match.get("heading") or "").strip().casefold():
            reason += (
                f" — NOTE: the decision names it {table_name!r}, Code heading is "
                f"{match.get('heading')!r}; still resolved (matched by number), flagged for a human "
                "to double check the title wording"
            )
        return {"status": "resolved", "code": "resolved", "reason": reason,
                "detail": {"id": match["id"], "heading": match.get("heading")}}

    if article is None:
        return {
            "status": "unresolved",
            "code": "no_article_context",
            "reason": "no explicit or inferable Article number for this citation (a bare "
            "'Section N...' with no preceding Article anywhere earlier in the same document)",
            "detail": None,
        }

    art_id = f"art{article}"
    art_node = by_id.get(art_id)
    if art_node is None:
        return {
            "status": "unresolved",
            "code": "no_article_node",
            "reason": f"no Article {article} node in articles.json (the adopted Code has "
            f"Articles 1-{idx.article_counts.get('article', '?')})",
            "detail": None,
        }

    if section is None:
        return {
            "status": "resolved",
            "code": "resolved",
            "reason": f"matched Article {article} ({art_node.get('heading')}) in articles.json",
            "detail": {"id": art_id, "heading": art_node.get("heading")},
        }

    sec_id = f"{art_id}.{section}"
    sec_node = by_id.get(sec_id)
    if sec_node is None:
        return {
            "status": "unresolved",
            "code": "no_section_node",
            "reason": f"no Article {article}, Section {section} node in articles.json (Article "
            f"{article} — {art_node.get('heading')} — has {len(art_node.get('children') or [])} "
            "sections)",
            "detail": None,
        }

    if subsection is not None:
        sub_id = f"{sec_id}.{subsection.lower()}"
        sub_node = by_id.get(sub_id)
        if sub_node is None:
            return {
                "status": "unresolved",
                "code": "no_subsection_node",
                "reason": f"no Article {article}, Section {section}.{subsection} subsection node "
                f"in articles.json ({sec_id} is {sec_node.get('heading')!r})",
                "detail": None,
            }
        return {
            "status": "resolved",
            "code": "resolved",
            "reason": f"matched {sub_id} ({sub_node.get('heading')}) in articles.json",
            "detail": {"id": sub_id, "heading": sub_node.get("heading")},
        }

    if standard is not None:
        appstd = _find_child_by_heading(sec_node, "approval standards")
        if appstd is None:
            return {
                "status": "unresolved",
                "code": "no_approval_standards_subsection",
                "reason": f"Article {article}, Section {section} ({sec_node.get('heading')}) has "
                "no child subsection headed 'APPROVAL STANDARDS' in articles.json — searched by "
                "heading text, not a fixed letter, since that subsection's own letter is known to "
                "vary by section",
                "detail": None,
            }
        matches = _find_standard_letter(appstd, standard)
        if not matches:
            available = sorted(
                {it.get("number") for it in _standard_level_items(appstd) if it.get("number")}
            )
            return {
                "status": "unresolved",
                "code": "no_standard_letter",
                "reason": f"Article {article}, Section {section}'s APPROVAL STANDARDS ({appstd['id']}) "
                f"has no standard lettered {standard!r} at the lettered-standards level in "
                f"articles.json (it has: {available})",
                "detail": None,
            }
        if len(matches) > 1:
            candidate_ids = [m["id"] for m in matches]
            return {
                "status": "unresolved",
                "code": "ambiguous_standard_letter",
                "reason": f"Article {article}, Section {section}'s APPROVAL STANDARDS ({appstd['id']}) "
                f"has {len(matches)} DIFFERENT standards lettered {standard!r} at the "
                f"lettered-standards level ({candidate_ids!r}) — the citation does not say which "
                "one, so this is reported ambiguous rather than silently guessed (CONTRACT.md §1 S7)",
                "detail": {
                    "candidates": [
                        {"id": m["id"], "text_preview": (m.get("text") or "")[:160]} for m in matches
                    ]
                },
            }
        item = matches[0]
        detail = {"id": item["id"], "text_preview": (item.get("text") or "")[:160]}
        reason = f"matched {item['id']} under APPROVAL STANDARDS ({appstd['id']}) in articles.json"
        name_hint = p.get("standard_name")
        if name_hint and item.get("text") and not item["text"].strip().casefold().startswith(name_hint.strip().casefold()):
            reason += (
                f" — NOTE: the decision names this standard {name_hint!r}, but the Code text "
                f"begins {item['text'][:60]!r}; still resolved (the node exists), flagged for a "
                "human to double check the label"
            )
        return {"status": "resolved",
            "code": "resolved", "reason": reason, "detail": detail}

    if part is not None:
        appstd = _find_child_by_heading(sec_node, "approval standards")
        if appstd is None:
            return {
                "status": "unresolved",
                "code": "no_approval_standards_subsection",
                "reason": f"Article {article}, Section {section} ({sec_node.get('heading')}) has "
                "no child subsection headed 'APPROVAL STANDARDS' in articles.json",
                "detail": None,
            }
        detail = {"id": appstd["id"], "actual_letter": appstd.get("number")}
        reason = f"matched {appstd['id']} (APPROVAL STANDARDS) in articles.json"
        if (appstd.get("number") or "").casefold() != part.casefold():
            reason += (
                f" — NOTE: the decision calls it 'Part {part}', but the Code's own letter for this "
                f"subsection is {appstd.get('number')!r} (that subsection's letter is known to vary "
                "by section, so this is still a match on heading text, not a discrepancy in scope)"
            )
        return {"status": "resolved",
            "code": "resolved", "reason": reason, "detail": detail}

    # Plain "Article N, Section M" — no subsection, no standard letter, no part.
    reason = f"matched {sec_id} ({sec_node.get('heading')}) in articles.json"
    section_name_hint = p.get("section_name")
    if section_name_hint and sec_node.get("heading") and section_name_hint.strip().casefold() != sec_node["heading"].strip().casefold():
        reason += f" — NOTE: the decision calls it {section_name_hint!r}; the Code heading is {sec_node['heading']!r}"
    return {"status": "resolved",
            "code": "resolved", "reason": reason, "detail": {"id": sec_id, "heading": sec_node.get("heading")}}


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def build_report(ruleset_key: str = "adopted") -> dict[str, Any]:
    idx = load_node_index(ruleset_key)

    pdfs = find_decision_pdfs()
    entries: list[dict[str, Any]] = []
    format_counts: dict[str, int] = {}
    format_counts_excluded: dict[str, int] = {}
    exclude_reason_counts: dict[str, int] = {}
    not_a_citation_count = 0
    doc_errors: list[dict[str, str]] = []
    seq = 0

    for pdf in pdfs:
        try:
            docs = extract_pdf_text(pdf)
        except PdfLibraryUnavailable as e:
            doc_errors.append({"document": pdf.name, "error": str(e)})
            continue
        except Exception as e:  # defensive: one bad PDF must not sink the run
            doc_errors.append({"document": pdf.name, "error": f"extraction failed: {e}"})
            continue

        candidates = scan_document(docs.text)

        # Scope classification MUST run before context carry-forward: a
        # heading that is itself out-of-gate-scope (the RDEO has its own
        # genuine "Article 2 - Standards" / "Section 1. Entrances" heading
        # pair, in ITS numbering, not the CZC's) must not seed the CZC
        # "current Article" context that later bare CZC section headings
        # infer from. See apply_context_carry_forward()'s docstring comment.
        windows: dict[int, str] = {}
        for c in candidates:
            windows[id(c)] = sentence_window(docs.text, c.start, c.end)
            if c.origin == "heading":
                scope_text = backward_window(docs.text, c.start)
            else:
                scope_text = scope_window(docs.text, c.start, c.end)
            c.exclude_reason = classify_scope(scope_text)

        apply_context_carry_forward(candidates)

        for c in candidates:
            window = windows[id(c)]
            exclude_reason = c.exclude_reason

            if exclude_reason is not None:
                format_counts_excluded[c.format] = format_counts_excluded.get(c.format, 0) + 1
                exclude_reason_counts[exclude_reason] = exclude_reason_counts.get(exclude_reason, 0) + 1
                seq += 1
                entries.append(
                    {
                        "id": seq,
                        "source_document": docs.filename,
                        "page": docs.page_of(c.start),
                        "format": c.format,
                        "raw": c.raw,
                        "context": window,
                        "parsed": c.parsed,
                        "in_gate_scope": False,
                        "exclude_reason": exclude_reason,
                        "resolution": None,
                    }
                )
                continue

            resolution = resolve_candidate(c, idx)
            if resolution.pop("not_a_citation", False):
                not_a_citation_count += 1
                continue

            format_counts[c.format] = format_counts.get(c.format, 0) + 1
            seq += 1
            entries.append(
                {
                    "id": seq,
                    "source_document": docs.filename,
                    "page": docs.page_of(c.start),
                    "format": c.format,
                    "raw": c.raw,
                    "context": window,
                    "parsed": c.parsed,
                    "in_gate_scope": True,
                    "exclude_reason": None,
                    "resolution": resolution,
                }
            )

    gate_entries = [e for e in entries if e["in_gate_scope"]]
    resolved = [e for e in gate_entries if e["resolution"]["status"] == "resolved"]
    unresolved = [e for e in gate_entries if e["resolution"]["status"] != "resolved"]

    unresolved_reason_counts: dict[str, int] = {}
    for e in unresolved:
        key = e["resolution"].get("code") or e["resolution"]["reason"].split(":")[0]
        unresolved_reason_counts[key] = unresolved_reason_counts.get(key, 0) + 1

    total = len(gate_entries)
    n_resolved = len(resolved)
    pct = round(100 * n_resolved / total, 1) if total else 0.0

    report = {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "ruleset_key": ruleset_key,
        "source": {
            "docs_dir": str(DOCS_DIR.relative_to(REPO_ROOT)),
            "documents_found": [p.name for p in pdfs],
            "documents_expected": 9,
        },
        "node_index": {
            "articles_json_present": idx.articles is not None,
            "articles_json_error": idx.articles_error,
            "use_matrix_json_present": idx.use_matrix is not None,
            "use_matrix_json_error": idx.use_matrix_error,
            "districts_json_present": idx.districts_json_present,
            "districts_json_note": "blocked by DECISIONS-NEEDED.md D-0001/D-0002 — expected absent",
        },
        "document_errors": doc_errors,
        "counts": {
            "gate_scope_total": total,
            "resolved": n_resolved,
            "unresolved": total - n_resolved,
            "resolved_pct": pct,
            "excluded_total": sum(format_counts_excluded.values()),
            "not_a_citation_filtered": not_a_citation_count,
            "by_format_in_scope": dict(sorted(format_counts.items())),
            "by_format_excluded": dict(sorted(format_counts_excluded.items())),
            "by_exclude_reason": dict(sorted(exclude_reason_counts.items())),
            "by_unresolved_reason": dict(sorted(unresolved_reason_counts.items(), key=lambda kv: -kv[1])),
        },
        "entries": entries,
    }
    return report


def print_summary(report: dict[str, Any]) -> None:
    c = report["counts"]
    print(f"Documents found: {len(report['source']['documents_found'])} / {report['source']['documents_expected']} expected")
    if report["document_errors"]:
        print("Document errors:")
        for e in report["document_errors"]:
            print(f"  - {e['document']}: {e['error']}")

    ni = report["node_index"]
    print()
    print("Node index availability:")
    print(f"  articles.json    : {'present' if ni['articles_json_present'] else 'MISSING (' + str(ni['articles_json_error']) + ')'}")
    print(f"  use-matrix.json  : {'present' if ni['use_matrix_json_present'] else 'MISSING (' + str(ni['use_matrix_json_error']) + ')'}")
    print(f"  districts.json   : {'present' if ni['districts_json_present'] else 'absent — ' + ni['districts_json_note']}")

    print()
    print("In-gate-scope citation formats found:")
    for fmt, n in c["by_format_in_scope"].items():
        print(f"  {fmt:32s} {n}")

    print()
    print("Excluded (out-of-gate-scope) citation formats found:")
    for fmt, n in c["by_format_excluded"].items():
        print(f"  {fmt:32s} {n}")
    print("Excluded by reason:")
    for reason, n in c["by_exclude_reason"].items():
        print(f"  {reason:32s} {n}")

    if c["by_unresolved_reason"]:
        print()
        print("Unresolved, by reason (first word of the reason string):")
        for reason, n in c["by_unresolved_reason"].items():
            print(f"  {reason:32s} {n}")

    if c["not_a_citation_filtered"]:
        print()
        print(f"Candidates discarded as not-actually-a-citation: {c['not_a_citation_filtered']}")

    print()
    print("Unresolved citations (source document + surrounding sentence):")
    unresolved = [e for e in report["entries"] if e["in_gate_scope"] and e["resolution"]["status"] != "resolved"]
    for e in unresolved[:40]:
        print(f"  [{e['id']}] {e['source_document']} p.{e['page']} ({e['format']}): {e['raw']!r}")
        print(f"        context: {e['context']}")
        print(f"        reason:  {e['resolution']['reason']}")
    if len(unresolved) > 40:
        print(f"  ... and {len(unresolved) - 40} more (see the JSON report)")

    print()
    print(f"CITATIONS: {c['resolved']}/{c['gate_scope_total']} resolved ({c['resolved_pct']}%)")


def write_report(report: dict[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False)
    # Atomic write (same discipline as CONTRACT.md §1 S2, though this is a
    # generated report, not durable app state — no backup/rotation needed).
    tmp = out_path.with_name(out_path.name + f".tmp-{__import__('os').getpid()}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            __import__("os").fsync(f.fileno())
        __import__("os").replace(tmp, out_path)
    finally:
        if tmp.exists():
            tmp.unlink()


def run(out_path: Path | None = None, quiet: bool = False) -> int:
    report = build_report()
    write_report(report, out_path or REPORT_PATH)
    if not quiet:
        print_summary(report)
        print()
        # Display relative to APP_ROOT when the target resolves inside it
        # (the common case, both for the default REPORT_PATH and for a
        # caller-supplied relative --out); otherwise show the path as given.
        # Resolve FIRST -- comparing a relative Path's un-resolved `.parents`
        # against the absolute APP_ROOT can never match, which previously
        # made a relative --out crash `.relative_to()` unconditionally.
        target = (out_path or REPORT_PATH).resolve()
        display = target.relative_to(APP_ROOT) if APP_ROOT == target or APP_ROOT in target.parents else target
        print(f"Full report written to {display}")
    else:
        c = report["counts"]
        print(f"CITATIONS: {c['resolved']}/{c['gate_scope_total']} resolved ({c['resolved_pct']}%)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Citation-verification harness (W2 gate)")
    parser.add_argument("--out", type=Path, default=None, help="report path (default: data/citation-report.json)")
    parser.add_argument("--quiet", action="store_true", help="print only the final CITATIONS: line")
    args = parser.parse_args(argv)
    return run(out_path=args.out, quiet=args.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
